frappe.ui.form.on('KOT', {
    refresh(frm) {
        frm.add_custom_button('Send to Kitchen', () => {
            frm.set_value('status', 'New');
            frm.save();
            frappe.msgprint('Order sent to kitchen!');
        });
    }
});
