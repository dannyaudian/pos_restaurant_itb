# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:43:36'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from pos_restaurant_itb.utils.error_handlers import handle_api_error
from pos_restaurant_itb.utils.constants import (
    OrderStatus,
    AnalyticsPeriod,
    ErrorMessages,
    CacheKeys
)

@frappe.whitelist()
@handle_api_error
def get_order_analytics(
    branch: str,
    date_range: Dict,
    stations: Optional[List[str]] = None
) -> Dict:
    """
    Get analisis pesanan
    
    Args:
        branch: ID branch
        date_range: Range tanggal
        stations: List kitchen stations (optional)
        
    Returns:
        Dict: Order analytics
    """
    start_date = date_range.get("start")
    end_date = date_range.get("end")
    
    # Initialize metrics
    metrics = {
        "summary": {
            "total_orders": 0,
            "total_items": 0,
            "avg_items_per_order": 0,
            "avg_preparation_time": 0,
            "peak_hours": []
        },
        "items": {
            "most_ordered": [],
            "longest_prep_time": [],
            "most_modified": []
        },
        "station_metrics": {},
        "trends": {
            "hourly": [],
            "daily": [],
            "item_combos": []
        }
    }
    
    # Get orders within date range
    orders = frappe.get_all(
        "Kitchen Display Order",
        filters={
            "branch": branch,
            "creation": ["between", [start_date, end_date]],
            "docstatus": 1,
            "kitchen_station": ["in", stations] if stations else ["!=", ""]
        },
        fields=[
            "name", "kot_id", "kitchen_station",
            "status", "creation", "modified",
            "priority"
        ]
    )
    
    if not orders:
        return metrics
    
    # Process orders
    hour_counts = [0] * 24
    station_data = {}
    item_data = {}
    daily_counts = {}
    
    for order in orders:
        # Get KOT items
        kot = frappe.get_doc("KOT", order.kot_id)
        items = kot.kot_items
        
        # Update summary metrics
        metrics["summary"]["total_orders"] += 1
        metrics["summary"]["total_items"] += len(items)
        
        # Hour tracking
        hour = frappe.utils.get_datetime(order.creation).hour
        hour_counts[hour] += 1
        
        # Daily tracking
        date = frappe.utils.get_datetime(order.creation).date()
        daily_counts[date] = daily_counts.get(date, 0) + 1
        
        # Station tracking
        station = order.kitchen_station
        if station not in station_data:
            station_data[station] = {
                "total_orders": 0,
                "total_items": 0,
                "avg_prep_time": 0,
                "prep_times": []
            }
        
        station_data[station]["total_orders"] += 1
        station_data[station]["total_items"] += len(items)
        
        # Calculate preparation time
        if order.status == OrderStatus.COMPLETED:
            prep_time = frappe.utils.time_diff_in_seconds(
                order.modified,
                order.creation
            ) / 60  # Convert to minutes
            
            station_data[station]["prep_times"].append(prep_time)
        
        # Item tracking
        for item in items:
            if item.item_code not in item_data:
                item_data[item.item_code] = {
                    "count": 0,
                    "prep_times": [],
                    "modifications": 0,
                    "combos": {}
                }
            
            item_data[item.item_code]["count"] += item.qty
            
            if item.note:
                item_data[item.item_code]["modifications"] += 1
            
            # Track item combinations
            for other_item in items:
                if other_item.item_code != item.item_code:
                    combo = tuple(sorted([item.item_code, other_item.item_code]))
                    item_data[item.item_code]["combos"][combo] = \
                        item_data[item.item_code]["combos"].get(combo, 0) + 1
    
    # Calculate final metrics
    
    # Summary metrics
    if metrics["summary"]["total_orders"] > 0:
        metrics["summary"]["avg_items_per_order"] = \
            metrics["summary"]["total_items"] / metrics["summary"]["total_orders"]
    
    # Peak hours
    max_hour_count = max(hour_counts)
    if max_hour_count > 0:
        metrics["summary"]["peak_hours"] = [
            {
                "hour": hour,
                "count": count,
                "percentage": (count / max_hour_count) * 100
            }
            for hour, count in enumerate(hour_counts)
            if count > 0
        ]
    
    # Station metrics
    for station, data in station_data.items():
        if data["prep_times"]:
            data["avg_prep_time"] = sum(data["prep_times"]) / len(data["prep_times"])
            
        metrics["station_metrics"][station] = {
            "total_orders": data["total_orders"],
            "total_items": data["total_items"],
            "avg_items_per_order": data["total_items"] / data["total_orders"],
            "avg_preparation_time": data["avg_prep_time"]
        }
    
    # Item analytics
    items_list = [(code, data) for code, data in item_data.items()]
    
    # Most ordered items
    most_ordered = sorted(
        items_list,
        key=lambda x: x[1]["count"],
        reverse=True
    )[:10]
    
    metrics["items"]["most_ordered"] = [
        {
            "item_code": code,
            "item_name": frappe.get_cached_value("Item", code, "item_name"),
            "count": data["count"]
        }
        for code, data in most_ordered
    ]
    
    # Most modified items
    most_modified = sorted(
        items_list,
        key=lambda x: x[1]["modifications"],
        reverse=True
    )[:10]
    
    metrics["items"]["most_modified"] = [
        {
            "item_code": code,
            "item_name": frappe.get_cached_value("Item", code, "item_name"),
            "modifications": data["modifications"]
        }
        for code, data in most_modified
    ]
    
    # Popular combinations
    all_combos = {}
    for _, data in item_data.items():
        for combo, count in data["combos"].items():
            all_combos[combo] = all_combos.get(combo, 0) + count
    
    popular_combos = sorted(
        all_combos.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    metrics["trends"]["item_combos"] = [
        {
            "items": [
                {
                    "item_code": code,
                    "item_name": frappe.get_cached_value("Item", code, "item_name")
                }
                for code in combo
            ],
            "count": count
        }
        for combo, count in popular_combos
    ]
    
    # Daily trends
    metrics["trends"]["daily"] = [
        {
            "date": frappe.utils.format_date(date),
            "count": count,
            "percentage": (count / metrics["summary"]["total_orders"]) * 100
        }
        for date, count in sorted(daily_counts.items())
    ]
    
    return metrics

@frappe.whitelist()
@handle_api_error
def get_comparative_analytics(
    branch: str,
    period: str = AnalyticsPeriod.DAILY
) -> List[Dict]:
    """
    Get analisis perbandingan
    
    Args:
        branch: ID branch
        period: Period analisis
        
    Returns:
        List[Dict]: Comparative data
    """
    if period not in AnalyticsPeriod.ALL:
        frappe.throw(_(ErrorMessages.INVALID_PERIOD))
    
    # Set date ranges
    end_date = frappe.utils.now_datetime()
    
    if period == AnalyticsPeriod.DAILY:
        start_date = end_date - timedelta(days=30)
        group_by = "DATE(creation)"
        date_format = "%Y-%m-%d"
    elif period == AnalyticsPeriod.WEEKLY:
        start_date = end_date - timedelta(weeks=12)
        group_by = "YEARWEEK(creation)"
        date_format = "Week %U, %Y"
    else:  # Monthly
        start_date = end_date - timedelta(days=365)
        group_by = "DATE_FORMAT(creation, '%Y-%m')"
        date_format = "%B %Y"
    
    # Get comparative data
    data = frappe.db.sql(f"""
        SELECT 
            {group_by} as period,
            COUNT(DISTINCT kot_id) as total_orders,
            COUNT(DISTINCT table) as unique_tables,
            COUNT(DISTINCT kitchen_station) as active_stations,
            AVG(
                TIMESTAMPDIFF(MINUTE, 
                    creation,
                    modified
                )
            ) as avg_prep_time,
            SUM(CASE WHEN priority = 'High' THEN 1 ELSE 0 END) as high_priority
        FROM `tabKitchen Display Order`
        WHERE 
            branch = %s AND
            creation BETWEEN %s AND %s AND
            docstatus = 1
        GROUP BY period
        ORDER BY period
    """, (branch, start_date, end_date), as_dict=1)
    
    # Enhance data
    for point in data:
        if isinstance(point.period, str):
            point["period_formatted"] = datetime.strptime(
                point.period,
                "%Y-%m-%d" if "-" in point.period else "%Y%m"
            ).strftime(date_format)
        else:
            # Handle YEARWEEK format
            year = str(point.period)[:4]
            week = str(point.period)[4:]
            point["period_formatted"] = f"Week {week}, {year}"
            
        # Calculate percentages
        if point.total_orders > 0:
            point["high_priority_rate"] = (point.high_priority / point.total_orders) * 100
            
    return data