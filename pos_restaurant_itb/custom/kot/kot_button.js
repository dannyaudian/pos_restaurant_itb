// File: pos_restaurant_itb/custom/kot/kot_button.js

frappe.ui.form.on('KOT', {
  refresh: function (frm) {
    if (frm.doc.docstatus === 1) {
      frm.add_custom_button("📺 Buat Kitchen Display", () => {
        frappe.call({
          method: "pos_restaurant_itb.api.kds_handler.create_kds_from_kot",
          args: { kot_id: frm.doc.name },
          callback: function (r) {
            if (r.message && r.message.kds_name) {
              frappe.show_alert(r.message.message || "✅ Kitchen Display dibuat.");
              frappe.set_route("Form", "Kitchen Display Order", r.message.kds_name);
            } else {
              frappe.show_alert("⚠️ Kitchen Display sudah tersedia.");
            }
          }
        });
      }, __("Actions"));
    }
  }
});
