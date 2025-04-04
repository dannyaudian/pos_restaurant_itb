import frappe
from frappe.model.document import Document

class POSOrderItem(Document):
    def validate(self):
        if not self.item_name:
            frappe.throw("Item name is required.")
