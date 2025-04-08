import frappe
from frappe.model.document import Document
from frappe import _

class KOT(Document):
    def autoname(self):
        # Format: KOT-YYYYMMDD-BRANCHCODE-####
        today = frappe.utils.now().strftime("%Y%m%d")

        # Ambil branch code
        branch_code = frappe.db.get_value("Branch", self.branch, "branch_code") or "XXX"
        branch_code = branch_code.strip().upper()

        prefix = f"KOT-{today}-{branch_code}"

        last = frappe.db.sql(
            """SELECT name FROM `tabKOT`
               WHERE name LIKE %s
               ORDER BY name DESC LIMIT 1""",
            (prefix + "%",)
        )

        last_number = int(last[0][0].split("-")[-1]) if last else 0
        self.name = f"{prefix}-{str(last_number + 1).zfill(4)}"
        
        # Set field kot_id jika diperlukan
        self.kot_id = self.name

    def validate(self):
        if self.pos_order:
            pos_order = frappe.get_doc("POS Order", self.pos_order)

            # Hindari ambil dari POS Order yang sudah final
            if pos_order.docstatus == 1 and pos_order.status == "Paid":
                frappe.throw(_("POS Order ini sudah Final Billed dan tidak bisa digunakan untuk KOT."))

            self.table = self.table or pos_order.table
            self.branch = self.branch or pos_order.branch

            if not self.kot_items:
                for item in pos_order.pos_order_items:
                    if not item.cancelled and not item.sent_to_kitchen:
                        self.append("kot_items", {
                            "item_code": item.item_code,
                            "item_name": item.item_name,
                            "qty": item.qty,
                            "note": item.note,
                            "kot_status": "Queued",
                            "kot_last_update": frappe.utils.now(),
                            "dynamic_attributes": frappe.as_json(item.dynamic_attributes or []),
                            "order_id": pos_order.order_id,
                            "branch": pos_order.branch,
                            "waiter": get_waiter_from_user(frappe.session.user)
                        })

        # Tetapkan waiter jika belum
        if not self.waiter:
            self.waiter = get_waiter_from_user(frappe.session.user)

        if not self.kot_items:
            frappe.throw(_("Tidak ada item KOT yang valid untuk dibuat."))


def get_waiter_from_user(user_id):
    # Jika user punya Employee, ambil nama-nya
    emp = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
    return emp or user_id  # fallback ke user_id jika bukan karyawan (misal System Manager)
