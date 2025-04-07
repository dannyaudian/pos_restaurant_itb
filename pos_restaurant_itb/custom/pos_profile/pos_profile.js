frappe.ui.form.on('POS Profile', {
    refresh: function(frm) {
        frappe.call({
            method: 'pos_restaurant_itb.api.metrics.load_pos_restaurant_config',
            args: { profile: frm.doc.name },
            callback: function(r) {
                if (r.message && r.message.is_restaurant) {
                    frm.dashboard.set_headline(__('This POS is configured for RESTAURANT MODE 🍽️'));
                    
                    frm.add_custom_button(__('View Restaurant Config'), function() {
                        frappe.set_route('Form', 'POS Restaurant Config', r.message.name);
                    });

                    // Optional: logging atau UI behavior lainnya
                    console.log("KOT Printing:", r.message.enable_kot_printing);
                    console.log("Receipt Mode:", r.message.receipt_template);
                }
            }
        });
    }
});
