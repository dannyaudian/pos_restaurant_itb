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
        frappe.msgprint("🔍 Validating POS Order...")

        if not self.pos_order_items:
            self.status = "Draft"
            self.total_amount = 0
            frappe.msgprint("📭 No items. Status: Draft, Amount: 0")
            return

        total = 0
        item_statuses = []

        for item in self.pos_order_items:
            item.load_children()
            item.validate()  # Trigger validate() POSOrderItem

            total += item.amount
            item_statuses.append(item.kot_status or "Draft")

        self.total_amount = total
        frappe.msgprint(f"💰 Total Order Amount: {self.total_amount}")

        # Status logic
        if all(s == "Ready" for s in item_statuses):
            self.status = "Ready for Billing"
            frappe.msgprint("✅ Status: Ready for Billing")
        elif any(s in ["Cooking", "Queued"] for s in item_statuses):
            self.status = "In Progress"
            frappe.msgprint("⏳ Status: In Progress")
        else:
            self.status = "Draft"
            frappe.msgprint("📄 Status fallback: Draft")
