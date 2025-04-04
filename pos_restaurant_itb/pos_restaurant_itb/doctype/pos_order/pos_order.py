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
        """
        Validasi dan update:
        - Total amount (qty * rate)
        - Status berdasarkan kot_status
        - Optional: parsing dynamic attributes per item
        """
        frappe.msgprint("🔍 Validating POS Order...")

        if not self.pos_order_items:
            self.status = "Draft"
            self.total_amount = 0
            frappe.msgprint("📭 No items. Status: Draft, Amount: 0")
            return

        total = 0
        item_statuses = []

        for item in self.pos_order_items:
            # Hitung amount
            qty = item.qty or 0
            rate = item.rate or 0
            item.amount = qty * rate
            total += item.amount

            item_statuses.append(item.kot_status or "Draft")
            frappe.msgprint(f"🧾 {item.item_name or item.item_code}: {qty} x {rate} = {item.amount}")

            # 🔄 Dynamic Attributes processing (jika child table digunakan)
        for item in self.pos_order_items:
            if not hasattr(item, "dynamic_attributes") or not item.dynamic_attributes:
                frappe.msgprint(f"Item {item.item_name} tidak memiliki dynamic attributes.")
                continue

            try:
                for attr in item.dynamic_attributes:
                    info = f"{attr.attribute_name} = {attr.attribute_value}"
                    if getattr(attr, "item_code", None):
                        info += f" → Linked Item: {attr.item_code}"
                    frappe.msgprint(f"✔️ Dynamic Attribute: {info}")
            except Exception as e:
                frappe.msgprint(f"❌ Gagal parsing dynamic attributes: {e}")


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
