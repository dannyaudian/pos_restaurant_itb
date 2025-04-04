import frappe
from frappe import _
from frappe.model.document import Document

class POSOrder(Document):
    def autoname(self):
     if not self.branch:
        frappe.throw(_("Branch is required to generate Order ID."))

     branch_code = frappe.db.get_value("Branch", self.branch, "branch_code")
     if not branch_code:
        frappe.throw(_("Branch must have a valid Branch Code."))

     branch_code = branch_code.strip().upper()

     if not self.order_id:
        count = frappe.db.count("POS Order", {"branch": self.branch}) + 1
        self.order_id = f"POS-{branch_code}-{count:05d}"
        frappe.msgprint(f"Generated Order ID: {self.order_id}")

     self.name = self.order_id

    def validate(self):
        """
        Update status otomatis berdasarkan isian dan proses:
        - Jika belum ada item: tetap Draft
        - Jika ada item tapi belum diproses dapur: In Progress
        - Jika semua item sudah Ready: Ready for Billing
        """
        frappe.msgprint("Running validate() on POS Order...")

        if not self.pos_order_items:
            self.status = "Draft"
            frappe.msgprint("Status set to Draft (no items).")
            return

        item_statuses = [d.kot_status for d in self.pos_order_items if d.kot_status]
        frappe.msgprint(f"Detected item statuses: {item_statuses}")

        if all(s == "Ready" for s in item_statuses):
            self.status = "Ready for Billing"
            frappe.msgprint("Status set to Ready for Billing.")
        elif any(s in ["Cooking", "Queued"] for s in item_statuses):
            self.status = "In Progress"
            frappe.msgprint("Status set to In Progress.")
        else:
            self.status = "Draft"
            frappe.msgprint("Fallback status: Draft.")
