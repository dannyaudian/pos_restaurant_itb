# -*- coding: utf-8 -*-
# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 17:26:57'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

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
    TableStatus,
    ErrorMessages
)
from pos_restaurant_itb.utils.security import SecurityManager

class StatusTransitionError(OrderError):
    pass

@handle_pos_errors()
def update_order_status(
    doc: Document, 
    new_status: str,
    user: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update order status with validation and side effects
    
    Args:
        doc (Document): Order document
        new_status (str): New status
        user (str, optional): User performing the update. Defaults to current user.
        
    Returns:
        Dict: Status update result
        
    Raises:
        ValidationError: If status transition is invalid
        StatusTransitionError: If status update fails
    """
    try:
        user = user or frappe.session.user
        doctype = doc.doctype
        current_status = doc.status
        
        # Get valid transitions for document type
        valid_transitions = STATUS_TRANSITIONS.get(doctype, {}).get(current_status, [])
        
        if new_status not in valid_transitions:
            raise ValidationError(
                ErrorMessages.format(
                    "Cannot change {doctype} status from {current} to {new}",
                    doctype=doctype,
                    current=current_status,
                    new=new_status
                )
            )
            
        security = SecurityManager()
        
        # Handle specific doctypes
        if doctype == "QR Order":
            _handle_qr_order_status_change(doc, new_status, security)
        elif doctype == "KOT":
            _handle_kot_status_change(doc, new_status, security)
        
        # Update status
        old_status = doc.status
        doc.status = new_status
        doc.status_changed_by = user
        doc.status_changed_on = frappe.utils.now()
        
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        # Log status change
        _log_status_change(doc, old_status, new_status, user)
        
        return {
            "success": True,
            "message": _(f"Status updated from {old_status} to {new_status}"),
            "old_status": old_status,
            "new_status": new_status
        }
        
    except Exception as e:
        frappe.db.rollback()
        raise StatusTransitionError(
            str(e),
            title=f"{doctype} Status Update Error"
        )

def _handle_qr_order_status_change(
    doc: Document,
    new_status: str,
    security: SecurityManager
) -> None:
    """
    Handle QR Order status change side effects
    
    Args:
        doc (Document): QR Order document
        new_status (str): New status
        security (SecurityManager): Security manager instance
    """
    # Validate branch access
    security.validate_branch_operation(
        doc.branch,
        f"update_qr_order_{new_status.lower()}"
    )
    
    if new_status == "Confirmed":
        # Create KOT
        if not doc.items:
            raise ValidationError(ErrorMessages.ITEMS_REQUIRED)
            
        kot = frappe.get_doc({
            "doctype": "KOT",
            "table": doc.table,
            "order_type": "QR",
            "order_id": doc.name,
            "branch": doc.branch,
            "items": [
                {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "notes": item.notes
                }
                for item in doc.items
            ]
        })
        kot.insert()
        
    elif new_status in ["Rejected", "Cancelled"]:
        # Update table status
        table = frappe.get_doc("POS Table", doc.table)
        table.status = TableStatus.AVAILABLE
        table.save()
        
        # Cancel related KOTs if any
        kots = frappe.get_all(
            "KOT",
            filters={
                "order_id": doc.name,
                "docstatus": ["!=", 2]  # Not cancelled
            }
        )
        for kot in kots:
            kot_doc = frappe.get_doc("KOT", kot.name)
            kot_doc.cancel()

def _handle_kot_status_change(
    doc: Document,
    new_status: str,
    security: SecurityManager
) -> None:
    """
    Handle KOT status change side effects
    
    Args:
        doc (Document): KOT document
        new_status (str): New status
        security (SecurityManager): Security manager instance
    """
    if new_status not in KOT_STATUSES:
        raise ValidationError(
            ErrorMessages.format(
                "Invalid KOT status: {status}",
                status=new_status
            )
        )
    
    # Validate branch access    
    security.validate_branch_operation(
        doc.branch,
        f"update_kot_{new_status.lower()}"
    )
    
    # Update related orders
    if doc.order_type == "QR" and doc.order_id:
        order = frappe.get_doc("QR Order", doc.order_id)
        order.kot_status = new_status
        order.save()

def _log_status_change(
    doc: Document,
    old_status: str,
    new_status: str,
    user: str
) -> None:
    """
    Log status change in system
    
    Args:
        doc (Document): Document being updated
        old_status (str): Previous status
        new_status (str): New status
        user (str): User performing the update
    """
    frappe.get_doc({
        "doctype": "Status Change Log",
        "reference_doctype": doc.doctype,
        "reference_name": doc.name,
        "old_status": old_status,
        "new_status": new_status,
        "changed_by": user,
        "creation": frappe.utils.now()
    }).insert(ignore_permissions=True)

@handle_pos_errors()
def get_valid_status_transitions(
    doctype: str,
    current_status: str
) -> Dict[str, Any]:
    """
    Get valid status transitions for document type
    
    Args:
        doctype (str): Document type
        current_status (str): Current status
        
    Returns:
        Dict: Valid status transitions
    """
    transitions = STATUS_TRANSITIONS.get(doctype, {}).get(current_status, [])
    
    return {
        "current_status": current_status,
        "valid_transitions": transitions,
        "doctype": doctype
    }