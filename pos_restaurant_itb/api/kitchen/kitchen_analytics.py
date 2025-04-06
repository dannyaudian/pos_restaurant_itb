# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:39:16'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from pos_restaurant_itb.utils.error_handlers import handle_api_error
from pos_restaurant_itb.utils.constants import (
    KOTStatus,
    ErrorMessages,
    AnalyticsPeriod
)

@frappe.whitelist()
@handle_api_error
def get_kitchen_performance(
    branch: str,
    date_range: Dict,
    station: Optional[str] = None
) -> Dict:
    """
    Get analisis performa dapur
    
    Args:
        branch: ID branch
        date_range: Range tanggal
        station: ID station (optional)
        
    Returns:
        Dict: Performance metrics
    """
    start_date = date_range.get("start")
    end_date = date_range.get("end")
    
    filters = {
        "branch": branch,
        "creation": ["between", [start_date, end_date]],
        "docstatus": 1
    }
    
    if station:
        filters["kitchen_station"] = station
    
    # Get orders
    orders = frappe.get_all(
        "Kitchen Display Order",
        filters=filters,
        fields=[
            "name", "status", "creation", "last_updated",
            "priority", "kitchen_station"
        ]
    )
    
    # Initialize metrics
    metrics = {
        "total_orders": len(orders),
        "avg_preparation_time": 0,
        "completion_rate": 0,
        "on_time_rate": 0,
        "station_performance": {},
        "peak_load_times": [],
        "common_delays": []
    }
    
    if not orders:
        return metrics
        
    # Calculate detailed metrics
    prep_times = []
    completed = 0
    on_time = 0
    station_metrics = {}
    hour_load = [0] * 24
    delay_reasons = {}
    
    for order in orders:
        # Preparation time
        if order.status == KOTStatus.READY:
            prep_time = calculate_preparation_time(order)
            if prep_time:
                prep_times.append(prep_time)
                completed += 1
                
                # Check if completed on time
                if is_completed_on_time(order, prep_time):
                    on_time += 1
                else:
                    # Track delay reasons
                    delay_reason = get_delay_reason(order)
                    if delay_reason:
                        delay_reasons[delay_reason] = delay_reasons.get(delay_reason, 0) + 1
        
        # Station metrics
        station = order.kitchen_station
        if station not in station_metrics:
            station_metrics[station] = {
                "total": 0,
                "completed": 0,
                "avg_time": 0,
                "prep_times": []
            }
        
        station_metrics[station]["total"] += 1
        if order.status == KOTStatus.READY:
            station_metrics[station]["completed"] += 1
            if prep_time:
                station_metrics[station]["prep_times"].append(prep_time)
        
        # Hour load
        hour = frappe.utils.get_datetime(order.creation).hour
        hour_load[hour] += 1
    
    # Calculate final metrics
    if prep_times:
        metrics["avg_preparation_time"] = sum(prep_times) / len(prep_times)
    
    if metrics["total_orders"] > 0:
        metrics["completion_rate"] = (completed / metrics["total_orders"]) * 100
        
    if completed > 0:
        metrics["on_time_rate"] = (on_time / completed) * 100
    
    # Station performance
    for station, data in station_metrics.items():
        if data["prep_times"]:
            avg_time = sum(data["prep_times"]) / len(data["prep_times"])
        else:
            avg_time = 0
            
        metrics["station_performance"][station] = {
            "total_orders": data["total"],
            "completed_orders": data["completed"],
            "completion_rate": (data["completed"] / data["total"]) * 100 if data["total"] > 0 else 0,
            "avg_preparation_time": avg_time
        }
    
    # Peak load times
    max_load = max(hour_load)
    if max_load > 0:
        metrics["peak_load_times"] = [
            {
                "hour": hour,
                "orders": count,
                "percentage": (count / max_load) * 100
            }
            for hour, count in enumerate(hour_load)
            if count > 0
        ]
    
    # Common delays
    if delay_reasons:
        total_delays = sum(delay_reasons.values())
        metrics["common_delays"] = [
            {
                "reason": reason,
                "count": count,
                "percentage": (count / total_delays) * 100
            }
            for reason, count in sorted(
                delay_reasons.items(),
                key=lambda x: x[1],
                reverse=True
            )
        ]
    
    return metrics

@frappe.whitelist()
@handle_api_error
def get_efficiency_report(
    branch: str,
    period: str = AnalyticsPeriod.DAILY
) -> List[Dict]:
    """
    Get laporan efisiensi dapur
    
    Args:
        branch: ID branch
        period: Period analisis (daily/weekly/monthly)
        
    Returns:
        List[Dict]: Efficiency data points
    """
    if period not in AnalyticsPeriod.ALL:
        frappe.throw(_(ErrorMessages.INVALID_PERIOD))
    
    # Calculate date range
    end_date = frappe.utils.now_datetime()
    if period == AnalyticsPeriod.DAILY:
        start_date = end_date - timedelta(days=7)
        group_by = "DATE(creation)"
    elif period == AnalyticsPeriod.WEEKLY:
        start_date = end_date - timedelta(weeks=12)
        group_by = "YEARWEEK(creation)"
    else:  # Monthly
        start_date = end_date - timedelta(days=365)
        group_by = "DATE_FORMAT(creation, '%Y-%m')"
    
    # Get efficiency data
    data = frappe.db.sql(f"""
        SELECT 
            {group_by} as period,
            COUNT(*) as total_orders,
            AVG(
                TIMESTAMPDIFF(MINUTE, 
                    creation,
                    CASE 
                        WHEN status = 'Ready' THEN last_updated
                        ELSE NULL
                    END
                )
            ) as avg_prep_time,
            SUM(CASE WHEN status = 'Ready' THEN 1 ELSE 0 END) as completed_orders
        FROM `tabKitchen Display Order`
        WHERE 
            branch = %s AND
            creation BETWEEN %s AND %s AND
            docstatus = 1
        GROUP BY period
        ORDER BY period
    """, (branch, start_date, end_date), as_dict=1)
    
    # Calculate efficiency metrics
    for point in data:
        if point.total_orders > 0:
            point["completion_rate"] = (point.completed_orders / point.total_orders) * 100
        else:
            point["completion_rate"] = 0
            
        # Format period
        if period == AnalyticsPeriod.DAILY:
            point["period"] = frappe.utils.format_date(point.period)
        elif period == AnalyticsPeriod.WEEKLY:
            year, week = str(point.period)[:4], str(point.period)[4:]
            point["period"] = f"Week {week}, {year}"
    
    return data

def calculate_preparation_time(order: Dict) -> Optional[float]:
    """Calculate preparation time in minutes"""
    if not order.last_updated or not order.creation:
        return None
        
    return frappe.utils.time_diff_in_seconds(
        order.last_updated,
        order.creation
    ) / 60

def is_completed_on_time(order: Dict, actual_time: float) -> bool:
    """Check if order was completed within target time"""
    # Get target preparation time from items
    kot = frappe.get_doc("KOT", order.kot_id)
    max_target_time = max(
        (item.preparation_time for item in kot.kot_items),
        default=30  # Default 30 minutes
    )
    
    return actual_time <= max_target_time

def get_delay_reason(order: Dict) -> Optional[str]:
    """Get reason for delay if any"""
    logs = frappe.get_all(
        "Kitchen Order Log",
        filters={
            "order": order.name,
            "log_type": "Delay"
        },
        fields=["reason"],
        order_by="timestamp desc",
        limit=1
    )
    
    return logs[0].reason if logs else None