# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now
from frappe import _

class KitchenDisplayOrder(Document):
    def autoname(self):
        """
        Autoname format: KDS-{BRANCHCODE}-{YYYYMMDD}-{####}
        """
        if not self.branch:
            frappe.throw(_("Branch wajib diisi sebelum menyimpan KDS."))

        branch_code = frappe.db.get_value("Branch", self.branch, "branch_code")
        if not branch_code:
            frappe.throw(_("Branch Code tidak ditemukan untuk cabang: {0}").format(self.branch))

        prefix = f"KDS-{branch_code.upper()}-{now().strftime('%Y%m%d')}"
        last = frappe.db.sql(
            """SELECT name FROM `tabKitchen Display Order`
            WHERE name LIKE %s ORDER BY name DESC LIMIT 1""",
            (prefix + "%",)
        )

        last_number = int(last[0][0].split("-")[-1]) if last else 0
        self.name = f"{prefix}-{str(last_number + 1).zfill(4)}"

    def before_insert(self):
        self.last_updated = now()
        self.status = "New"

        # Auto isi branch dan table dari KOT jika kosong
        if self.kot_id:
            kot = frappe.get_doc("KOT", self.kot_id)
            self.branch = self.branch or kot.branch
            self.table = self.table or kot.table

    def on_update(self):
        self.last_updated = now()
