frappe.ui.form.on('POS Order', {
    table: function (frm) {
        if (frm.doc.table) {
            frappe.db.get_value('POS Table', frm.doc.table, 'branch', function (r) {
                if (r && r.branch) {
                    frm.set_value('branch', r.branch);
                    frappe.call({
                        method: "pos_restaurant_itb.api.get_new_order_id",
                        args: { branch: r.branch },
                        callback: function (res) {
                            if (res && res.message) {
                                frm.set_value("order_id", res.message);
                            }
                        }
                    });
                }
            });
        }
    },

    refresh: function (frm) {
        frm.add_custom_button(__('Print KOT'), function () {
            frappe.call({
                method: 'pos_restaurant_itb.api.print_kot',
                args: { name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        const win = window.open();
                        win.document.write(r.message);
                        win.document.close();
                    }
                }
            });
        }, __("Actions"));

        frm.add_custom_button(__('Print Receipt'), function () {
            frappe.call({
                method: 'pos_restaurant_itb.api.print_receipt',
                args: { name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        const win = window.open();
                        win.document.write(r.message);
                        win.document.close();
                    }
                }
            });
        }, __("Actions"));
    },

    onload: function (frm) {
        frm.fields_dict.pos_order_items.grid.get_field('item_code').get_query = function (doc, cdt, cdn) {
            return {
                filters: {
                    variant_of: ["is", "not set"],
                    is_sales_item: 1,
                    disabled: 0
                }
            };
        };
    }
});

frappe.ui.form.on('POS Order Item', {
    item_code: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.item_code) return;

        frappe.db.get_value("Item", row.item_code, "has_variants", function(r) {
            if (r && r.has_variants) {
                frappe.show_alert("🧩 Item ini punya varian. Silakan pilih atribut.");

                frappe.model.clear_table(row, 'dynamic_attributes');
                frm.refresh_field('pos_order_items');

                const grid_row = frm.fields_dict.pos_order_items.grid.grid_rows_by_docname[row.name];
                if (grid_row && grid_row.toggle_view) {
                    grid_row.toggle_view(true);
                }
            }
        });

        const price_list = frm.doc.selling_price_list || 'Standard Selling';
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Item Price",
                filters: {
                    item_code: row.item_code,
                    price_list: price_list
                },
                fields: ["price_list_rate"],
                limit_page_length: 1
            },
            callback: function(res) {
                const rate = (res.message?.[0]?.price_list_rate) || 0;
                frappe.model.set_value(cdt, cdn, 'rate', rate);
                if (rate === 0) {
                    frappe.msgprint(__('Harga tidak ditemukan di Price List: ' + price_list));
                }
            }
        });
    },

    qty: update_item_amount_and_total,
    rate: update_item_amount_and_total,

    dynamic_attributes: function(frm, cdt, cdn) {
        resolve_variant_if_ready(frm, cdt, cdn);
    }
});

frappe.ui.form.on('POS Dynamic Attribute', {
    attribute_value: function(frm, cdt, cdn) {
        const parent_row = frm.fields_dict["pos_order_items"].grid.get_selected_children()?.[0];
        if (!parent_row || !parent_row.item_code) return;
        resolve_variant_if_ready(frm, parent_row.doctype, parent_row.name);
    }
});

function resolve_variant_if_ready(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row.item_code || !row.dynamic_attributes?.length) return;

    const attributes = row.dynamic_attributes.map(attr => ({
        attribute_name: attr.attribute_name,
        attribute_value: attr.attribute_value
    }));

    if (!attributes.length) return;

    frappe.call({
        method: "pos_restaurant_itb.api.resolve_variant",
        args: {
            template: row.item_code,
            attributes: attributes
        },
        callback: function(r) {
            if (r.message) {
                frappe.model.set_value(cdt, cdn, 'item_code', r.message.item_code);
                frappe.model.set_value(cdt, cdn, 'item_name', r.message.item_name);
                frappe.model.set_value(cdt, cdn, 'rate', r.message.rate);

                frappe.show_alert({
                    message: `🔄 Diganti ke Variant: ${r.message.item_name}`,
                    indicator: 'green'
                });
            }
        }
    });
}

function update_item_amount_and_total(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row) return;

    const qty = row.qty || 0;
    const rate = row.rate || 0;
    const amount = qty * rate;

    frappe.model.set_value(cdt, cdn, "amount", amount);

    let total = 0;
    (frm.doc.pos_order_items || []).forEach(item => {
        total += item.amount || 0;
    });

    frm.set_value("total_amount", total);
    frm.refresh_field("total_amount");
}
