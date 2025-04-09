import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime

class POSOrder(Document):
    def autoname(self):
        self.validate_branch_for_autoname()
        self.name = self.generate_order_id()

    def before_save(self):
        self.validate_branch_is_set()
        validate_active_kitchen_station(self.branch)

    def validate(self):
        self.validate_branch_is_set()

        if not self.pos_order_items:
            self.status = "Draft"
            self.total_amount = 0
            frappe.msgprint("📭 Order kosong. Status: Draft, Total: 0")
            return

        self.calculate_total_and_update_status()

    def validate_branch_for_autoname(self):
        if not self.branch:
            frappe.throw(_("Branch is required to generate Order ID."))

    def generate_order_id(self):
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
        return f"{prefix}-{str(last_number + 1).zfill(4)}"

    def validate_branch_is_set(self):
        if not self.branch:
            frappe.throw(_("Branch harus diisi."))

    def calculate_total_and_update_status(self):
        total = 0
        item_statuses = []

        for item in self.pos_order_items:
            if item.cancelled:
                continue
            item.validate()
            total += item.amount
            item_statuses.append(item.kot_status or "Draft")

        self.total_amount = total

        # Tentukan status order
        if all(s == "Ready" for s in item_statuses):
            new_status = "Ready for Billing"
        elif any(s in ["Cooking", "Queued"] for s in item_statuses):
            new_status = "In Progress"
        else:
            new_status = "Draft"

        # Hanya ubah status jika berbeda
        if self.status != new_status:
            self.status = new_status
            if self.docstatus == 0 and new_status == "Draft":
                frappe.msgprint("📥 Order masih dalam draft.")
            elif self.docstatus == 0 and new_status == "In Progress":
                frappe.msgprint("⏳ Order berubah menjadi 'In Progress', silakan simpan untuk mengirim ke dapur.")
            else:
                frappe.msgprint(f"🔁 Status updated to: {self.status}")

        frappe.msgprint(f"💰 Total Order Amount: {self.total_amount}")

def validate_active_kitchen_station(branch):
    """Memeriksa apakah ada kitchen station yang aktif untuk cabang tertentu."""
    found = frappe.db.exists("Kitchen Station Setup", {"branch": branch, "status": "Active"})

    if not found:
        frappe.logger().warning(f"[DEBUG] Tidak ditemukan Kitchen Station aktif untuk cabang: '{branch}'")
        frappe.msgprint(_("⚠️ Tidak ada Kitchen Station aktif untuk cabang ini (dev mode)."))
