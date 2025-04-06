# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:55:39'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from pos_restaurant_itb.utils.error_handlers import (
    handle_api_error,
    ValidationError
)
from pos_restaurant_itb.utils.security import validate_branch_operation
from pos_restaurant_itb.utils.constants import (
    OrderStatus,
    TableStatus,
    CacheKeys
)

@frappe.whitelist()
@handle_api_error
def get_available_tables(
    branch: str,
    section: Optional[str] = None,
    capacity: Optional[int] = None
) -> Dict:
    """
    Get list of available tables for POS Order
    
    Tables are considered *in use* if there's a POS Order with status:
    - Draft
    - In Progress
    - Ready for Billing
    
    Args:
        branch: Branch code to get available tables from
        section: Filter by section (optional)
        capacity: Filter by minimum capacity (optional)
        
    Returns:
        Dict: Available tables with metadata
            {
                "total_tables": int,
                "available_count": int,
                "occupied_count": int,
                "reserved_count": int,
                "sections": [
                    {
                        "name": str,
                        "table_count": int
                    }
                ],
                "tables": [
                    {
                        "name": str,
                        "table_number": str,
                        "section": str,
                        "capacity": int,
                        "status": str,
                        "floor": str,
                        "coordinates": {
                            "x": int,
                            "y": int
                        },
                        "current_order": str,
                        "reservation": {
                            "id": str,
                            "customer": str,
                            "time": datetime
                        }
                    }
                ]
            }
            
    Raises:
        ValidationError: If branch is not provided or invalid
    """
    if not branch:
        raise ValidationError(
            "Branch is required",
            "Missing Data"
        )
    
    validate_branch_operation(
        branch,
        "view_tables",
        frappe.session.user
    )
    
    # Check cache
    cache_key = f"{CacheKeys.AVAILABLE_TABLES}:{branch}"
    if section:
        cache_key += f":{section}"
    if capacity:
        cache_key += f":{capacity}"
        
    tables_data = frappe.cache().get_value(cache_key)
    
    if not tables_data:
        # Get tables currently in use
        used_tables = get_used_tables(branch)
        
        # Base filters
        filters = {
            "branch": branch,
            "disabled": 0,
            "name": ["not in", used_tables or [""]]
        }
        
        if section:
            filters["section"] = section
        if capacity:
            filters["capacity"] = [">=", capacity]
        
        # Get available tables
        tables = frappe.get_all(
            "POS Table",
            filters=filters,
            fields=[
                "name", "table_number", "section",
                "capacity", "status", "floor",
                "coordinates", "current_order",
                "current_reservation"
            ],
            order_by="table_number"
        )
        
        # Get section statistics
        sections = frappe.db.sql("""
            SELECT 
                section,
                COUNT(*) as table_count
            FROM `tabPOS Table`
            WHERE 
                branch = %s AND
                disabled = 0
            GROUP BY section
        """, branch, as_dict=1)
        
        # Count by status
        status_counts = frappe.db.sql("""
            SELECT 
                status,
                COUNT(*) as count
            FROM `tabPOS Table`
            WHERE 
                branch = %s AND
                disabled = 0
            GROUP BY status
        """, branch, as_dict=1)
        
        # Process tables data
        for table in tables:
            # Get reservation details if any
            if table.current_reservation:
                reservation = frappe.get_doc(
                    "Table Reservation",
                    table.current_reservation
                )
                table["reservation"] = {
                    "id": reservation.name,
                    "customer": reservation.customer_name,
                    "time": reservation.reservation_time,
                    "status": reservation.status
                }
            
            # Parse coordinates
            if table.coordinates:
                table["coordinates"] = frappe.parse_json(table.coordinates)
            else:
                table["coordinates"] = {"x": 0, "y": 0}
        
        tables_data = {
            "total_tables": len(tables),
            "available_count": sum(
                s.count for s in status_counts 
                if s.status == TableStatus.AVAILABLE
            ),
            "occupied_count": sum(
                s.count for s in status_counts 
                if s.status == TableStatus.OCCUPIED
            ),
            "reserved_count": sum(
                s.count for s in status_counts 
                if s.status == TableStatus.RESERVED
            ),
            "sections": sections,
            "tables": tables
        }
        
        # Cache for 30 seconds
        frappe.cache().set_value(
            cache_key,
            tables_data,
            expires_in_sec=30
        )
        
        # Log for monitoring
        frappe.logger().debug(
            f"[{datetime.utcnow()}] Get Available Tables\n"
            f"Branch: {branch}\n"
            f"Section: {section}\n"
            f"Capacity: {capacity}\n"
            f"Total Available: {len(tables)}\n"
            f"Used Tables: {used_tables}"
        )
    
    return tables_data

@frappe.whitelist()
@handle_api_error
def get_table_status(table: str) -> Dict:
    """
    Get detailed status of a specific table
    
    Args:
        table: Table name/ID to check
        
    Returns:
        Dict: Table status details
            {
                "name": str,
                "table_number": str,
                "status": str,
                "current_order": {
                    "id": str,
                    "status": str,
                    "customer": str,
                    "amount": float,
                    "started_at": datetime
                },
                "last_order": {
                    "id": str,
                    "completed_at": datetime
                },
                "reservation": {
                    "id": str,
                    "customer": str,
                    "time": datetime,
                    "status": str
                },
                "section": str,
                "floor": str,
                "capacity": int,
                "coordinates": {
                    "x": int,
                    "y": int
                }
            }
    """
    if not table:
        raise ValidationError(
            "Table ID is required",
            "Missing Data"
        )
    
    # Check cache
    cache_key = f"{CacheKeys.TABLE_STATUS}:{table}"
    status_data = frappe.cache().get_value(cache_key)
    
    if not status_data:
        table_doc = frappe.get_doc("POS Table", table)
        
        status_data = {
            "name": table_doc.name,
            "table_number": table_doc.table_number,
            "status": table_doc.status,
            "section": table_doc.section,
            "floor": table_doc.floor,
            "capacity": table_doc.capacity,
            "coordinates": frappe.parse_json(table_doc.coordinates or "{}")
        }
        
        # Get current order details
        if table_doc.current_order:
            order = frappe.get_doc("POS Order", table_doc.current_order)
            status_data["current_order"] = {
                "id": order.name,
                "status": order.status,
                "customer": order.customer_name,
                "amount": order.grand_total,
                "started_at": order.creation
            }
        
        # Get last completed order
        last_order = frappe.get_value(
            "POS Order",
            {
                "table": table,
                "docstatus": 1,
                "status": OrderStatus.COMPLETED
            },
            ["name", "modified"],
            order_by="modified desc"
        )
        
        if last_order:
            status_data["last_order"] = {
                "id": last_order[0],
                "completed_at": last_order[1]
            }
        
        # Get reservation if any
        if table_doc.current_reservation:
            reservation = frappe.get_doc(
                "Table Reservation",
                table_doc.current_reservation
            )
            status_data["reservation"] = {
                "id": reservation.name,
                "customer": reservation.customer_name,
                "time": reservation.reservation_time,
                "status": reservation.status
            }
        
        # Cache for 15 seconds
        frappe.cache().set_value(
            cache_key,
            status_data,
            expires_in_sec=15
        )
    
    return status_data

def get_used_tables(branch: str) -> List[str]:
    """
    Get list of tables currently in use
    
    Args:
        branch: Branch to check
        
    Returns:
        List[str]: List of table IDs in use
    """
    return frappe.get_all(
        "POS Order",
        filters={
            "docstatus": ["<", 2],  # Not cancelled
            "status": ["in", [
                OrderStatus.DRAFT,
                OrderStatus.IN_PROGRESS,
                OrderStatus.READY_FOR_BILLING
            ]],
            "branch": branch
        },
        pluck="table"
    )