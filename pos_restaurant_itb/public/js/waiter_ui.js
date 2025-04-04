frappe.ui.form.on('KOT', {
    refresh(frm) {
        // Hanya tampilkan tombol jika status belum 'Submitted' atau 'Served'
        if (!frm.doc.__islocal && frm.doc.status !== 'Served') {
            frm.add_custom_button(__('Send to Kitchen (Manual)'), () => {
                frappe.call({
                    method: "pos_restaurant_itb.api.send_to_kitchen",
                    args: {
                        pos_order: frm.doc.pos_order
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.msgprint(__('Order sent to kitchen via backend.'));
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
    }
});
