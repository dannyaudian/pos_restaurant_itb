import frappe
from frappe.model.document import Document
from frappe import _

class POSTable(Document):
    def autoname(self):
        """
        Sets the name of the document based on the table_id and branch code.
        Format: [table_id] - [branch_code]
        """
        if not self.table_id:
            frappe.throw(_("Table ID is required"))
            
        # Clean table_id
        table_id = self.table_id.strip()
        
        # Get branch code
        branch_code = ""
        if self.branch:
            # Try to get branch_code field if it exists
            branch_fields = frappe.get_meta("Branch").get_fieldnames()
            if "branch_code" in branch_fields:
                branch_code = frappe.db.get_value("Branch", self.branch, "branch_code") or ""
            else:
                # If branch_code field doesn't exist, use first 3 chars of branch name
                branch_name = frappe.db.get_value("Branch", self.branch, "name") or ""
                branch_code = branch_name[:3].upper() if branch_name else ""
        
        # Set the name
        if branch_code:
            self.name = f"{table_id} - {branch_code}"
        else:
            self.name = table_id

    def validate(self):
        """
        Validates the POS Table data.
        """
        # Validate that the branch exists
        if self.branch and not frappe.db.exists("Branch", self.branch):
            frappe.throw(_("Branch {0} does not exist").format(self.branch))
        
        # Validate table_id format (add any specific validation rules here)
        if self.table_id:
            self.table_id = self.table_id.strip()
        
        # Additional validations can be added as needed