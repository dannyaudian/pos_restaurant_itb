# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:49:54'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta

from pos_restaurant_itb.utils.error_handlers import handle_api_error
from pos_restaurant_itb.utils.constants import (
    AnalyticsPeriod,
    OrderStatus,
    PaymentStatus,
    ErrorMessages
)

@frappe.whitelist()
@handle_api_error
def get_operational_dashboard(
    branch: str,
    date: Optional[str] = None
) -> Dict:
    """
    Get dashboard metrik operasional
    
    Args:
        branch: ID branch
        date: Tanggal (default: hari ini)
        
    Returns:
        Dict: Operational metrics
    """
    if not date:
        date = frappe.utils.today()
    
    # Initialize metrics
    metrics = {
        "summary": {
            "total_orders": 0,
            "total_revenue": 0,
            "avg_order_value": 0,
            "table_turnover_rate": 0
        },
        "orders": {
            "completed": 0,
            "in_progress": 0,
            "cancelled": 0,
            "by_source": {}
        },
        "tables": {
            "total": 0,
            "occupied": 0,
            "available": 0,
            "reserved": 0
        },
        "kitchen": {
            "active_orders": 0,
            "avg_preparation_time": 0,
            "delayed_orders": 0
        },
        "payments": {
            "completed": 0,
            "pending": 0,
            "by_method": {}
        },
        "peak_hours": [],
        "trending_items": []
    }
    
    # Get orders for the day
    orders = frappe.get_all(
        "KOT",
        filters={
            "branch": branch,
            "posting_date": date,
            "docstatus": 1
        },
        fields=[
            "name", "status", "source", "grand_total",
            "payment_status", "payment_method",
            "creation", "table"
        ]
    )
    
    if not orders:
        return metrics
    
    # Process orders
    hour_counts = [0] * 24
    payment_methods = {}
    order_sources = {}
    
    for order in orders:
        # Summary metrics
        metrics["summary"]["total_orders"] += 1
        metrics["summary"]["total_revenue"] += order.grand_total
        
        # Order status
        if order.status == OrderStatus.COMPLETED:
            metrics["orders"]["completed"] += 1
        elif order.status == OrderStatus.IN_PROGRESS:
            metrics["orders"]["in_progress"] += 1
        elif order.status == OrderStatus.CANCELLED:
            metrics["orders"]["cancelled"] += 1
        
        # Order source
        source = order.source or "POS"
        order_sources[source] = order_sources.get(source, 0) + 1
        
        # Payment method
        if order.payment_status == PaymentStatus.COMPLETED:
            method = order.payment_method or "Cash"
            payment_methods[method] = payment_methods.get(method, 0) + 1
            metrics["payments"]["completed"] += 1
        elif order.payment_status == PaymentStatus.PENDING:
            metrics["payments"]["pending"] += 1
        
        # Hour tracking
        hour = frappe.utils.get_datetime(order.creation).hour
        hour_counts[hour] += 1
    
    # Calculate averages
    if metrics["summary"]["total_orders"] > 0:
        metrics["summary"]["avg_order_value"] = \
            metrics["summary"]["total_revenue"] / metrics["summary"]["total_orders"]
    
    # Get table status
    table_status = frappe.db.sql("""
        SELECT 
            status,
            COUNT(*) as count
        FROM `tabPOS Table`
        WHERE 
            branch = %s AND
            disabled = 0
        GROUP BY status
    """, branch, as_dict=1)
    
    for status in table_status:
        if status.status == "Available":
            metrics["tables"]["available"] = status.count
        elif status.status == "Occupied":
            metrics["tables"]["occupied"] = status.count
        elif status.status == "Reserved":
            metrics["tables"]["reserved"] = status.count
            
    metrics["tables"]["total"] = sum(s.count for s in table_status)
    
    # Calculate table turnover
    if metrics["tables"]["total"] > 0:
        metrics["summary"]["table_turnover_rate"] = \
            metrics["orders"]["completed"] / metrics["tables"]["total"]
    
    # Get kitchen metrics
    kitchen_metrics = get_kitchen_metrics(branch, date)
    metrics["kitchen"].update(kitchen_metrics)
    
    # Process hour counts
    max_hour_count = max(hour_counts)
    if max_hour_count > 0:
        metrics["peak_hours"] = [
            {
                "hour": hour,
                "count": count,
                "percentage": (count / max_hour_count) * 100
            }
            for hour, count in enumerate(hour_counts)
            if count > 0
        ]
    
    # Get trending items
    metrics["trending_items"] = get_trending_items(branch, date)
    
    # Format source and payment methods
    metrics["orders"]["by_source"] = {
        source: {
            "count": count,
            "percentage": (count / metrics["summary"]["total_orders"]) * 100
        }
        for source, count in order_sources.items()
    }
    
    metrics["payments"]["by_method"] = {
        method: {
            "count": count,
            "percentage": (count / metrics["payments"]["completed"]) * 100
            if metrics["payments"]["completed"] > 0 else 0
        }
        for method, count in payment_methods.items()
    }
    
    return metrics

@frappe.whitelist()
@handle_api_error
def get_performance_trends(
    branch: str,
    period: str = AnalyticsPeriod.DAILY,
    metrics: Optional[List[str]] = None
) -> Dict[str, List[Dict]]:
    """
    Get tren performa
    
    Args:
        branch: ID branch
        period: Period analisis
        metrics: List metrik yang diminta
        
    Returns:
        Dict[str, List[Dict]]: Performance trends
    """
    if period not in AnalyticsPeriod.ALL:
        frappe.throw(_(ErrorMessages.INVALID_PERIOD))
    
    if not metrics:
        metrics = ["orders", "revenue", "avg_order_value"]
    
    # Set date ranges
    end_date = frappe.utils.now_datetime()
    
    if period == AnalyticsPeriod.DAILY:
        start_date = end_date - timedelta(days=30)
        group_by = "DATE(posting_date)"
        date_format = "%Y-%m-%d"
    elif period == AnalyticsPeriod.WEEKLY:
        start_date = end_date - timedelta(weeks=12)
        group_by = "YEARWEEK(posting_date)"
        date_format = "Week %U, %Y"
    else:  # Monthly
        start_date = end_date - timedelta(days=365)
        group_by = "DATE_FORMAT(posting_date, '%Y-%m')"
        date_format = "%B %Y"
    
    # Get base data
    data = frappe.db.sql(f"""
        SELECT 
            {group_by} as period,
            COUNT(*) as total_orders,
            SUM(grand_total) as total_revenue,
            AVG(grand_total) as avg_order_value,
            COUNT(DISTINCT table) as unique_tables,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_orders,
            AVG(
                TIMESTAMPDIFF(MINUTE, 
                    creation,
                    modified
                )
            ) as avg_preparation_time
        FROM `tabKOT`
        WHERE 
            branch = %s AND
            posting_date BETWEEN %s AND %s AND
            docstatus = 1
        GROUP BY period
        ORDER BY period
    """, (branch, start_date, end_date), as_dict=1)
    
    # Initialize trends
    trends = {metric: [] for metric in metrics}
    
    # Process data points
    for point in data:
        if "orders" in metrics:
            trends["orders"].append({
                "period": format_period(point.period, period),
                "total": point.total_orders,
                "completed": point.completed_orders,
                "completion_rate": (point.completed_orders / point.total_orders * 100)
                if point.total_orders > 0 else 0
            })
        
        if "revenue" in metrics:
            trends["revenue"].append({
                "period": format_period(point.period, period),
                "amount": point.total_revenue,
                "per_table": (point.total_revenue / point.unique_tables)
                if point.unique_tables > 0 else 0
            })
        
        if "avg_order_value" in metrics:
            trends["avg_order_value"].append({
                "period": format_period(point.period, period),
                "amount": point.avg_order_value
            })
        
        if "preparation_time" in metrics:
            trends["preparation_time"].append({
                "period": format_period(point.period, period),
                "minutes": point.avg_preparation_time
            })
    
    return trends

def get_kitchen_metrics(branch: str, date: str) -> Dict:
    """Get kitchen performance metrics"""
    metrics = {
        "active_orders": 0,
        "avg_preparation_time": 0,
        "delayed_orders": 0
    }
    
    # Get active kitchen orders
    active_orders = frappe.get_all(
        "Kitchen Display Order",
        filters={
            "branch": branch,
            "creation": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]],
            "status": ["in", ["New", "In Progress"]]
        },
        fields=["name", "creation", "kot_id"]
    )
    
    metrics["active_orders"] = len(active_orders)
    
    # Get completed orders for the day
    completed_orders = frappe.get_all(
        "Kitchen Display Order",
        filters={
            "branch": branch,
            "creation": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]],
            "status": "Ready"
        },
        fields=["name", "creation", "modified"]
    )
    
    if completed_orders:
        # Calculate average preparation time
        prep_times = []
        for order in completed_orders:
            prep_time = frappe.utils.time_diff_in_seconds(
                order.modified,
                order.creation
            ) / 60  # Convert to minutes
            prep_times.append(prep_time)
        
        if prep_times:
            metrics["avg_preparation_time"] = sum(prep_times) / len(prep_times)
    
    # Count delayed orders
    for order in active_orders:
        kot = frappe.get_doc("KOT", order.kot_id)
        max_prep_time = max(
            (item.preparation_time for item in kot.kot_items),
            default=30  # Default 30 minutes
        )
        
        current_time = frappe.utils.now_datetime()
        order_time = frappe.utils.get_datetime(order.creation)
        
        if (current_time - order_time).total_seconds() / 60 > max_prep_time:
            metrics["delayed_orders"] += 1
    
    return metrics

def get_trending_items(branch: str, date: str) -> List[Dict]:
    """Get trending items for the day"""
    items = frappe.db.sql("""
        SELECT 
            koti.item_code,
            koti.item_name,
            COUNT(*) as order_count,
            SUM(koti.qty) as total_qty,
            AVG(koti.rate) as avg_rate
        FROM `tabKOT Item` koti
        JOIN `tabKOT` kot ON kot.name = koti.parent
        WHERE 
            kot.branch = %s AND
            kot.posting_date = %s AND
            kot.docstatus = 1
        GROUP BY koti.item_code
        ORDER BY order_count DESC
        LIMIT 10
    """, (branch, date), as_dict=1)
    
    return items

def format_period(period: Union[str, int], period_type: str) -> str:
    """Format period based on type"""
    if period_type == AnalyticsPeriod.DAILY:
        return frappe.utils.format_date(period)
    elif period_type == AnalyticsPeriod.WEEKLY:
        year = str(period)[:4]
        week = str(period)[4:]
        return f"Week {week}, {year}"
    else:  # Monthly
        return datetime.strptime(period, "%Y-%m").strftime("%B %Y")