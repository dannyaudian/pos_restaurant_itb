# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 15:12:58'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, Optional, Union
from datetime import datetime

from pos_restaurant_itb.utils.error_handlers import (
    handle_api_error,
    ValidationError,
    PermissionError,
    KitchenError
)
from pos_restaurant_itb.utils.security import (
    validate_branch_operation,
    validate_manager_role
)
from pos_restaurant_itb.utils.constants import (
    KOTStatus,
    OrderStatus,
    ErrorMessages
)
from pos_restaurant_itb.utils.realtime import (
    notify_kot_update,
    notify_order_update
)

@frappe.whitelist()
@handle_api_error
def send_to_kitchen(
    pos_order: str,
    printer_id: Optional[str] = None
) -> Dict:
    """
    Send order items to kitchen by creating KOT
    
    Args:
        pos_order: POS Order ID
        printer_id: Specific printer to use (optional)
        
    Returns:
        Dict: Response with KOT details
            {
                "success": bool,
                "kot_id": str,
                "html": str,
                "items_sent": int,
                "timestamp": datetime
            }
    """
    if not pos_order:
        raise ValidationError(
            "POS Order ID is required",
            "Missing Data"
        )

    # Import here to avoid circular dependency
    from pos_restaurant_itb.api.create_kot import create_kot_from_pos_order

    try:
        # Create KOT
        kot_details = create_kot_from_pos_order(pos_order)
        kot_id = kot_details.get("kot_id")
        
        if not kot_id:
            raise KitchenError(
                "No additional items to send to kitchen",
                "No Items"
            )
        
        # Get KOT document
        kot_doc = frappe.get_doc("KOT", kot_id)
        
        # Render KOT template
        html = render_kot_template(
            kot_doc,
            printer_id
        )
        
        return {
            "success": True,
            "kot_id": kot_id,
            "html": html,
            "items_sent": len(kot_doc.kot_items),
            "timestamp": frappe.utils.now()
        }
        
    except Exception as e:
        log_error(e, pos_order)
        raise

@frappe.whitelist()
@handle_api_error
def cancel_pos_order_item(
    item_id: str,
    reason: Optional[str] = None
) -> Dict:
    """
    Cancel specific item in POS Order
    Only allowed for Outlet Manager
    
    Args:
        item_id: POS Order Item ID
        reason: Cancellation reason (optional)
        
    Returns:
        Dict: Cancellation status
            {
                "success": bool,
                "item_code": str,
                "reason": str,
                "amount_reduced": float,
                "timestamp": datetime
            }
    """
    # Validate manager role
    validate_manager_role(frappe.session.user)
    
    try:
        item = frappe.get_doc("POS Order Item", item_id)
        
        # Validate branch permission
        validate_branch_operation(
            item.branch,
            "cancel_order",
            frappe.session.user
        )
        
        # Store original amount for reduction
        original_amount = item.amount
        
        # Update item
        item.is_cancelled = 1
        item.cancellation_reason = reason or "Cancelled by manager"
        item.cancelled_by = frappe.session.user
        item.cancelled_at = frappe.utils.now()
        item.rate = 0
        item.amount = 0
        item.save()
        
        # Update parent order
        update_order_total(item.parent)
        
        # Notify cancellation
        notify_order_update(item.parent)
        
        return {
            "success": True,
            "item_code": item.item_code,
            "reason": item.cancellation_reason,
            "amount_reduced": original_amount,
            "timestamp": frappe.utils.now()
        }
        
    except Exception as e:
        log_error(e, f"Item: {item_id}")
        raise

@frappe.whitelist()
@handle_api_error
def mark_all_served(pos_order_id: str) -> Dict:
    """
    Mark all items in POS Order as Served
    
    Args:
        pos_order_id: POS Order ID
        
    Returns:
        Dict: Update status
            {
                "success": bool,
                "items_updated": int,
                "timestamp": datetime
            }
    """
    if not pos_order_id:
        raise ValidationError(
            "POS Order ID is required",
            "Missing Data"
        )
        
    try:
        order = frappe.get_doc("POS Order", pos_order_id)
        
        # Validate branch permission
        validate_branch_operation(
            order.branch,
            "update_order",
            frappe.session.user
        )
        
        updated_items = []
        
        for item in order.pos_order_items:
            if item.kot_status not in [KOTStatus.SERVED, KOTStatus.CANCELLED]:
                item.kot_status = KOTStatus.SERVED
                item.kot_last_update = frappe.utils.now()
                updated_items.append(item)
        
        if updated_items:
            order.save()
            
            # Update associated KDS
            update_kds_for_items(updated_items)
            
            # Notify update
            notify_order_update(order)
            
            return {
                "success": True,
                "items_updated": len(updated_items),
                "timestamp": frappe.utils.now()
            }
            
        return {
            "success": True,
            "items_updated": 0,
            "message": "No items needed update"
        }
        
    except Exception as e:
        log_error(e, pos_order_id)
        raise

def render_kot_template(kot_doc, printer_id: Optional[str] = None) -> str:
    """
    Render KOT HTML template
    
    Args:
        kot_doc: KOT document
        printer_id: Specific printer to use
        
    Returns:
        str: Rendered HTML
    """
    template_data = {
        "kot": kot_doc,
        "print_time": frappe.utils.now(),
        "printer_id": printer_id
    }
    
    return frappe.render_template(
        "templates/kot_print.html",
        template_data
    )

def update_order_total(order_id: str) -> None:
    """
    Recalculate and update order total
    
    Args:
        order_id: POS Order ID
    """
    order = frappe.get_doc("POS Order", order_id)
    
    total = sum(
        item.amount 
        for item in order.pos_order_items 
        if not item.is_cancelled
    )
    
    order.total_amount = total
    order.save()

def update_kds_for_items(items: List) -> None:
    """
    Update KDS status for updated items
    
    Args:
        items: List of updated items
    """
    from pos_restaurant_itb.api.kot_status_update import update_kds_status_from_kot
    
    processed_kots = set()
    
    for item in items:
        if item.kot_id and item.kot_id not in processed_kots:
            kds = frappe.db.get_value(
                "Kitchen Display Order",
                {"kot_id": item.kot_id},
                "name"
            )
            if kds:
                update_kds_status_from_kot(kds)
                processed_kots.add(item.kot_id)

def log_error(error: Exception, context: str) -> None:
    """
    Log operation error
    
    Args:
        error: Exception object
        context: Error context
    """
    error_msg = f"""
    Kitchen Operation Error
    ----------------------
    Context: {context}
    User: {frappe.session.user}
    Time: {frappe.utils.now()}
    Error: {str(error)}
    Traceback: {frappe.get_traceback()}
    """
    
    frappe.log_error(
        message=error_msg,
        title="❌ Kitchen Operation Error"
    )