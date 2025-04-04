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
