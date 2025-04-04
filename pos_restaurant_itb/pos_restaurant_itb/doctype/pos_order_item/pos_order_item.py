import frappe
from frappe.model.document import Document

class POSOrderItem(Document):
    def validate(self):
        # Pastikan item name ada
        if not self.item_name:
            frappe.throw("Item name is required.")

        # Ambil rate dari Item jika kosong
        if not self.rate and self.item_code:
            self.rate = frappe.db.get_value("Item", self.item_code, "standard_rate") or 0
            frappe.msgprint(f"Rate otomatis diisi dari Item: {self.rate}")

        # Hitung amount otomatis
        self.amount = (self.rate or 0) * (self.qty or 0)
        frappe.msgprint(f"Amount dihitung ulang: {self.amount}")
