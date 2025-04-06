# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:36:55'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional
from datetime import datetime

from pos_restaurant_itb.utils.error_handlers import handle_api_error
from pos_restaurant_itb.utils.constants import TableStatus, ErrorMessages
from pos_restaurant_itb.utils.realtime import notify_table_update

@frappe.whitelist()
@handle_api_error
def update_table_status(
    table: str, 
    status: str, 
    notes: Optional[str] = None
) -> Dict:
    """
    Update status meja
    
    Args:
        table: ID meja
        status: Status baru (Available/Occupied/Reserved/Maintenance)
        notes: Catatan optional
        
    Returns:
        Dict: Status update details
    """
    if status not in TableStatus.ALL:
        frappe.throw(_(ErrorMessages.INVALID_TABLE_STATUS))
        
    table_doc = frappe.get_doc("POS Table", table)
    
    # Update status
    table_doc.status = status
    table_doc.notes = notes
    table_doc.last_updated = frappe.utils.now()
    table_doc.modified_by = frappe.session.user
    table_doc.save()
    
    # Log perubahan
    log_doc = frappe.get_doc({
        "doctype": "Table Status Log",
        "table": table,
        "previous_status": table_doc.get_doc_before_save().status,
        "new_status": status,
        "notes": notes,
        "user": frappe.session.user,
        "timestamp": frappe.utils.now()
    }).insert()
    
    # Notify realtime update
    notify_table_update(table_doc)
    
    return {
        "success": True,
        "table": table,
        "status": status,
        "timestamp": frappe.utils.now(),
        "log_id": log_doc.name
    }

@frappe.whitelist()
@handle_api_error
def get_table_status(
    branch: str,
    include_logs: bool = False
) -> List[Dict]:
    """
    Get status semua meja di branch
    
    Args:
        branch: ID branch
        include_logs: Include status history
        
    Returns:
        List[Dict]: List status meja
    """
    # Get tables with cache
    cache_key = f"table_status:{branch}"
    tables = frappe.cache().get_value(cache_key)
    
    if not tables:
        tables = frappe.get_all(
            "POS Table",
            filters={
                "branch": branch,
                "disabled": 0
            },
            fields=[
                "name", "table_number", "status",
                "capacity", "notes", "last_updated",
                "current_order", "server_assigned"
            ]
        )
        
        frappe.cache().set_value(
            cache_key, 
            tables,
            expires_in_sec=30
        )
    
    if include_logs:
        for table in tables:
            table["status_logs"] = frappe.get_all(
                "Table Status Log",
                filters={"table": table.name},
                fields=["status", "notes", "user", "timestamp"],
                order_by="timestamp desc",
                limit=5
            )
    
    return tables

@frappe.whitelist()
@handle_api_error
def get_table_analytics(
    branch: str,
    date_range: Dict
) -> Dict:
    """
    Get table usage analytics
    
    Args:
        branch: ID branch
        date_range: Range tanggal
        
    Returns:
        Dict: Analytics data
    """
    start_date = date_range.get("start")
    end_date = date_range.get("end")
    
    # Get status changes
    status_logs = frappe.db.sql("""
        SELECT 
            table,
            previous_status,
            new_status,
            TIMESTAMPDIFF(MINUTE, 
                LAG(timestamp) OVER (PARTITION BY table ORDER BY timestamp),
                timestamp
            ) as duration_mins
        FROM `tabTable Status Log`
        WHERE 
            branch = %s AND
            timestamp BETWEEN %s AND %s
        ORDER BY timestamp
    """, (branch, start_date, end_date), as_dict=1)
    
    # Calculate metrics
    metrics = {
        "total_tables": frappe.db.count(
            "POS Table",
            {"branch": branch, "disabled": 0}
        ),
        "status_distribution": {},
        "avg_occupation_time": 0,
        "peak_hours": [],
        "turnover_rate": 0
    }
    
    # Process logs for metrics
    total_occupied_mins = 0
    status_counts = {}
    hour_counts = [0] * 24
    
    for log in status_logs:
        if log.new_status == TableStatus.OCCUPIED:
            if log.duration_mins:
                total_occupied_mins += log.duration_mins
                hour = frappe.utils.get_datetime(log.timestamp).hour
                hour_counts[hour] += 1
                
        status_counts[log.new_status] = status_counts.get(log.new_status, 0) + 1
    
    # Calculate final metrics
    total_records = len(status_logs)
    if total_records > 0:
        metrics["status_distribution"] = {
            status: (count / total_records) * 100 
            for status, count in status_counts.items()
        }
        
        metrics["avg_occupation_time"] = total_occupied_mins / status_counts.get(
            TableStatus.OCCUPIED, 1
        )
        
        metrics["peak_hours"] = [
            {
                "hour": hour,
                "count": count,
                "percentage": (count / max(hour_counts)) * 100
            }
            for hour, count in enumerate(hour_counts)
            if count > 0
        ]
        
        metrics["turnover_rate"] = status_counts.get(
            TableStatus.OCCUPIED, 0
        ) / metrics["total_tables"]
    
    return metrics