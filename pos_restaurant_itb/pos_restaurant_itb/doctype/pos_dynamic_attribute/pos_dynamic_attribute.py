import frappe
from frappe.model.document import Document

class POSDynamicAttribute(Document):
    def validate(self):
        # Jika tidak lengkap, lewati
        if not self.attribute_name or not self.attribute_value:
            return

        # Validasi: attribute_value harus valid untuk attribute_name
        if frappe.db.exists("Item Attribute", self.attribute_name):
            valid_values = frappe.get_all(
                "Item Attribute Value",
                filters={"parent": self.attribute_name},
                pluck="name"
            )
            if self.attribute_value not in valid_values:
                frappe.throw(f"⚠️ Value '{self.attribute_value}' is not valid for Attribute '{self.attribute_name}'.")

        # Info tambahan jika ada item_code
        if self.item_code:
            if frappe.db.exists("Item", self.item_code):
                item_name = frappe.db.get_value("Item", self.item_code, "item_name")
                frappe.msgprint(f"✔️ Item: {self.item_code} - {item_name}")
            else:
                frappe.msgprint(f"⚠️ Item {self.item_code} tidak ditemukan.")
