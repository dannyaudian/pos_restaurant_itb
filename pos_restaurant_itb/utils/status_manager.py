# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 09:51:38'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Optional, Dict, Any
from frappe.utils import now_datetime
from pos_restaurant_itb.utils.error_handlers import ValidationError
from pos_restaurant_itb.utils.constants import (
    STATUS_TRANSITIONS,
    POS_ORDER_STATUSES,
    KOT_STATUSES,
    KDS_STATUSES
)

class StatusManager:
    """
    Manages document status transitions and validations
    """
    
    def __init__(self, doctype: str, doc: Dict[str, Any]):
        self.doctype = doctype
        self.doc = doc
        self.transitions = STATUS_TRANSITIONS.get(doctype, {})
        self._set_valid_statuses()
    
    def _set_valid_statuses(self) -> None:
        """Set valid statuses based on doctype"""
        self.valid_statuses = {
            "POS Order": POS_ORDER_STATUSES,
            "KOT": KOT_STATUSES,
            "KDS": KDS_STATUSES
        }.get(self.doctype, set())
    
    def validate_status(self, new_status: str) -> None:
        """
        Validate if status is valid for doctype
        
        Args:
            new_status (str): Status to validate
            
        Raises:
            ValidationError: If status is invalid
        """
        if not self.valid_statuses:
            raise ValidationError(
                f"No status configuration found for {self.doctype}",
                "Configuration Error"
            )
            
        if new_status not in self.valid_statuses:
            raise ValidationError(
                f"Invalid status: {new_status}. Valid statuses are: {', '.join(sorted(self.valid_statuses))}",
                "Status Error"
            )
    
    def validate_transition(self, old_status: str, new_status: str) -> None:
        """
        Validate status transition
        
        Args:
            old_status (str): Current status
            new_status (str): New status
            
        Raises:
            ValidationError: If transition is invalid
        """
        if old_status == new_status:
            return
            
        allowed = self.transitions.get(old_status, [])
        if new_status not in allowed:
            raise ValidationError(
                f"Cannot change status from {old_status} to {new_status}",
                "Status Error"
            )
    
    def update_status(self, new_status: str, user: Optional[str] = None) -> None:
        """
        Update document status with validation
        
        Args:
            new_status (str): New status to set
            user (str, optional): User making the change
        """
        self.validate_status(new_status)
        
        old_status = self.doc.get("status")
        if old_status:
            self.validate_transition(old_status, new_status)
        
        self.doc.status = new_status
        self.doc.status_changed_at = now_datetime()
        self.doc.status_changed_by = user or frappe.session.user
        
        self._log_status_change(old_status, new_status)
    
    def _log_status_change(self, old_status: str, new_status: str) -> None:
        """
        Log status change
        
        Args:
            old_status (str): Previous status
            new_status (str): New status
        """
        frappe.get_doc({
            "doctype": "Status Log",
            "reference_doctype": self.doctype,
            "reference_name": self.doc.get("name"),
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": frappe.session.user,
            "timestamp": now_datetime(),
            "branch": self.doc.get("branch")
        }).insert(ignore_permissions=True)

def update_document_status(
    doctype: str,
    name: str,
    new_status: str,
    user: Optional[str] = None
) -> None:
    """
    Helper function to update document status
    
    Args:
        doctype (str): Document type
        name (str): Document name
        new_status (str): New status
        user (str, optional): User making the change
    """
    doc = frappe.get_doc(doctype, name)
    status_manager = StatusManager(doctype, doc)
    status_manager.update_status(new_status, user)
    doc.save(ignore_permissions=True)
    frappe.db.commit()