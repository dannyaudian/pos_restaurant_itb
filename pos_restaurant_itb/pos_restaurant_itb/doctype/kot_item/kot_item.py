# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 09:26:12'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
from pos_restaurant_itb.utils import error_handlers
from pos_restaurant_itb.utils.constants import KOT_STATUSES

class KOTItem(Document):
    @error_handlers.handle_pos_errors()
    def validate(self):
        """Validate KOT Item"""
        self._set_defaults()
        self._validate_status()
        self._validate_cancellation()
        
    def _set_defaults(self):
        """Set default values"""
        if not self.kot_status:
            self.kot_status = "Queued"
            
        if self.kot_status and not self.kot_last_update:
            self.kot_last_update = now_datetime()
            
        if not self.waiter:
            self._set_waiter()
            
    def _set_waiter(self):
        """Set waiter from parent or current user"""
        if self.parent:
            parent_waiter = frappe.db.get_value(
                "KOT",
                self.parent,
                "waiter"
            )
            self.waiter = parent_waiter if parent_waiter else frappe.session.user
        else:
            self.waiter = frappe.session.user
            
    def _validate_status(self):
        """Validate KOT status transitions"""
        if not self.kot_status in KOT_STATUSES:
            raise error_handlers.ValidationError(
                f"Invalid KOT status: {self.kot_status}",
                "Status Error"
            )
            
        if hasattr(self, '_doc_before_save'):
            old_status = self._doc_before_save.kot_status
            if old_status and old_status != self.kot_status:
                self._validate_status_transition(old_status)
                self.kot_last_update = now_datetime()
                
    def _validate_status_transition(self, old_status):
        """Validate if status transition is allowed"""
        valid_transitions = {
            "Queued": ["Cooking", "Cancelled"],
            "Cooking": ["Ready", "Cancelled"],
            "Ready": ["Served", "Cancelled"],
            "Served": [],  # Final state
            "Cancelled": []  # Final state
        }
        
        if (old_status in valid_transitions and 
            self.kot_status not in valid_transitions[old_status]):
            raise error_handlers.ValidationError(
                f"Cannot change status from {old_status} to {self.kot_status}",
                "Status Error"
            )
            
    def _validate_cancellation(self):
        """Validate cancellation requirements"""
        if self.cancelled:
            if not self.cancellation_note:
                raise error_handlers.ValidationError(
                    "Cancellation note is required when cancelling an item",
                    "Validation Error"
                )
            self.kot_status = "Cancelled"
            self.kot_last_update = now_datetime()