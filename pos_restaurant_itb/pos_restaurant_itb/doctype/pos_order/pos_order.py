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
            frappe.msgprint(f"✅ Generated Order ID: {self.order_id}")

        self.name = self.order_id

    def validate(self):
        if not self.pos_order_items:
            self.status = "Draft"
            self.total_amount = 0
            frappe.msgprint("📭 Order kosong. Status: Draft, Total: 0")
            return

        total = 0
        item_statuses = []

        for item in self.pos_order_items:
            item.validate()
            total += item.amount
            item_statuses.append(item.kot_status or "Draft")

        self.total_amount = total

        # Tentukan status berdasarkan status item
        new_status = "Draft"
        if all(s == "Ready" for s in item_statuses):
            new_status = "Ready for Billing"
        elif any(s in ["Cooking", "Queued"] for s in item_statuses):
            new_status = "In Progress"

        if self.status != new_status:
            self.status = new_status
            frappe.msgprint(f"🔁 Status updated to: {self.status}")

        frappe.msgprint(f"💰 Total Order Amount: {self.total_amount}")
