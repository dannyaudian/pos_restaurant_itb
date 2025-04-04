frappe.ui.form.on('POS Order', {
    table: function(frm) {
        if (frm.doc.table) {
            frappe.db.get_value('POS Table', frm.doc.table, 'branch', (r) => {
                if (r.branch) {
                    frm.set_value('branch', r.branch);

                    frappe.call({
                        method: "pos_restaurant_itb.api.get_new_order_id",
                        args: { branch: r.branch },
                        callback: function(res) {
                            if (res.message) {
                                frm.set_value("order_id", res.message);
                            }
                        }
                    });
                }
            });
        }
    }
});
