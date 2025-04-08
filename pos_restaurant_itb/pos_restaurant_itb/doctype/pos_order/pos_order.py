import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime

class POSOrder(Document):
    def autoname(self):
        if not self.branch:
            frappe.throw(_("Branch is required to generate Order ID."))

        # Format: POS-YYYYMMDD-BRANCHCODE-#####
        today = datetime.now().strftime("%Y%m%d")

        branch_code = frappe.db.get_value("Branch", self.branch, "branch_code")
        if not branch_code:
            frappe.throw(_("Branch must have a valid Branch Code."))

        branch_code = branch_code.strip().upper()
        prefix = f"POS-{today}-{branch_code}"

        last = frappe.db.sql(
            """SELECT name FROM `tabPOS Order`
               WHERE name LIKE %s
               ORDER BY name DESC LIMIT 1""",
            (prefix + "-%",),
        )

        last_number = int(last[0][0].split("-")[-1]) if last else 0
        self.name = f"{prefix}-{str(last_number + 1).zfill(4)}"

    def before_save(self):
        if not self.branch:
            frappe.throw(_("Branch harus diisi."))
        validate_active_kitchen_station(self.branch)

    def validate(self):
        if not self.branch:
            frappe.throw(_("Branch harus diisi sebelum menyimpan order."))

        if not self.pos_order_items:
            self.status = "Draft"
            self.total_amount = 0
            frappe.msgprint("📭 Order kosong. Status: Draft, Total: 0")
            return

        total = 0
        item_statuses = []

        for item in self.pos_order_items:
            if item.cancelled:
                continue
            item.validate()
            total += item.amount
            item_statuses.append(item.kot_status or "Draft")

        self.total_amount = total

        # Penentuan status berdasarkan item
        if all(s == "Ready" for s in item_statuses):
            new_status = "Ready for Billing"
        elif any(s in ["Cooking", "Queued"] for s in item_statuses):
            new_status = "In Progress"
        else:
            new_status = "Draft"

        if self.status != new_status:
            self.status = new_status
            frappe.msgprint(f"🔁 Status updated to: {self.status}")

        frappe.msgprint(f"💰 Total Order Amount: {self.total_amount}")


def validate_active_kitchen_station(branch):
    """Memeriksa apakah ada kitchen station yang aktif untuk cabang tertentu."""
    found = frappe.db.exists("Kitchen Station Setup", {"branch": branch, "status": "Active"})

    if not found:
        frappe.logger().warning(f"[DEBUG] Tidak ditemukan Kitchen Station aktif untuk cabang: '{branch}'")
        frappe.msgprint(_("⚠️ Tidak ada Kitchen Station aktif untuk cabang ini (dev mode)."))
