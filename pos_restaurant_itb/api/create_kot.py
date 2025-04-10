# File: pos_restaurant_itb/api/create_kot.py

import frappe
import json
from frappe import _
from frappe.utils import now, now_datetime

@frappe.whitelist()
def create_kot_from_pos_order(pos_order_id: str):
    """
    Create a Kitchen Order Ticket (KOT) from POS Order.
    
    Args:
        pos_order_id: The ID of the POS Order
        
    Returns:
        Dict with status and KOT ID if successful
    """
    if not pos_order_id:
        frappe.throw(_("POS Order ID is required."))
    
    try:
        pos_order = frappe.get_doc("POS Order", pos_order_id)
        
        # Check if any items need to be sent to kitchen
        items_to_send = [
            item for item in pos_order.items 
            if not item.sent_to_kitchen and not item.cancelled
        ]
        
        if not items_to_send:
            return {
                "status": "warning",
                "message": _("No new items to send to kitchen.")
            }
        
        # Create new KOT
        kot = frappe.new_doc("Kitchen Order Ticket")
        kot.pos_order = pos_order.name
        kot.table = pos_order.table
        kot.branch = pos_order.branch
        kot.kot_time = now_datetime()
        kot.status = "New"
        
        # Get waiter from current user if not specified
        kot.waiter = get_waiter_from_user(frappe.session.user)
        
        # Add items to KOT
        for item in items_to_send:
            kot.append("kot_items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "note": item.note,
                "kot_status": "Queued",
                "kot_last_update": now_datetime(),
                # Copy variant attributes if available
                "variant_attributes": item.variant_attributes,
                "cancelled": False
            })
        
        # Insert KOT
        kot.insert(ignore_permissions=True)
        
        # Update POS Order items to mark them as sent to kitchen
        for item in items_to_send:
            frappe.db.set_value("POS Order Item", item.name, {
                "sent_to_kitchen": 1,
                "kot_id": kot.name
            })
        
        # Update POS Order status if needed
        if pos_order.status == "Draft":
            frappe.db.set_value("POS Order", pos_order.name, "status", "In Progress")
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Kitchen Order Ticket created successfully."),
            "kot_id": kot.name
        }
        
    except Exception as e:
        log_error(e, pos_order_id)
        return {
            "status": "error",
            "message": _("Error creating Kitchen Order Ticket: {0}").format(str(e))
        }

def get_waiter_from_user(user_id: str):
    """
    Get Employee ID from user, or return user_id if not found
    """
    emp = frappe.db.get_value("Employee", {"user_id": user_id}, "name", cache=True)
    return emp or user_id

def log_error(error: Exception, pos_order_id: str):
    """
    Log error with context
    """
    frappe.log_error(
        title=f"KOT Creation Error for POS Order {pos_order_id}",
        message=f"Error: {str(error)}\n\nTraceback: {frappe.get_traceback()}"
    )