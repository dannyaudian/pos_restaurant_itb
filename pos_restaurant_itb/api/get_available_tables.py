"""
GET Available Tables API
-----------------------
API to get list of available tables for POS Order.

Created: 2025-04-06 07:52:14
Author: dannyaudian
Owner: PT. Innovasi Terbaik Bangsa
"""

import frappe
from frappe import _
from typing import List, Dict

__created_date__ = '2025-04-06 07:52:14'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

@frappe.whitelist()
def get_available_tables(branch: str) -> List[Dict]:
    """
    Get list of active tables that are not being used by ongoing POS Orders.
    
    Tables are considered *in use* if there's a POS Order with status:
    - Draft
    - In Progress
    - Ready for Billing
    
    Args:
        branch (str): Branch code to get available tables from
        
    Returns:
        List[Dict]: List of available tables with their details
            [
                {
                    "name": "T01-JKT-R1",
                    "table_id": "T01",
                    "section": "Indoor",
                    "capacity": 4,
                    "current_status": "Available"
                },
                ...
            ]
            
    Raises:
        frappe.ValidationError: If branch is not provided or invalid
    """
    if not branch:
        frappe.throw(_("Branch is required."))
        
    # Validate branch exists
    if not frappe.db.exists("Branch", branch):
        frappe.throw(_("Invalid Branch: {0}").format(branch))

    # Get all tables currently in use in this branch
    used_tables = frappe.get_all(
        "POS Order",
        filters={
            "docstatus": ["<", 2],  # Not cancelled
            "status": ["in", [
                "Draft",
                "In Progress", 
                "Ready for Billing"
            ]],
            "branch": branch
        },
        pluck="table"
    )
    
    # Get all active tables in branch that are not in use
    available_tables = frappe.get_all(
        "POS Table",
        filters={
            "branch": branch,
            "is_active": 1,
            "current_status": ["in", ["Available", "Reserved"]],
            "name": ["not in", used_tables or [""]]
        },
        fields=[
            "name",
            "table_id",
            "section",
            "capacity",
            "current_status"
        ],
        order_by="table_id"
    )
    
    # Log for debugging
    frappe.logger().debug(
        f"[{__created_date__}] Get Available Tables for Branch {branch}\n"
        f"Used Tables: {used_tables}\n"
        f"Available Tables: {[t.get('name') for t in available_tables]}"
    )

    return available_tables

@frappe.whitelist()
def get_table_status(table: str) -> Dict:
    """
    Get detailed status of a specific table
    
    Args:
        table (str): Table name/ID to check
        
    Returns:
        Dict: Table status details
            {
                "name": "T01-JKT-R1",
                "table_id": "T01",
                "is_active": 1,
                "current_status": "Available",
                "current_order": None,
                "last_order": "POS-ORD-2025-00001"
            }
    """
    if not table:
        frappe.throw(_("Table ID is required."))
        
    # Get table details
    table_doc = frappe.get_doc("POS Table", table)
    
    # Get current active order
    current_order = frappe.db.get_value(
        "POS Order",
        {
            "table": table,
            "docstatus": ["<", 2],
            "status": ["in", ["Draft", "In Progress", "Ready for Billing"]]
        },
        "name"
    )
    
    # Get last completed order
    last_order = frappe.db.get_value(
        "POS Order",
        {
            "table": table,
            "docstatus": 1,
            "status": "Completed"
        },
        "name",
        order_by="creation desc"
    )
    
    return {
        "name": table_doc.name,
        "table_id": table_doc.table_id,
        "is_active": table_doc.is_active,
        "current_status": table_doc.current_status,
        "current_order": current_order,
        "last_order": last_order
    }