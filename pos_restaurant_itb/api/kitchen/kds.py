# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 15:00:12'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional
from datetime import datetime

from pos_restaurant_itb.utils.error_handlers import (
    handle_api_error,
    ValidationError,
    KitchenError
)
from pos_restaurant_itb.utils.security import validate_branch_operation
from pos_restaurant_itb.utils.constants import (
    OrderStatus,
    KOTStatus,
    ErrorMessages,
    CacheKeys
)
from pos_restaurant_itb.utils.realtime import notify_kds_update

@frappe.whitelist()
@handle_api_error
def get_kds_dashboard(
    branch: str,
    station: Optional[str] = None
) -> Dict:
    """
    Get Kitchen Display System dashboard data
    
    Args:
        branch: Branch code
        station: Kitchen station filter (optional)
        
    Returns:
        Dict: KDS dashboard data
            {
                "summary": {
                    "total_orders": int,
                    "pending_orders": int,
                    "in_progress": int,
                    "delayed": int,
                    "avg_preparation_time": float
                },
                "stations": [
                    {
                        "name": str,
                        "order_count": int,
                        "status": str
                    }
                ],
                "orders": [
                    {
                        "id": str,
                        "table": str,
                        "status": str,
                        "priority": str,
                        "creation_time": datetime,
                        "preparation_time": int,
                        "items": [
                            {
                                "item_code": str,
                                "item_name": str,
                                "qty": int,
                                "status": str,
                                "note": str
                            }
                        ]
                    }
                ]
            }
    """
    # Validate permission
    validate_branch_operation(
        branch,
        "view_kds",
        frappe.session.user
    )
    
    # Check cache
    cache_key = f"{CacheKeys.KDS_DASHBOARD}:{branch}"
    if station:
        cache_key += f":{station}"
        
    dashboard_data = frappe.cache().get_value(cache_key)
    
    if not dashboard_data:
        # Base filters
        filters = {
            "branch": branch,
            "status": ["in", [
                OrderStatus.NEW,
                OrderStatus.IN_PROGRESS
            ]]
        }
        
        if station:
            filters["kitchen_station"] = station
        
        # Get active orders
        orders = frappe.get_all(
            "Kitchen Display Order",
            filters=filters,
            fields=[
                "name", "table", "status", "priority",
                "creation", "kitchen_station",
                "special_instructions", "waiter"
            ],
            order_by="creation asc"
        )
        
        # Process orders
        processed_orders = []
        for order in orders:
            order_doc = frappe.get_doc(
                "Kitchen Display Order",
                order.name
            )
            
            # Calculate preparation time
            prep_time = max(
                (item.preparation_time for item in order_doc.items),
                default=30
            )
            
            processed_orders.append({
                "id": order.name,
                "table": order.table,
                "status": order.status,
                "priority": order.priority,
                "creation_time": order.creation,
                "preparation_time": prep_time,
                "kitchen_station": order.kitchen_station,
                "special_instructions": order.special_instructions,
                "waiter": order.waiter,
                "items": [
                    {
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "qty": item.qty,
                        "status": item.status,
                        "note": item.note,
                        "preparation_time": item.preparation_time
                    }
                    for item in order_doc.items
                ]
            })
        
        # Get station statistics
        stations = frappe.db.sql("""
            SELECT 
                kitchen_station as name,
                COUNT(*) as order_count,
                MAX(status) as status
            FROM `tabKitchen Display Order`
            WHERE
                branch = %s AND
                status IN ('New', 'In Progress')
            GROUP BY kitchen_station
        """, branch, as_dict=1)
        
        # Calculate summary metrics
        delayed_count = 0
        total_prep_time = 0
        completed_orders = 0
        
        for order in processed_orders:
            current_time = frappe.utils.now_datetime()
            order_time = frappe.utils.get_datetime(order.get("creation_time"))
            prep_time = order.get("preparation_time", 30)
            
            if (current_time - order_time).total_seconds() / 60 > prep_time:
                delayed_count += 1
            
            if order.get("status") == OrderStatus.COMPLETED:
                total_prep_time += (
                    frappe.utils.time_diff_in_seconds(
                        order.get("completion_time"),
                        order.get("creation_time")
                    ) / 60
                )
                completed_orders += 1
        
        dashboard_data = {
            "summary": {
                "total_orders": len(processed_orders),
                "pending_orders": len([
                    o for o in processed_orders
                    if o["status"] == OrderStatus.NEW
                ]),
                "in_progress": len([
                    o for o in processed_orders
                    if o["status"] == OrderStatus.IN_PROGRESS
                ]),
                "delayed": delayed_count,
                "avg_preparation_time": (
                    total_prep_time / completed_orders
                    if completed_orders > 0 else 0
                )
            },
            "stations": stations,
            "orders": processed_orders
        }
        
        # Cache for 15 seconds
        frappe.cache().set_value(
            cache_key,
            dashboard_data,
            expires_in_sec=15
        )
    
    return dashboard_data

@frappe.whitelist()
@handle_api_error
def update_order_status(
    order_id: str,
    new_status: str,
    items: Optional[List[Dict]] = None
) -> Dict:
    """
    Update KDS order status
    
    Args:
        order_id: KDS order ID
        new_status: New status to set
        items: List of items with new status (optional)
        
    Returns:
        Dict: Update status
    """
    if new_status not in OrderStatus.ALL:
        raise ValidationError(
            f"Invalid status: {new_status}",
            "Invalid Status"
        )
    
    order = frappe.get_doc("Kitchen Display Order", order_id)
    
    # Validate permission
    validate_branch_operation(
        order.branch,
        "update_kds",
        frappe.session.user
    )
    
    try:
        # Update order status
        order.status = new_status
        order.modified_by = frappe.session.user
        order.modified = frappe.utils.now()
        
        # Update specific items if provided
        if items:
            for item_update in items:
                for item in order.items:
                    if item.name == item_update.get("name"):
                        item.status = item_update.get("status")
                        item.modified = frappe.utils.now()
        
        order.save()
        
        # Update associated KOT
        update_kot_status(order)
        
        # Notify update
        notify_kds_update(order)
        
        return {
            "success": True,
            "order_id": order_id,
            "status": new_status,
            "timestamp": frappe.utils.now()
        }
        
    except Exception as e:
        frappe.db.rollback()
        log_error(e, order_id)
        raise

def update_kot_status(order) -> None:
    """
    Update associated KOT status
    
    Args:
        order: KDS order document
    """
    try:
        kot = frappe.get_doc("KOT", order.kot_id)
        kot.status = order.status
        
        for kot_item in kot.kot_items:
            matching_kds_item = next(
                (item for item in order.items 
                 if item.item_code == kot_item.item_code),
                None
            )
            if matching_kds_item:
                kot_item.kot_status = matching_kds_item.status
                kot_item.kot_last_update = frappe.utils.now()
        
        kot.save()
        
    except Exception as e:
        frappe.log_error(
            message=f"Failed to update KOT {order.kot_id}: {str(e)}",
            title="❌ KOT Update Error"
        )
        raise KitchenError(
            f"Failed to update KOT status: {str(e)}",
            "Update Error"
        )

def log_error(error: Exception, order_id: str) -> None:
    """
    Log KDS operation error
    
    Args:
        error: Exception object
        order_id: Related order ID
    """
    error_msg = f"""
    KDS Operation Error
    ------------------
    Order: {order_id}
    User: {frappe.session.user}
    Time: {frappe.utils.now()}
    Error: {str(error)}
    Traceback: {frappe.get_traceback()}
    """
    
    frappe.log_error(
        message=error_msg,
        title="❌ KDS Operation Error"
    )