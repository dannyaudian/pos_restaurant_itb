import frappe
from frappe.model.document import Document

class KOTItem(Document):
    def autoname(self):
        # Use default autoname (e.g., KOTI-00001)
        pass

    def before_insert(self):
        if not self.waiter:
            waiter_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
            self.waiter = waiter_id or frappe.session.user
            frappe.msgprint(f"Waiter set to: {self.waiter}")
