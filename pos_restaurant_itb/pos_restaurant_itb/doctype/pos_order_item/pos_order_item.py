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
            frappe.msgprint(f"📌 Rate otomatis diisi dari Item: {self.rate}")

        # Hitung amount otomatis
        self.amount = (self.rate or 0) * (self.qty or 0)
        frappe.msgprint(f"💰 Amount dihitung ulang: {self.amount}")

        # Load nested dynamic attributes jika ada
        self.load_children()
        if not self.dynamic_attributes:
            frappe.msgprint(f"⚠️ Item {self.item_name} tidak memiliki dynamic attributes.")
            return

        try:
            for attr in self.dynamic_attributes:
                info = f"{attr.attribute_name} = {attr.attribute_value}"
                if getattr(attr, "item_code", None):
                    info += f" → Linked Item: {attr.item_code}"
                frappe.msgprint(f"✔️ Dynamic Attribute: {info}")
        except Exception as e:
            frappe.msgprint(f"❌ Gagal parsing dynamic attributes: {e}")
