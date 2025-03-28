frappe.ui.form.on('POS Order', {
    refresh: function(frm) {
        frm.add_custom_button(__('Print KOT'), function() {
            frappe.call({
                method: 'restaurant_pos_itb.api.print_kot',
                args: { name: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        var win = window.open();
                        win.document.write(r.message);
                        win.document.close();
                    }
                }
            });
        }, __("Actions"));

        frm.add_custom_button(__('Print Receipt'), function() {
            frappe.call({
                method: 'restaurant_pos_itb.api.print_receipt',
                args: { name: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        var win = window.open();
                        win.document.write(r.message);
                        win.document.close();
                    }
                }
            });
        }, __("Actions"));
    }
});
