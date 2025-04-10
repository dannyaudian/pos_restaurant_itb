import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

class KitchenDisplayOrder(Document):
    def autoname(self):
        """
        Auto-generate name based on KOT ID and a suffix
        """
        if self.kot_id:
            self.name = f"KDS-{self.kot_id}"
        else:
            # Fallback to timestamp if no KOT ID
            timestamp = now_datetime().strftime("%Y%m%d%H%M%S")
            self.name = f"KDS-{timestamp}"
    
    def before_insert(self):
        """
        Set the last_updated field before insert
        """
        self.last_updated = now_datetime()
    
    def on_update(self):
        """
        Update the last_updated field on every update
        Also update the status of the related KOT if needed
        """
        self.last_updated = now_datetime()
        
        # Only update the KOT if this document is being updated manually (not from KOT)
        if not frappe.flags.in_kot_update and self.kot_id:
            kot = frappe.get_doc("Kitchen Order Ticket", self.kot_id)
            
            # Only update KOT status if it's different
            if kot.status != self.status:
                kot.status = self.status
                kot.db.set_value("Kitchen Order Ticket", self.kot_id, "status", self.status)
                frappe.db.commit()