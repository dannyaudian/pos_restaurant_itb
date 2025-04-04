# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class POSDynamicAttribute(Document):
    def validate(self):
        # Optional: basic validation or debug message
        if not self.attribute_name or not self.attribute_value:
            frappe.throw("Attribute Name and Value are required.")
        
        # Optional info/debug
        frappe.msgprint(f"Dynamic Attribute: {self.attribute_name} = {self.attribute_value}")
