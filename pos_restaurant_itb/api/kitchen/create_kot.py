# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:51:55'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.utils import now
from typing import List, Dict
from pos_restaurant_itb.utils.error_handlers import (
    handle_api_error,
    ValidationError,
    POSRestaurantError
)
from pos_restaurant_itb.utils.security import validate_branch_operation
from pos_restaurant_itb.utils.constants import KOTStatus
from pos_restaurant_itb.utils.realtime import notify_kot_update

@frappe.whitelist()
@handle_api_error
def create_kot_from_pos_order(pos_order_id: str) -> Dict:
    """
    Create Kitchen Order Ticket (KOT) from POS Order
    
    Args:
        pos_order_id: POS Order ID
        
    Returns:
        Dict: Created KOT details with status
        
    Raises:
        ValidationError: If validation fails
    """
    if not pos_order_id:
        raise ValidationError(
            "POS Order ID is required",
            "Missing Data"
        )
        
    frappe.logger().debug(f"📝 Starting KOT creation for POS Order: {pos_order_id}")
    
    pos_order = frappe.get_doc("POS Order", pos_order_id)
    validate_pos_order(pos_order)
    
    items_to_send = get_items_to_send(pos_order)
    if not items_to_send:
        raise ValidationError(
            "All items are already sent to kitchen or cancelled",
            "No Items"
        )
    
    try:
        kot = create_kot_document(pos_order, items_to_send)
        update_pos_order_items(pos_order, kot.name, items_to_send)
        
        # Create kitchen station orders
        create_kitchen_orders(kot)
        
        frappe.db.commit()
        
        frappe.logger().info(f"✅ KOT created successfully: {kot.name}")
        
        return {
            "success": True,
            "kot_id": kot.name,
            "table": kot.table,
            "timestamp": frappe.utils.now(),
            "items_count": len(items_to_send)
        }
        
    except Exception as e:
        frappe.db.rollback()
        log_error(e, pos_order_id)
        raise

def validate_pos_order(pos_order) -> None:
    """
    Validate POS Order status and permissions
    
    Args:
        pos_order: POS Order document
        
    Raises:
        ValidationError: If validation fails
    """
    if pos_order.docstatus != 0:
        raise ValidationError(
            "Cannot send finalized POS Order to kitchen",
            "Invalid Status"
        )
    
    validate_branch_operation(
        pos_order.branch,
        "create_kot",
        frappe.session.user
    )

def get_items_to_send(pos_order) -> List[Dict]:
    """
    Get items not yet sent to kitchen
    
    Args:
        pos_order: POS Order document
        
    Returns:
        List[Dict]: List of items to send
    """
    return [
        item for item in pos_order.pos_order_items
        if not item.sent_to_kitchen and not item.cancelled
    ]

def create_kot_document(pos_order, items_to_send) -> "Document":
    """
    Create new KOT document
    
    Args:
        pos_order: POS Order document
        items_to_send: List of items to include
        
    Returns:
        Document: Created KOT document
        
    Raises:
        POSRestaurantError: If creation fails
    """
    try:
        kot = frappe.get_doc({
            "doctype": "KOT",
            "pos_order": pos_order.name,
            "table": pos_order.table,
            "branch": pos_order.branch,
            "waiter": pos_order.waiter,
            "customer_name": pos_order.customer_name,
            "customer_count": pos_order.customer_count,
            "status": KOTStatus.NEW,
            "source": "POS",
            "creation": frappe.utils.now()
        })
        
        # Add items
        for item in items_to_send:
            kot.append("kot_items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "note": item.note,
                "kot_status": KOTStatus.NEW,
                "kitchen_station": get_kitchen_station(item.item_code),
                "preparation_time": get_preparation_time(item.item_code),
                "dynamic_attributes": frappe.as_json(
                    item.dynamic_attributes or []
                ),
                "order_id": pos_order.order_id
            })
            
        kot.insert(ignore_permissions=True)
        
        # Notify creation
        notify_kot_update(kot)
        
        return kot
        
    except Exception as e:
        log_error(e, pos_order.name)
        raise POSRestaurantError(
            f"Failed to create KOT: {str(e)}",
            "Creation Error"
        )

def update_pos_order_items(pos_order, kot_name: str, items_to_send: List) -> None:
    """
    Update POS Order items status
    
    Args:
        pos_order: POS Order document
        kot_name: Created KOT ID
        items_to_send: List of sent items
        
    Raises:
        POSRestaurantError: If update fails
    """
    try:
        for item in pos_order.pos_order_items:
            if item in items_to_send:
                item.sent_to_kitchen = 1
                item.kot_id = kot_name
                item.kot_status = KOTStatus.NEW
                item.kot_last_update = frappe.utils.now()
        
        pos_order.save(ignore_permissions=True)
        
    except Exception as e:
        log_error(e, pos_order.name)
        raise POSRestaurantError(
            f"Failed to update POS Order: {str(e)}",
            "Update Error"
        )

def create_kitchen_orders(kot) -> None:
    """
    Create kitchen display orders
    
    Args:
        kot: KOT document
    """
    try:
        # Group items by kitchen station
        station_items = {}
        for item in kot.kot_items:
            station = item.kitchen_station
            if station not in station_items:
                station_items[station] = []
            station_items[station].append(item)
        
        # Create order for each station
        for station, items in station_items.items():
            kds_doc = frappe.get_doc({
                "doctype": "Kitchen Display Order",
                "kot_id": kot.name,
                "table": kot.table,
                "kitchen_station": station,
                "status": KOTStatus.NEW,
                "branch": kot.branch,
                "creation": frappe.utils.now()
            })
            
            for item in items:
                kds_doc.append("items", {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "qty": item.qty,
                    "note": item.note,
                    "preparation_time": item.preparation_time
                })
            
            kds_doc.insert(ignore_permissions=True)
            
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create Kitchen Orders for KOT {kot.name}: {str(e)}",
            title="❌ Kitchen Order Creation Error"
        )
        frappe.msgprint(
            _("KOT created but failed to create Kitchen Orders. Please check error logs.")
        )

def get_kitchen_station(item_code: str) -> str:
    """Get assigned kitchen station for item"""
    return frappe.get_cached_value(
        "Item",
        item_code,
        "kitchen_station"
    )

def get_preparation_time(item_code: str) -> int:
    """Get standard preparation time for item"""
    return frappe.get_cached_value(
        "Item",
        item_code,
        "preparation_time"
    ) or 30  # Default 30 minutes

def log_error(error: Exception, pos_order_id: str) -> None:
    """
    Log detailed error information
    
    Args:
        error: Exception object
        pos_order_id: Related POS Order ID
    """
    error_msg = f"""
    KOT Creation Error
    -----------------
    POS Order: {pos_order_id}
    User: {frappe.session.user}
    Time: {frappe.utils.now()}
    Error: {str(error)}
    Traceback: {frappe.get_traceback()}
    """
    
    frappe.log_error(
        message=error_msg,
        title="❌ KOT Creation Error"
    )