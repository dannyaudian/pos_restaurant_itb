import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime

class POSOrder(Document):
    def autoname(self):
        # Validasi: branch harus ada
        if not self.branch:
            frappe.throw(_("Branch is required to generate Order ID."))

        # Format: POS-YYYYMMDD-BRANCHCODE-#####
        today = datetime.now().strftime("%Y%m%d")
        branch_code = frappe.db.get_value("Branch", self.branch, "branch_code")

        if not branch_code:
            frappe.throw(_("Branch must have a valid Branch Code."))

        branch_code = branch_code.strip().upper()
        prefix = f"POS-{today}-{branch_code}"

        # Cari order terakhir dengan prefix yang sama
        last = frappe.db.sql(
            """SELECT name FROM `tabPOS Order`
               WHERE name LIKE %s
               ORDER BY name DESC LIMIT 1""",
            (prefix + "-%",)
        )

        last_number = int(last[0][0].split("-")[-1]) if last else 0
        order_id = f"{prefix}-{str(last_number + 1).zfill(4)}"

        self.name = order_id
        self.order_id = order_id  # Untuk menghindari error mandatory field

    def before_save(self):
        if not self.branch:
            frappe.throw(_("Branch harus diisi."))

        # Validasi setup dapur aktif berdasarkan cabang
        has_station = frappe.db.exists("Kitchen Station Setup", {
            "branch": self.branch,
            "status": "Active"
        })

        if not has_station:
            frappe.throw(_("⚠️ Tidak ada Kitchen Station aktif untuk cabang ini."))

    def validate(self):
        if not self.branch:
            frappe.throw(_("Branch harus diisi."))

        # Tidak ada item: status draft
        if not self.pos_order_items:
            self.status = "Draft"
            self.total_amount = 0
            frappe.msgprint("📭 Order kosong. Status: Draft, Total: 0")
            return

        total = 0
        item_statuses = []

        for item in self.pos_order_items:
            if getattr(item, "cancelled", 0):
                continue

            item.validate()
            total += getattr(item, "amount", 0)
            item_statuses.append(getattr(item, "kot_status", "Draft") or "Draft")

        self.total_amount = total

        # Status logika berdasarkan status KOT item
        if all(s == "Ready" for s in item_statuses):
            new_status = "Ready for Billing"
        elif any(s in ["Cooking", "Queued"] for s in item_statuses):
            new_status = "In Progress"
        else:
            new_status = "Draft"

        if self.status != new_status:
            self.status = new_status

            if self.docstatus == 0 and new_status == "Draft":
                frappe.msgprint("📥 Order masih dalam draft.")
            elif self.docstatus == 0 and new_status == "In Progress":
                frappe.msgprint("⏳ Order berubah menjadi 'In Progress', silakan simpan untuk mengirim ke dapur.")
            else:
                frappe.msgprint(f"🔁 Status updated to: {self.status}")

        frappe.msgprint(f"💰 Total Order Amount: {self.total_amount}")
