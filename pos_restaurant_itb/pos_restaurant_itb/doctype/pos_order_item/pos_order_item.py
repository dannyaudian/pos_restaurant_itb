import frappe
from frappe.model.document import Document

class POSOrderItem(Document):
    def validate(self):
        # 🚨 Pastikan item_name ada
        if not self.item_name:
            frappe.throw("Item name is required.")

        # 📦 Ambil rate dari Price List (default: Standard Selling)
        if not self.rate and self.item_code:
            price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"

            rate = frappe.db.get_value("Item Price", {
                "item_code": self.item_code,
                "price_list": price_list
            }, "price_list_rate")

            if rate is None:
                rate = frappe.db.get_value("Item", self.item_code, "standard_rate") or 0
                frappe.msgprint(f"📌 Harga *fallback* dari Item: {rate}")
            else:
                frappe.msgprint(f"📌 Harga dari Price List *{price_list}*: {rate}")

            self.rate = rate

        # 💰 Hitung amount otomatis
        self.amount = (self.rate or 0) * (self.qty or 0)
        frappe.msgprint(f"💰 Total Amount = {self.qty or 0} x {self.rate or 0} = {self.amount}")

     # 🧩 Validasi Dynamic Attributes (jika ada)
    def resolve_item_variant(template_item, dynamic_attributes):
        # Buat dict attribute untuk pencocokan
        attr_dict = {attr.attribute_name: attr.attribute_value for attr in dynamic_attributes}

        # Cari variant dari template_item yang cocok
        variants = frappe.get_all("Item", filters={"variant_of": template_item}, fields=["name"])
        for v in variants:
            match = True
            variant_attrs = frappe.get_all("Item Variant Attribute", filters={"parent": v.name}, fields=["attribute", "attribute_value"])
            for va in variant_attrs:
                if attr_dict.get(va.attribute) != va.attribute_value:
                    match = False
                    break
            if match:
                return v.name
        return None

