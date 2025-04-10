import frappe
from frappe import _
from frappe.utils import today, now_datetime
from frappe.model.document import Document

class POSOrder(Document):
    def autoname(self):
        """
        Automatically generates the order_id based on branch code and date
        Format: ORD-{branch_code}-{YYYYMMDD}-{####}
        """
        if self.branch and not self.order_id:
            branch_code = frappe.db.get_value("Branch", self.branch, "branch_code") or "XXX"
            branch_code = branch_code.strip().upper()
            
            date_str = now_datetime().strftime("%Y%m%d")
            prefix = f"ORD-{branch_code}-{date_str}"
            
            # Find the last order ID with this prefix
            last_order = frappe.db.sql("""
                SELECT name FROM `tabPOS Order`
                WHERE name LIKE %s
                ORDER BY name DESC LIMIT 1
            """, (prefix + "%",))
            
            if last_order:
                last_num = int(last_order[0][0].split("-")[-1])
                order_id = f"{prefix}-{str(last_num + 1).zfill(4)}"
            else:
                order_id = f"{prefix}-0001"
                
            self.order_id = order_id
    
    def validate(self):
        """Validate POS Order data."""
        self.validate_branch()
        self.validate_table()
        self.validate_items()
        self.calculate_total_amount()
        self.validate_status_transition()
    
    def validate_branch(self):
        """Validate that the branch is active."""
        if self.branch:
            branch_is_active = frappe.db.get_value("Branch", self.branch, "is_active")
            if not branch_is_active:
                frappe.throw(_("Selected branch is not active."))
    
    def validate_table(self):
        """Validate that the table belongs to the selected branch and is active."""
        if self.table and self.branch and self.order_type == "Dine In":
            table_data = frappe.db.get_value(
                "POS Table", 
                self.table, 
                ["branch", "is_active"], 
                as_dict=True
            )
            
            if not table_data:
                frappe.throw(_("Table {0} not found.").format(self.table))
            
            if table_data.branch != self.branch:
                frappe.throw(
                    _("Table {0} does not belong to branch {1}.").format(
                        self.table, self.branch
                    )
                )
                
            if not table_data.is_active:
                frappe.throw(_("Selected table is not active."))
    
    def validate_items(self):
        """Validate that the order has items."""
        if not self.items or len(self.items) == 0:
            frappe.throw(_("Please add at least one item to the order."))
    
    def calculate_total_amount(self):
        """Calculate the total amount based on items."""
        total = 0
        for item in self.items:
            if not item.amount:
                item.amount = item.qty * item.rate
            total += item.amount
            
        self.total_amount = total
    
    def validate_status_transition(self):
        """Validate status transitions."""
        if not self.is_new():
            old_status = frappe.db.get_value("POS Order", self.name, "status")
            
            # Define valid status transitions
            valid_transitions = {
                "Draft": ["In Progress", "Cancelled"],
                "In Progress": ["Ready for Billing", "Cancelled"],
                "Ready for Billing": ["Paid", "Cancelled"],
                "Paid": [],  # Cannot transition from Paid
                "Cancelled": []  # Cannot transition from Cancelled
            }
            
            if old_status != self.status and self.status not in valid_transitions.get(old_status, []):
                frappe.throw(
                    _("Cannot change status from {0} to {1}.").format(
                        old_status, self.status
                    )
                )
            
            # If status is changed to Paid, set final_billed
            if self.status == "Paid" and old_status != "Paid":
                self.final_billed = 1
                
                # Ensure there's a Sales Invoice
                if not self.sales_invoice:
                    frappe.throw(_("Sales Invoice is required when marking order as Paid."))
    
    def before_save(self):
        """Operations before saving the document."""
        # If this is a new order, ensure status is Draft
        if self.is_new() and self.status != "Draft":
            self.status = "Draft"