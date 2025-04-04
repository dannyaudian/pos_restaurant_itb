frappe.ui.form.on('POS Order', {
    table: function(frm) {
        if (frm.doc.table) {
            frappe.db.get_value('POS Table', frm.doc.table, 'branch', function(r) {
                if (r && r.branch) {
                    frm.set_value('branch', r.branch);

                    // Panggil API untuk generate order_id
                    frappe.call({
                        method: "pos_restaurant_itb.api.get_new_order_id",
                        args: {
                            branch: r.branch
                        },
                        callback: function(res) {
                            if (res && res.message) {
                                frm.set_value("order_id", res.message);
                            }
                        }
                    });
                }
            });
        }
    },

    refresh: function(frm) {
        // Tombol Print KOT
        frm.add_custom_button(__('Print KOT'), function() {
            frappe.call({
                method: 'pos_restaurant_itb.api.print_kot',
                args: { name: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        const win = window.open();
                        win.document.write(r.message);
                        win.document.close();
                    }
                }
            });
        }, __("Actions"));

        // Tombol Print Receipt
        frm.add_custom_button(__('Print Receipt'), function() {
            frappe.call({
                method: 'pos_restaurant_itb.api.print_receipt',
                args: { name: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        const win = window.open();
                        win.document.write(r.message);
                        win.document.close();
                    }
                }
            });
        }, __("Actions"));
    }
});

frappe.ui.form.on('POS Order Item', {
    item_code: function(frm, cdt, cdn) {
        let child = locals[cdt][cdn];
        if (!child.item_code) return;

        // Gunakan default price list dari POS Profile, atau fallback ke 'Standard Selling'
        let price_list = frm.doc.selling_price_list || 'Standard Selling';

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Item Price",
                filters: {
                    item_code: child.item_code,
                    price_list: price_list
                },
                fields: ["price_list_rate"],
                limit_page_length: 1
            },
            callback: function(res) {
                if (res.message && res.message.length > 0) {
                    let rate = res.message[0].price_list_rate;
                    frappe.model.set_value(cdt, cdn, 'rate', rate);
                } else {
                    frappe.msgprint(__('Harga untuk item ini tidak ditemukan di Price List: ' + price_list));
                    frappe.model.set_value(cdt, cdn, 'rate', 0);
                }
            }
        });
    },

    qty: function(frm, cdt, cdn) {
        update_item_amount_and_total(frm, cdt, cdn);
    },

    rate: function(frm, cdt, cdn) {
        update_item_amount_and_total(frm, cdt, cdn);
    }
});
frappe.ui.form.on('POS Order Item', {
    dynamic_attributes: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (!row.item_code || !row.dynamic_attributes || row.dynamic_attributes.length === 0) {
            return;
        }

        // Ambil atribut dari child table
        const attributes = row.dynamic_attributes.map(attr => ({
            attribute_name: attr.attribute_name,
            attribute_value: attr.attribute_value
        }));

        frappe.call({
            method: "pos_restaurant_itb.api.resolve_variant",
            args: {
                template: row.item_code,
                attributes: attributes
            },
            callback: function(res) {
                if (res.message) {
                    frappe.model.set_value(cdt, cdn, "item_code", res.message);
                    frappe.show_alert({
                        message: `🔄 Item diganti dengan variant: ${res.message}`,
                        indicator: 'green'
                    });
                }
            }
        });
    }
});
frappe.ui.form.on('POS Order', {
    onload: function(frm) {
        frm.fields_dict.pos_order_items.grid.get_field('item_code').get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    variant_of: null  // Hanya tampilkan item yang bukan varian
                }
            };
        };
    }
});
