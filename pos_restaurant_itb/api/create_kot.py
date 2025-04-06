# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 09:29:47'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.utils import now
from pos_restaurant_itb.utils import (
    error_handlers,
    security,
    common
)
from pos_restaurant_itb.api.kitchen_station import create_kitchen_station_items_from_kot

@frappe.whitelist()
@error_handlers.handle_pos_errors()
def create_kot_from_pos_order(pos_order_id: str) -> str:
    """
    Create Kitchen Order Ticket (KOT) from POS Order
    
    Args:
        pos_order_id (str): POS Order ID
        
    Returns:
        str: Created KOT ID
        
    Raises:
        ValidationError: If validation fails
    """
    if not pos_order_id:
        raise error_handlers.ValidationError(
            "POS Order ID is required",
            "Validation Error"
        )
        
    frappe.logger().debug(f"📝 Starting KOT creation for POS Order: {pos_order_id}")
    
    pos_order = frappe.get_doc("POS Order", pos_order_id)
    validate_pos_order(pos_order)
    
    items_to_send = get_items_to_send(pos_order)
    if not items_to_send:
        raise error_handlers.ValidationError(
            "All items are already sent to kitchen or cancelled",
            "Validation Error"
        )
    
    try:
        kot = create_kot_document(pos_order, items_to_send)
        update_pos_order_items(pos_order, kot.name, items_to_send)
        frappe.db.commit()
        
        # Process Kitchen Station
        process_kitchen_station(kot.name)
        
        frappe.logger().info(f"✅ KOT created successfully: {kot.name}")
        return kot.name
        
    except Exception as e:
        frappe.db.rollback()
        log_error(e, pos_order_id)
        raise

def validate_pos_order(pos_order):
    """Validate POS Order status"""
    if pos_order.docstatus != 0:
        raise error_handlers.ValidationError(
            "Cannot send finalized POS Order to kitchen",
            "Status Error"
        )
    
    security.validate_branch_operation(
        pos_order.branch,
        "create_kot",
        frappe.session.user
    )

def get_items_to_send(pos_order):
    """Get items not yet sent to kitchen"""
    return [
        item for item in pos_order.pos_order_items
        if not item.sent_to_kitchen and not item.cancelled
    ]

def create_kot_document(pos_order, items_to_send):
    """Create new KOT document"""
    try:
        
        kot = frappe.new_doc("KOT")
        kot.update({
            "pos_order": pos_order.name,
            "table": pos_order.table,
            "branch": pos_order.branch,
            "kot_time": now(),
            "status": "New",
            "waiter": waiter
        })
        
        # Add items
        for item in items_to_send:
            kot.append("kot_items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "note": item.note,
                "kot_status": "Queued",
                "kot_last_update": now(),
                "dynamic_attributes": frappe.as_json(
                    item.dynamic_attributes or []
                ),
                "order_id": pos_order.order_id,
                "branch": pos_order.branch,
                "waiter": waiter
            })
            
        kot.insert(ignore_permissions=True)
        return kot
        
    except Exception as e:
        log_error(e, pos_order.name)
        raise error_handlers.POSRestaurantError(
            f"Failed to create KOT: {str(e)}",
            "Creation Error"
        )

def update_pos_order_items(pos_order, kot_name, items_to_send):
    """Update POS Order items status"""
    try:
        for item in pos_order.pos_order_items:
            if item in items_to_send:
                item.sent_to_kitchen = 1
                item.kot_id = kot_name
                item.kot_status = "Queued"
                item.kot_last_update = now()
        
        pos_order.save(ignore_permissions=True)
        
    except Exception as e:
        log_error(e, pos_order.name)
        raise error_handlers.POSRestaurantError(
            f"Failed to update POS Order: {str(e)}",
            "Update Error"
        )

def process_kitchen_station(kot_name):
    """Process Kitchen Station Items creation"""
    try:
        create_kitchen_station_items_from_kot(kot_name)
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create Kitchen Station Items for KOT {kot_name}: {str(e)}",
            title="❌ Kitchen Station Warning"
        )
        frappe.msgprint(
            _("KOT created successfully, but failed to add items to Kitchen Station.")
        )

def log_error(error, pos_order_id):
    """Log detailed error"""
    error_msg = f"""
    KOT Creation Error
    -----------------
    POS Order: {pos_order_id}
    User: {frappe.session.user}
    Time: {now()}
    Error: {str(error)}
    Traceback: {frappe.get_traceback()}
    """
    
    frappe.log_error(
        message=error_msg,
        title="❌ KOT Creation Error"
    )