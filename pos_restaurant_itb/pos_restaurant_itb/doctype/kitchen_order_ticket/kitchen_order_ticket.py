import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now, now_datetime

class KOT(Document):
    def autoname(self):
        """
        Generate KOT ID with format: KOT-YYYYMMDD-BRANCHCODE-####
        """
        today = now_datetime().strftime("%Y%m%d")
        
        # Get branch code
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
        self.kot_id = f"{prefix}-{str(last_number + 1).zfill(4)}"

    def validate(self):
        """
        Validates the Kitchen Order Ticket data.
        """
        if self.pos_order:
            pos_order = frappe.get_doc("POS Order", self.pos_order)
            
            # Prevent creating KOT from finalized POS Orders
            if pos_order.docstatus == 1 and pos_order.status == "Paid":
                frappe.throw(_("Cannot create KOT from a finalized POS Order."))
            
            # Fetch table and branch if not already set
            self.table = self.table or pos_order.table
            self.branch = self.branch or pos_order.branch
            
            # If no items specified, populate from POS Order items that aren't sent to kitchen
            if not self.kot_items:
                for item in pos_order.items:
                    if not item.cancelled and not item.sent_to_kitchen:
                        self.append("kot_items", {
                            "item_code": item.item_code,
                            "item_name": item.item_name,
                            "qty": item.qty,
                            "note": item.note,
                            "kot_status": "Queued",
                            "kot_last_update": now(),
                            "dynamic_attributes": item.dynamic_attributes,
                            "cancelled": 0
                        })
        
        # Set waiter if not specified
        if not self.waiter:
            self.waiter = self.get_waiter_from_user()
        
        # Ensure there are items to process
        if not self.kot_items:
            frappe.throw(_("No valid items found to create KOT."))
            
        # Set KOT time if not set
        if not self.kot_time:
            self.kot_time = now_datetime()
            
    def after_insert(self):
        """
        After KOT is saved, update the related POS Order items
        """
        if self.pos_order:
            # Get all item codes in this KOT
            kot_item_codes = [item.item_code for item in self.kot_items]
            
            # Update POS Order Items
            pos_order_items = frappe.get_all(
                "POS Order Item", 
                filters={
                    "parent": self.pos_order,
                    "item_code": ["in", kot_item_codes],
                    "sent_to_kitchen": 0,
                    "cancelled": 0
                },
                fields=["name"]
            )
            
            for item in pos_order_items:
                frappe.db.set_value("POS Order Item", item.name, {
                    "sent_to_kitchen": 1,
                    "kot_id": self.name
                })
    
    def get_waiter_from_user(self):
        """
        Get the Employee ID of the current user if they're a waiter/employee
        """
        user = frappe.session.user
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
        return employee or user
