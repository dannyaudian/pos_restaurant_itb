# pos_restaurant_itb/pos_restaurant_itb/doctype/kot_item/kot_item.py

import frappe
import json
from frappe.model.document import Document
from frappe.utils import now_datetime
from pos_restaurant_itb.utils.kot_helpers import get_attribute_summary

class KOTItem(Document):
    def validate(self):
        """
        Validates the KOT Item before saving.
        """
        # Set default status if not specified
        if not self.kot_status:
            self.kot_status = "Queued"
            
        # Update timestamp when status changes
        if self.kot_status and not self.kot_last_update:
            self.kot_last_update = now_datetime()
        
        # Ensure cancelled items have kot_status = "Cancelled"
        if self.cancelled and self.kot_status != "Cancelled":
            self.kot_status = "Cancelled"
            self.kot_last_update = now_datetime()
        
        # Ensure cancelled items have a reason
        if self.cancelled and not self.cancellation_note:
            frappe.throw(frappe._("Please provide a cancellation reason for the cancelled item."))
    
    @property
    def attribute_summary(self):
        """
        Returns a human-readable summary of dynamic attributes.
        This uses the common helper function to ensure consistency with POS Order Item.
        
        Note: This method handles both dynamic_attributes and variant_attributes field names
        for backward compatibility.
        """
        # Check which field is being used in this instance
        if hasattr(self, 'dynamic_attributes') and self.dynamic_attributes:
            return get_attribute_summary(self.dynamic_attributes)
        elif hasattr(self, 'variant_attributes') and self.variant_attributes:
            return get_attribute_summary(self.variant_attributes)
        else:
            return ""