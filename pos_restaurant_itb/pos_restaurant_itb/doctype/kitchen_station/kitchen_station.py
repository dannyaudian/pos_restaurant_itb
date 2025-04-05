import frappe
from frappe.model.document import Document
from frappe import _

class KitchenStation(Document):
    def autoname(self):
        if not self.branch:
            frappe.throw("Branch harus diisi untuk membuat ID Kitchen Station.")

        branch_code = frappe.db.get_value("Branch", self.branch, "branch_code")
        if not branch_code:
            frappe.throw("Branch Code tidak ditemukan untuk cabang ini.")

        branch_code = branch_code.strip().upper()
        count = frappe.db.count("Kitchen Station", {"branch": self.branch}) + 1
        self.name = f"KS-{branch_code}-{str(count).zfill(4)}"

    def validate(self):
        # Validasi tambahan jika diperlukan nanti
        pass
