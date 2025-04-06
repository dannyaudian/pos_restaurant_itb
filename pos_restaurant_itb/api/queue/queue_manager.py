# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:38:09'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from pos_restaurant_itb.utils.error_handlers import handle_api_error
from pos_restaurant_itb.utils.constants import (
    KOTStatus, 
    OrderPriority, 
    ErrorMessages,
    CacheKeys
)
from pos_restaurant_itb.utils.realtime import notify_queue_update

@frappe.whitelist()
@handle_api_error
def get_kitchen_queue(
    branch: str,
    station: Optional[str] = None,
    status: Optional[List[str]] = None,
    priority: Optional[List[str]] = None
) -> List[Dict]:
    """
    Get antrian pesanan dapur
    
    Args:
        branch: ID branch
        station: ID station (optional)
        status: Filter by status
        priority: Filter by priority
        
    Returns:
        List[Dict]: List pesanan dalam antrian
    """
    filters = {
        "branch": branch,
        "docstatus": 1  # Submitted
    }
    
    if station:
        filters["kitchen_station"] = station
    if status:
        filters["status"] = ["in", status]
    if priority:
        filters["priority"] = ["in", priority]
        
    orders = frappe.get_all(
        "Kitchen Display Order",
        filters=filters,
        fields=[
            "name", "kot_id", "table", "status",
            "priority", "last_updated", "creation"
        ],
        order_by="priority desc, creation asc"
    )
    
    for order in orders:
        # Get items
        order["items"] = frappe.get_all(
            "KOT Item",
            filters={"parent": order.kot_id},
            fields=[
                "item_code", "item_name", "qty",
                "note", "kot_status", "preparation_time"
            ]
        )
        
        # Calculate remaining time
        order["estimated_completion"] = calculate_completion_time(order)
        
    return orders

@frappe.whitelist()
@handle_api_error
def update_order_priority(
    order_id: str, 
    priority: str
) -> Dict:
    """
    Update prioritas pesanan
    
    Args:
        order_id: ID pesanan
        priority: Prioritas baru
        
    Returns:
        Dict: Update status
    """
    if priority not in OrderPriority.ALL:
        frappe.throw(_(ErrorMessages.INVALID_PRIORITY))
        
    order = frappe.get_doc("Kitchen Display Order", order_id)
    old_priority = order.priority
    
    # Update priority
    order.priority = priority
    order.last_updated = frappe.utils.now()
    order.save()
    
    # Log perubahan
    log_doc = frappe.get_doc({
        "doctype": "Kitchen Order Log",
        "order": order_id,
        "kot": order.kot_id,
        "log_type": "Priority Change",
        "from_value": old_priority,
        "to_value": priority,
        "user": frappe.session.user,
        "timestamp": frappe.utils.now()
    }).insert()
    
    # Notify update
    notify_queue_update(order)
    
    return {
        "success": True,
        "order": order_id,
        "priority": priority,
        "timestamp": frappe.utils.now(),
        "log_id": log_doc.name
    }

@frappe.whitelist()
@handle_api_error
def get_queue_analytics(
    branch: str,
    date_range: Dict
) -> Dict:
    """
    Get queue analytics
    
    Args:
        branch: ID branch
        date_range: Range tanggal
        
    Returns:
        Dict: Analytics data
    """
    start_date = date_range.get("start")
    end_date = date_range.get("end")
    
    # Get order logs
    logs = frappe.db.sql("""
        SELECT 
            ko.order,
            ko.kot,
            ko.log_type,
            ko.from_value,
            ko.to_value,
            ko.timestamp,
            kdo.kitchen_station,
            kdo.priority
        FROM `tabKitchen Order Log` ko
        JOIN `tabKitchen Display Order` kdo ON ko.order = kdo.name
        WHERE 
            kdo.branch = %s AND
            ko.timestamp BETWEEN %s AND %s
        ORDER BY ko.timestamp
    """, (branch, start_date, end_date), as_dict=1)
    
    # Calculate metrics
    metrics = {
        "total_orders": len(set(log.order for log in logs)),
        "avg_preparation_time": 0,
        "priority_distribution": {},
        "station_load": {},
        "peak_hours": []
    }
    
    # Process logs
    preparation_times = []
    priority_counts = {}
    station_counts = {}
    hour_counts = [0] * 24
    
    for log in logs:
        if log.log_type == "Status Change":
            if log.from_value == KOTStatus.NEW and log.to_value == KOTStatus.READY:
                start_time = frappe.get_doc(
                    "Kitchen Order Log",
                    {"order": log.order, "log_type": "Creation"}
                ).timestamp
                
                prep_time = frappe.utils.time_diff_in_seconds(
                    log.timestamp,
                    start_time
                ) / 60  # Convert to minutes
                
                preparation_times.append(prep_time)
                
                hour = frappe.utils.get_datetime(log.timestamp).hour
                hour_counts[hour] += 1
                
        priority_counts[log.priority] = priority_counts.get(log.priority, 0) + 1
        station_counts[log.kitchen_station] = station_counts.get(log.kitchen_station, 0) + 1
    
    # Calculate final metrics
    if preparation_times:
        metrics["avg_preparation_time"] = sum(preparation_times) / len(preparation_times)
        
    total_orders = metrics["total_orders"]
    if total_orders > 0:
        metrics["priority_distribution"] = {
            priority: (count / total_orders) * 100
            for priority, count in priority_counts.items()
        }
        
        metrics["station_load"] = {
            station: (count / total_orders) * 100
            for station, count in station_counts.items()
        }
        
        metrics["peak_hours"] = [
            {
                "hour": hour,
                "count": count,
                "percentage": (count / max(hour_counts)) * 100
            }
            for hour, count in enumerate(hour_counts)
            if count > 0
        ]
    
    return metrics

def calculate_completion_time(order: Dict) -> Optional[str]:
    """
    Calculate estimated completion time
    
    Args:
        order: Order details
        
    Returns:
        Optional[str]: Estimated completion time
    """
    if not order.get("items"):
        return None
        
    # Get max preparation time from items
    max_prep_time = max(
        item.get("preparation_time", 0) 
        for item in order["items"]
    )
    
    if not max_prep_time:
        return None
        
    creation_time = frappe.utils.get_datetime(order.get("creation"))
    estimated_time = creation_time + timedelta(minutes=max_prep_time)
    
    return frappe.utils.get_datetime_str(estimated_time)