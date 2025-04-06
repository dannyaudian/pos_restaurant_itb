# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 08:28:53'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count
from typing import List, Dict, Any, Optional
from frappe.utils import cint

def get_cached_value(
    doctype: str,
    name: str,
    field: str,
    cache_timeout: int = 3600
) -> Any:
    """
    Get cached document field value
    
    Args:
        doctype (str): DocType name
        name (str): Document name
        field (str): Field to get
        cache_timeout (int, optional): Cache timeout in seconds. Defaults to 3600.
        
    Returns:
        Any: Field value
    """
    cache_key = f"{doctype}:{name}:{field}"
    value = frappe.cache().get_value(cache_key)
    
    if value is None:
        value = frappe.db.get_value(doctype, name, field)
        if value is not None:
            frappe.cache().set_value(
                cache_key,
                value,
                expires_in_sec=cache_timeout
            )
            
    return value

def bulk_insert(
    doctype: str,
    docs: List[Dict],
    chunk_size: int = 100
) -> None:
    """
    Efficiently insert multiple documents
    
    Args:
        doctype (str): DocType to insert into
        docs (List[Dict]): List of document data
        chunk_size (int, optional): Size of chunks. Defaults to 100.
    """
    for i in range(0, len(docs), chunk_size):
        chunk = docs[i:i + chunk_size]
        frappe.db.bulk_insert(
            doctype,
            fields=list(chunk[0].keys()),
            values=[tuple(d.values()) for d in chunk]
        )

def optimize_list_query(
    doctype: str,
    filters: Dict,
    fields: List[str],
    order_by: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict]:
    """
    Optimize list query performance
    
    Args:
        doctype (str): DocType to query
        filters (Dict): Query filters
        fields (List[str]): Fields to fetch
        order_by (str, optional): Order by clause. Defaults to None.
        limit (int, optional): Limit results. Defaults to None.
        
    Returns:
        List[Dict]: Query results
    """
    DocType = frappe.qb.DocType(doctype)
    query = frappe.qb.from_(DocType).select(*fields)
    
    # Apply filters
    for field, value in filters.items():
        if isinstance(value, (list, tuple)):
            operator, val = value
            if operator == "in":
                query = query.where(DocType[field].isin(val))
            elif operator == "between":
                query = query.where(DocType[field][val[0]:val[1]])
        else:
            query = query.where(DocType[field] == value)
            
    # Apply order by
    if order_by:
        field, order = order_by.split()
        query = query.orderby(
            field,
            order="desc" if order.lower() == "desc" else "asc"
        )
        
    # Apply limit
    if limit:
        query = query.limit(cint(limit))
        
    return query.run(as_dict=True)

def update_pos_order_stats(order: Document) -> None:
    """
    Update POS Order related statistics
    
    Args:
        order (Document): POS Order document
    """
    branch = order.branch
    date = order.creation.date()
    
    # Update branch statistics
    stats_key = f"branch_stats:{branch}:{date}"
    stats = frappe.cache().get_value(stats_key) or {
        "total_orders": 0,
        "total_amount": 0
    }
    
    stats["total_orders"] += 1
    stats["total_amount"] += order.total_amount
    
    frappe.cache().set_value(
        stats_key,
        stats,
        expires_in_sec=86400  # 24 hours
    )
    
    # Update table statistics if applicable
    if order.table:
        table_key = f"table_stats:{order.table}"
        table_stats = frappe.cache().get_value(table_key) or {
            "total_orders": 0,
            "occupied_time": 0
        }
        
        table_stats["total_orders"] += 1
        
        frappe.cache().set_value(
            table_key,
            table_stats,
            expires_in_sec=86400  # 24 hours
        )

def cleanup_old_data() -> None:
    """Cleanup old temporary data"""
    # Cleanup old logs
    frappe.db.sql("""
        DELETE FROM `tabError Log`
        WHERE creation < DATE_SUB(NOW(), INTERVAL 30 DAY)
    """)
    
    # Cleanup old sessions
    frappe.db.sql("""
        DELETE FROM `tabSessions`
        WHERE lastupdate < DATE_SUB(NOW(), INTERVAL 7 DAY)
    """)
    
    # Clear cache older than 24 hours
    frappe.cache().delete_keys("pos_restaurant_itb:*")

def update_stats() -> None:
    """Update system-wide statistics"""
    today = frappe.utils.today()
    
    # Update order statistics
    orders = frappe.get_all(
        "POS Order",
        filters={"creation": [">=", today]},
        fields=["branch", "total_amount", "status"]
    )
    
    stats = {}
    for order in orders:
        branch = order.branch
        if branch not in stats:
            stats[branch] = {
                "total_orders": 0,
                "total_amount": 0,
                "completed": 0,
                "cancelled": 0
            }
        
        stats[branch]["total_orders"] += 1
        stats[branch]["total_amount"] += order.total_amount
        
        if order.status == "Completed":
            stats[branch]["completed"] += 1
        elif order.status == "Cancelled":
            stats[branch]["cancelled"] += 1
    
    # Cache statistics
    for branch, data in stats.items():
        frappe.cache().set_value(
            f"branch_stats:{branch}:{today}",
            data,
            expires_in_sec=86400
        )

def optimize_db_queries() -> None:
    """Optimize database queries"""
    # Add index for frequently used fields
    add_index_if_missing("POS Order", ["status", "branch", "creation"])
    add_index_if_missing("POS Order Item", ["item_code", "kot_status"])
    
def add_index_if_missing(doctype: str, fields: List[str]) -> None:
    """Add database index if missing"""
    from frappe.model.utils import add_index
    
    for field in fields:
        try:
            add_index(doctype, field)
        except Exception as e:
            frappe.log_error(f"Failed to add index {field} to {doctype}: {str(e)}")