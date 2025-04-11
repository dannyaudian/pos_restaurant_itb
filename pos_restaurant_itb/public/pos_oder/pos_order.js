
// File: pos_restaurant_itb/public/pos_order/pos_order.js

frappe.ui.form.on('POS Order', {
    refresh: function(frm) {
        setup_item_query(frm);
    },
    
    setup: function(frm) {
        // Set custom query for item selection to only show templates
        setup_item_query(frm);
    }
});

// Custom handlers for POS Order Item child table
frappe.ui.form.on('POS Order Item', {
    item_code: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        
        // Check if this is a template item
        if (row.item_code) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Item",
                    filters: {
                        name: row.item_code
                    },
                    fieldname: ["has_variants", "item_name", "standard_rate"]
                },
                callback: function(data) {
                    if (data.message && data.message.has_variants) {
                        // This is a template item, show attribute selection
                        row.template_item = row.item_code;
                        
                        // Open dialog to select attributes
                        show_attribute_dialog(frm, row);
                    } else {
                        // This is a regular item or variant, just update the row
                        if (data.message) {
                            frappe.model.set_value(cdt, cdn, "item_name", data.message.item_name);
                            frappe.model.set_value(cdt, cdn, "rate", data.message.standard_rate);
                            update_item_amount_and_total(frm, cdt, cdn);
                        }
                    }
                }
            });
        }
    }
});

// Function to setup the item query to only show templates
function setup_item_query(frm) {
    frm.set_query("item_code", "items", function() {
        return {
            filters: {
                "has_variants": 1,
                "is_sales_item": 1
            }
        };
    });
}

// Function to show the attribute selection dialog
function show_attribute_dialog(frm, row) {
    // Fetch attributes for this template
    frappe.call({
        method: "pos_restaurant_itb.api.get_attributes_for_item.get_attributes_for_item",
        args: {
            item_code: row.template_item
        },
        callback: function(r) {
            if (!r.message || r.message.length === 0) {
                frappe.msgprint(__("No attributes found for this template item."));
                return;
            }
            
            // Create fields for the dialog
            var fields = [];
            r.message.forEach(function(attr) {
                fields.push({
                    label: attr.attribute,
                    fieldname: attr.attribute,
                    fieldtype: "Select",
                    options: attr.values.join("\n"),
                    reqd: 1
                });
            });
            
            // Add a field for notes
            fields.push({
                label: "Preparation Note",
                fieldname: "note",
                fieldtype: "Small Text"
            });
            
            // Create and show dialog
            var d = new frappe.ui.Dialog({
                title: __("Select Attributes for {0}", [row.template_item]),
                fields: fields,
                primary_action_label: __("Add Item"),
                primary_action: function(values) {
                    resolve_variant_after_save(frm, row, values);
                    d.hide();
                }
            });
            
            d.show();
        }
    });
}

// Function to resolve the variant after attributes are selected
function resolve_variant_after_save(frm, row, attributes) {
    // Convert attribute values to the format expected by the API
    var attr_array = [];
    for (var key in attributes) {
        if (key !== "note") {  // Skip note field
            attr_array.push({
                "attribute_name": key,
                "attribute_value": attributes[key]
            });
        }
    }
    
    // Call API to resolve the variant
    frappe.call({
        method: "pos_restaurant_itb.api.resolve_variant.resolve_variant",
        args: {
            template: row.template_item,
            attributes: attr_array
        },
        callback: function(r) {
            if (r.message && r.message.status === "success") {
                // Set the resolved variant
                frappe.model.set_value(row.doctype, row.name, "item_code", r.message.item_code);
                frappe.model.set_value(row.doctype, row.name, "item_name", r.message.item_name);
                frappe.model.set_value(row.doctype, row.name, "rate", r.message.rate);
                frappe.model.set_value(row.doctype, row.name, "variant_attributes", JSON.stringify(attr_array));
                frappe.model.set_value(row.doctype, row.name, "note", attributes.note || "");
                
                // Update amounts
                update_item_amount_and_total(frm, row.doctype, row.name);
                
                frappe.show_alert({
                    message: __("Added variant item {0}", [r.message.item_code]),
                    indicator: 'green'
                });
            } else {
                // Show error
                frappe.msgprint(r.message.message || __("Could not resolve variant item."));
                
                // Clear the row if variant resolution failed
                frappe.model.set_value(row.doctype, row.name, "item_code", "");
                frappe.model.set_value(row.doctype, row.name, "template_item", "");
            }
        }
    });
}

// Function to update item amount and total
function update_item_amount_and_total(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    var amount = row.qty * row.rate;
    frappe.model.set_value(cdt, cdn, "amount", amount);
    
    // Update total
    var total = 0;
    frm.doc.items.forEach(function(item) {
        if (!item.cancelled) {
            total += item.amount;
        }
    });
    
    frm.set_value("total_amount", total);
}
