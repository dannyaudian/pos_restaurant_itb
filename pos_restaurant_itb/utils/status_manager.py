# -*- coding: utf-8 -*-
# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 17:28:47'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

# [KEEP EXISTING IMPORTS]
import frappe
from frappe import _
from typing import Dict, Optional, Any
from frappe.model.document import Document

from pos_restaurant_itb.utils.error_handlers import (
    handle_pos_errors,
    ValidationError,
    OrderError
)
from pos_restaurant_itb.utils.constants import (
    STATUS_TRANSITIONS,
    QR_ORDER_STATUSES,
    KOT_STATUSES,
    POS_ORDER_STATUSES,
    TableStatus,
    ErrorMessages
)
from pos_restaurant_itb.utils.security import SecurityManager@handle_pos_errors()
def handle_qr_order_status_update(
    qr_order: Document,
    new_status: str,
    user: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handle QR Order status updates
    
    Args:
        qr_order (Document): QR Order document
        new_status (str): New status to set
        user (str, optional): User performing update. Defaults to current user.
        
    Returns:
        Dict: Update result
    """
    if new_status not in QR_ORDER_STATUSES:
        raise ValidationError(
            ErrorMessages.format(
                "Invalid QR Order status: {status}. Valid statuses are: {valid}",
                status=new_status,
                valid=", ".join(QR_ORDER_STATUSES)
            )
        )
    
    security = SecurityManager()
    security.validate_branch_operation(
        qr_order.branch,
        f"update_qr_order_{new_status.lower()}"
    )
    
    result = update_order_status(qr_order, new_status, user)
    
    # Handle side effects
    if new_status == "Confirmed":
        _create_kot_from_qr_order(qr_order)
    elif new_status in ["Rejected", "Cancelled"]:
        _handle_qr_order_cancellation(qr_order)
        
    return result

def _create_kot_from_qr_order(qr_order: Document) -> Document:
    """
    Create KOT from QR Order
    
    Args:
        qr_order (Document): QR Order document
        
    Returns:
        Document: Created KOT document
    """
    if not qr_order.items:
        raise ValidationError(ErrorMessages.ITEMS_REQUIRED)
        
    kot = frappe.get_doc({
        "doctype": "KOT",
        "table": qr_order.table,
        "order_type": "QR",
        "order_id": qr_order.name,
        "branch": qr_order.branch,
        "items": [
            {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "quantity": item.quantity,
                "notes": item.notes
            }
            for item in qr_order.items
        ]
    })
    
    kot.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return kot

def _handle_qr_order_cancellation(qr_order: Document) -> None:
    """
    Handle QR Order cancellation side effects
    
    Args:
        qr_order (Document): QR Order document
    """
    # Update table status
    if qr_order.table:
        table = frappe.get_doc("POS Table", qr_order.table)
        table.status = TableStatus.AVAILABLE
        table.save(ignore_permissions=True)
    
    # Cancel related KOTs
    kots = frappe.get_all(
        "KOT",
        filters={
            "order_id": qr_order.name,
            "order_type": "QR",
            "docstatus": ["!=", 2]  # Not cancelled
        }
    )
    
    for kot in kots:
        kot_doc = frappe.get_doc("KOT", kot.name)
        if kot_doc.status not in ["Completed", "Cancelled"]:
            kot_doc.status = "Cancelled"
            kot_doc.save(ignore_permissions=True)

@frappe.whitelist()
@handle_pos_errors()
def get_qr_order_status_info(qr_order: str) -> Dict[str, Any]:
    """
    Get QR Order status information
    
    Args:
        qr_order (str): QR Order name/ID
        
    Returns:
        Dict: Status information
    """
    doc = frappe.get_doc("QR Order", qr_order)
    current_status = doc.status
    
    valid_transitions = STATUS_TRANSITIONS.get("QR Order", {}).get(current_status, [])
    
    security = SecurityManager()
    allowed_transitions = []
    
    for status in valid_transitions:
        try:
            security.validate_branch_operation(
                doc.branch,
                f"update_qr_order_{status.lower()}",
                raise_error=False
            )
            allowed_transitions.append(status)
        except:
            continue
    
    return {
        "current_status": current_status,
        "allowed_transitions": allowed_transitions,
        "has_active_kot": _has_active_kot(doc),
        "can_cancel": (current_status not in ["Cancelled", "Rejected"] and 
                      security.check_permission("update_qr_order_cancelled"))
    }

def _has_active_kot(qr_order: Document) -> bool:
    """
    Check if QR Order has active KOT
    
    Args:
        qr_order (Document): QR Order document
        
    Returns:
        bool: True if has active KOT
    """
    return bool(frappe.db.exists({
        "doctype": "KOT",
        "order_id": qr_order.name,
        "order_type": "QR",
        "status": ["not in", ["Completed", "Cancelled"]],
        "docstatus": ["!=", 2]
    }))

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
