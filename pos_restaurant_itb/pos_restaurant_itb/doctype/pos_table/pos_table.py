import frappe
from frappe.model.document import Document

class POSTable(Document):
    def autoname(self):
        """
        Sets the name of the document based on the table_id field.
        """
        # table_id is already configured as the autoname field in the JSON
        # This method is here for any additional processing if needed
        pass

    def validate(self):
        """
        Validates the POS Table data.
        """
        # Validate that the branch is active
        if self.branch:
            branch_is_active = frappe.db.get_value("Branch", self.branch, "is_active")
            if not branch_is_active:
                frappe.throw(frappe._("Selected branch is not active."))
        
        # Validate table_id format (add any specific validation rules here)
        self.table_id = self.table_id.strip()
        
        # Additional validations can be added as needed