# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class POSTable(Document):
    def autoname(self):
        """
        Autoname format: table_id__branch_code (e.g., T01__JKT)
        Ensures global uniqueness of table ID per branch
        """
        if not self.table_id:
            frappe.throw(_("Table ID is required."))

        if not self.branch:
            frappe.throw(_("Branch is required."))

        # Get branch_code from linked Branch
        branch_code = frappe.get_value("Branch", self.branch, "branch_code")
        if not branch_code:
            frappe.throw(_("Branch Code not found for Branch: {0}").format(self.branch))

        branch_code = branch_code.strip().upper()

        # Check if a table with the same table_id exists in the same branch (excluding current)
        existing = frappe.db.exists("POS Table", {
            "table_id": self.table_id,
            "branch": self.branch,
            "name": ["!=", self.name]
        })

        if existing:
            frappe.throw(_(
                f"Table ID '{self.table_id}' already exists in Branch '{self.branch}'."
            ))

        # Set final document name
        self.name = f"{self.table_id}__{branch_code}"
        frappe.msgprint(f"POS Table autonamed to: {self.name}")
