import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime

class POSOrder(Document):
    def autoname(self):
        # Pastikan field branch diisi
        if not self.branch:
            frappe.throw(_("Branch is required to generate Order ID."))

        # Format tanggal untuk digunakan dalam ID
        today = datetime.now().strftime("%Y%m%d")

        # Ambil kode cabang dari master Branch
        branch_code = frappe.db.get_value("Branch", self.branch, "branch_code")

        if not branch_code:
            frappe.throw(_("Branch must have a valid Branch Code."))

        branch_code = branch_code.strip().upper()
        prefix = f"POS-{today}-{branch_code}"

        # Ambil ID terakhir dengan prefix yang sama untuk increment
        last = frappe.db.sql(
            """SELECT name FROM `tabPOS Order`
               WHERE name LIKE %s
               ORDER BY name DESC LIMIT 1""",
            (prefix + "-%",),
        )

        # Hitung nomor berikutnya dan set sebagai name
        last_number = int(last[0][0].split("-")[-1]) if last else 0
        self.name = f"{prefix}-{str(last_number + 1).zfill(4)}"

    def before_save(self):
        # Validasi branch wajib diisi
        if not self.branch:
            frappe.throw(_("Branch harus diisi."))

        # Validasi kitchen station setup aktif harus tersedia
        if not frappe.db.exists("Kitchen Station Setup", {"branch": self.branch, "status": "Active"}):
            frappe.throw(_("\u26a0\ufe0f Tidak ada Kitchen Station aktif untuk cabang ini."))

    def validate(self):
        # Validasi branch harus diisi juga saat validate
        if not self.branch:
            frappe.throw(_("Branch harus diisi."))

        # Jika tidak ada item order, set sebagai draft
        if not self.pos_order_items:
            self.status = "Draft"
            self.total_amount = 0
            frappe.msgprint("\ud83d\udcec Order kosong. Status: Draft, Total: 0")
            return

        total = 0
        item_statuses = []

        # Iterasi semua item order
        for item in self.pos_order_items:
            # Lewati item yang dibatalkan
            if getattr(item, "cancelled", 0):
                continue

            item.validate()
            total += getattr(item, "amount", 0)
            item_statuses.append(getattr(item, "kot_status", "Draft") or "Draft")

        self.total_amount = total

        # Tentukan status baru berdasarkan status KOT item
        if all(s == "Ready" for s in item_statuses):
            new_status = "Ready for Billing"
        elif any(s in ["Cooking", "Queued"] for s in item_statuses):
            new_status = "In Progress"
        else:
            new_status = "Draft"

        # Jika status berubah, tampilkan notifikasi perubahan
        if self.status != new_status:
            self.status = new_status

            if self.docstatus == 0 and new_status == "Draft":
                frappe.msgprint("\ud83d\udcc5 Order masih dalam draft.")
            elif self.docstatus == 0 and new_status == "In Progress":
                frappe.msgprint("\u23f3 Order berubah menjadi 'In Progress', silakan simpan untuk mengirim ke dapur.")
            else:
                frappe.msgprint(f"\ud83d\udd01 Status updated to: {self.status}")

        # Tampilkan total order
        frappe.msgprint(f"\ud83d\udcb0 Total Order Amount: {self.total_amount}")
