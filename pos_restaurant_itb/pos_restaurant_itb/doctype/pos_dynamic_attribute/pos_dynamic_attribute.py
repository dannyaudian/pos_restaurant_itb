# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class POSDynamicAttribute(Document):
    def validate(self):
        if not self.attribute_name or not self.attribute_value:
            frappe.throw("Attribute Name and Value are required.")

        # Optional: pastikan attribute_value valid untuk attribute_name (jika diambil dari master ERP)
        if frappe.db.exists("Item Attribute", self.attribute_name):
            valid_values = frappe.get_all("Item Attribute Value",
                filters={"parent": self.attribute_name},
                pluck="attribute_value")
            
            if self.attribute_value not in valid_values:
                frappe.throw(f"Value '{self.attribute_value}' is not valid for Attribute '{self.attribute_name}'.")

        # Optional: validasi item_code jika diberikan
        if self.item_code and not frappe.db.exists("Item", self.item_code):
            frappe.throw(f"Item '{self.item_code}' not found.")

        # Debug
        frappe.msgprint(f"✔️ Dynamic Attribute valid: {self.attribute_name} = {self.attribute_value}")
