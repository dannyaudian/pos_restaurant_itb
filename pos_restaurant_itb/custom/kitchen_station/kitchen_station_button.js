frappe.ui.form.on('Kitchen Station', {
  refresh: function (frm) {
    // Tombol untuk status Queued
    if (!frm.doc.kot_status || frm.doc.kot_status === 'Queued') {
      frm.add_custom_button('▶️ Cooking', () => {
        updateKitchenItemStatus(frm, 'Cooking');
      }, 'Update Status');

      frm.add_custom_button('❌ Cancel', () => {
        frappe.prompt(
          [
            {
              label: 'Alasan Pembatalan',
              fieldname: "Cancellation Note",
              fieldtype: 'Small Text',
              reqd: 1
            }
          ],
          (values) => {
            frappe.call({
              method: 'pos_restaurant_itb.api.kitchen_station.cancel_kitchen_item',
              args: {
                kot_item_id: frm.doc.name,
                reason: values.reason
              },
              callback: function (r) {
                if (r.message && r.message.status === 'success') {
                  frappe.show_alert(r.message.message);
                  frm.reload_doc();
                }
              }
            });
          },
          'Konfirmasi Pembatalan',
          'Batalkan Item'
        );
      }, 'Update Status');
    }

    // Tombol untuk status Cooking
    if (frm.doc.kot_status === 'Cooking') {
      frm.add_custom_button('✅ Ready', () => {
        updateKitchenItemStatus(frm, 'Ready');
      }, 'Update Status');
    }
  }
});

function updateKitchenItemStatus(frm, status) {
  frappe.call({
    method: 'pos_restaurant_itb.api.kitchen_station.update_kitchen_item_status',
    args: {
      kot_item_id: frm.doc.name,
      new_status: status
    },
    callback: function (r) {
      if (r.message && r.message.status === 'success') {
        frappe.show_alert(r.message.message);
        frm.reload_doc();
      }
    }
  });
}
