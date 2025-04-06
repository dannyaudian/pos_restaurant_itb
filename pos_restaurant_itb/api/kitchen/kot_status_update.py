# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 15:05:58'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional
from datetime import datetime

from pos_restaurant_itb.utils.error_handlers import (
    handle_api_error,
    ValidationError,
    StatusError
)
from pos_restaurant_itb.utils.security import validate_branch_operation
from pos_restaurant_itb.utils.constants import (
    KOTStatus,
    KDSStatus,
    ErrorMessages
)
from pos_restaurant_itb.utils.realtime import (
    notify_kot_update,
    notify_kds_update
)

@frappe.whitelist()
@handle_api_error
def update_kds_status_from_kot(kds_id: str) -> Dict:
    """
    Update Kitchen Display Order (KDS) status based on KOT items status
    
    Status Logic:
    - All "Served"            → status = "Served"
    - All "Ready" / "Served"  → status = "Ready"
    - Any "In Progress"       → status = "In Progress"
    - Others                  → status = "New"
    
    Args:
        kds_id: Kitchen Display Order ID
        
    Returns:
        Dict: Update status
            {
                "success": bool,
                "kds_id": str,
                "old_status": str,
                "new_status": str,
                "timestamp": datetime
            }
    """
    if not kds_id:
        raise ValidationError(
            "KDS ID is required",
            "Missing Data"
        )

    try:
        kds = frappe.get_doc("Kitchen Display Order", kds_id)
        
        # Validate permission
        validate_branch_operation(
            kds.branch,
            "update_kds",
            frappe.session.user
        )
        
        # Get active items status
        statuses = [
            item.status 
            for item in kds.items 
            if not item.is_cancelled
        ]
        
        old_status = kds.status
        new_status = determine_kds_status(statuses)
        
        if old_status != new_status:
            kds.status = new_status
            kds.modified = frappe.utils.now()
            kds.modified_by = frappe.session.user
            kds.save(ignore_permissions=True)
            
            # Notify update
            notify_kds_update(kds)
            
            # Log status change
            log_status_change(
                kds_id,
                old_status,
                new_status
            )
        
        return {
            "success": True,
            "kds_id": kds_id,
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": frappe.utils.now()
        }

    except Exception as e:
        log_error(e, kds_id)
        raise

@frappe.whitelist()
@handle_api_error
def bulk_update_kot_status(updates: List[Dict]) -> Dict:
    """
    Batch update KOT items status
    
    Args:
        updates: List of updates
            [
                {
                    "kot_id": str,
                    "item_code": str,
                    "new_status": str,
                    "note": str (optional)
                }
            ]
        
    Returns:
        Dict: Update results
            {
                "success": [
                    {
                        "kot_id": str,
                        "item_code": str,
                        "old_status": str,
                        "new_status": str
                    }
                ],
                "failed": [
                    {
                        "kot_id": str,
                        "item_code": str,
                        "new_status": str,
                        "reason": str
                    }
                ]
            }
    """
    if not updates:
        raise ValidationError(
            "No updates provided",
            "Missing Data"
        )
    
    results = {
        "success": [],
        "failed": []
    }
    
    for update in updates:
        try:
            result = update_single_kot_item(update)
            results["success"].append(result)
            
        except Exception as e:
            results["failed"].append({
                **update,
                "reason": str(e)
            })
    
    return results

def determine_kds_status(statuses: List[str]) -> str:
    """
    Determine KDS status based on item statuses
    
    Args:
        statuses: List of item statuses
        
    Returns:
        str: Determined KDS status
    """
    if not statuses:
        return KDSStatus.NEW
        
    if all(s == KOTStatus.SERVED for s in statuses):
        return KDSStatus.SERVED
        
    if all(s in [KOTStatus.COMPLETED, KOTStatus.SERVED] for s in statuses):
        return KDSStatus.COMPLETED
        
    if any(s == KOTStatus.IN_PROGRESS for s in statuses):
        return KDSStatus.IN_PROGRESS
        
    return KDSStatus.NEW

def update_single_kot_item(update: Dict) -> Dict:
    """
    Update single KOT item status
    
    Args:
        update: Update details
        
    Returns:
        Dict: Update result
    """
    kot_id = update.get("kot_id")
    item_code = update.get("item_code")
    new_status = update.get("new_status")
    note = update.get("note")
    
    if not all([kot_id, item_code, new_status]):
        raise ValidationError(
            "kot_id, item_code and new_status are required",
            "Missing Data"
        )
        
    if new_status not in KOTStatus.ALL:
        raise StatusError(
            f"Invalid status: {new_status}",
            "Invalid Status"
        )
    
    kot = frappe.get_doc("KOT", kot_id)
    
    # Validate permission
    validate_branch_operation(
        kot.branch,
        "update_kot",
        frappe.session.user
    )
    
    # Find and update item
    item_updated = False
    for item in kot.kot_items:
        if item.item_code == item_code:
            old_status = item.kot_status
            item.kot_status = new_status
            item.note = note or item.note
            item.modified = frappe.utils.now()
            item_updated = True
            break
    
    if not item_updated:
        raise ValidationError(
            f"Item {item_code} not found in KOT {kot_id}",
            "Not Found"
        )
    
    kot.save(ignore_permissions=True)
    
    # Notify update
    notify_kot_update(kot)
    
    return {
        "kot_id": kot_id,
        "item_code": item_code,
        "old_status": old_status,
        "new_status": new_status
    }

def log_status_change(
    doc_id: str,
    old_status: str,
    new_status: str
) -> None:
    """
    Log status change event
    
    Args:
        doc_id: Document ID
        old_status: Previous status
        new_status: New status
    """
    frappe.logger().info(
        f"Status Change Event\n"
        f"Document: {doc_id}\n"
        f"Old Status: {old_status}\n"
        f"New Status: {new_status}\n"
        f"Changed by: {frappe.session.user}\n"
        f"Timestamp: {frappe.utils.now()}"
    )

def log_error(error: Exception, doc_id: str) -> None:
    """
    Log operation error
    
    Args:
        error: Exception object
        doc_id: Related document ID
    """
    error_msg = f"""
    Status Update Error
    ------------------
    Document: {doc_id}
    User: {frappe.session.user}
    Time: {frappe.utils.now()}
    Error: {str(error)}
    Traceback: {frappe.get_traceback()}
    """
    
    frappe.log_error(
        message=error_msg,
        title="❌ Status Update Error"
    )