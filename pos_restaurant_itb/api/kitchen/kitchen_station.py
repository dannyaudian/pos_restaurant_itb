# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 15:03:46'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional
import json
from datetime import datetime

from pos_restaurant_itb.utils.error_handlers import (
    handle_api_error,
    ValidationError,
    KitchenError
)
from pos_restaurant_itb.utils.security import validate_branch_operation
from pos_restaurant_itb.utils.constants import (
    KOTStatus,
    ErrorMessages
)
from pos_restaurant_itb.utils.realtime import notify_kitchen_update

@frappe.whitelist()
@handle_api_error
def create_kitchen_station_items_from_kot(kot_id: str) -> Dict:
    """
    Create kitchen station items from KOT
    Each item with qty > 1 will create multiple entries
    
    Args:
        kot_id: KOT document ID
        
    Returns:
        Dict: Creation status with details
            {
                "success": bool,
                "message": str,
                "kot_id": str,
                "items_created": int,
                "timestamp": datetime
            }
    """
    if not kot_id:
        raise ValidationError(
            "KOT ID is required",
            "Missing Data"
        )

    try:
        kot_doc = frappe.get_doc("KOT", kot_id)
    except frappe.DoesNotExistError:
        raise ValidationError(
            f"KOT {kot_id} not found",
            "Invalid KOT"
        )
    
    # Validate permission
    validate_branch_operation(
        kot_doc.branch,
        "create_kitchen",
        frappe.session.user
    )
    
    items_created = 0
    
    try:
        for item in kot_doc.kot_items:
            if item.is_cancelled:
                continue
            
            # Get or generate attribute summary
            attribute_summary = get_attribute_summary(
                item.dynamic_attributes,
                item.attribute_summary
            )
            
            # Check existing entries
            existing_count = get_existing_entries_count(
                kot_doc,
                item,
                attribute_summary
            )
            
            # Calculate remaining quantity
            remaining_qty = item.qty - existing_count
            if remaining_qty <= 0:
                continue
            
            # Create new entries
            for _ in range(remaining_qty):
                create_kitchen_station_entry(
                    kot_doc,
                    item,
                    attribute_summary
                )
                items_created += 1
        
        frappe.db.commit()
        
        # Log success
        log_creation_success(kot_id, items_created)
        
        return {
            "success": True,
            "message": f"Kitchen station items created from KOT {kot_id}",
            "kot_id": kot_id,
            "items_created": items_created,
            "timestamp": frappe.utils.now()
        }
        
    except Exception as e:
        frappe.db.rollback()
        log_error(e, kot_id)
        raise

def get_attribute_summary(
    dynamic_attributes: Optional[str],
    existing_summary: Optional[str] = None
) -> str:
    """
    Generate attribute summary from dynamic attributes
    
    Args:
        dynamic_attributes: JSON string of dynamic attributes
        existing_summary: Existing summary to use if available
        
    Returns:
        str: Formatted attribute summary
    """
    if existing_summary:
        return existing_summary
        
    try:
        attrs = json.loads(dynamic_attributes or "[]")
        if not attrs:
            return ""
            
        return ", ".join(
            f"{attr.get('name', '')}: {attr.get('value', '')}"
            for attr in attrs
            if attr.get('name') and attr.get('value')
        )
        
    except json.JSONDecodeError:
        frappe.log_error(
            message=f"Invalid dynamic attributes JSON: {dynamic_attributes}",
            title="❌ Attribute Processing Error"
        )
        return ""

def get_existing_entries_count(
    kot_doc,
    item,
    attribute_summary: str
) -> int:
    """
    Get count of existing kitchen station entries
    
    Args:
        kot_doc: KOT document
        item: KOT item
        attribute_summary: Processed attribute summary
        
    Returns:
        int: Count of existing entries
    """
    return frappe.db.count(
        "Kitchen Station",
        {
            "kot_id": kot_doc.name,
            "item_code": item.item_code,
            "attribute_summary": attribute_summary,
            "note": item.note or "",
            "branch": kot_doc.branch,
            "table": kot_doc.table
        }
    )

def create_kitchen_station_entry(
    kot_doc,
    item,
    attribute_summary: str
) -> None:
    """
    Create single kitchen station entry
    
    Args:
        kot_doc: KOT document
        item: KOT item
        attribute_summary: Processed attribute summary
    """
    kitchen_station = frappe.get_doc({
        "doctype": "Kitchen Station",
        "kot_id": kot_doc.name,
        "table": kot_doc.table,
        "branch": kot_doc.branch,
        "waiter": kot_doc.waiter,
        "customer_name": kot_doc.customer_name,
        "item_code": item.item_code,
        "item_name": item.item_name,
        "attribute_summary": attribute_summary,
        "note": item.note,
        "status": KOTStatus.NEW,
        "kitchen_station": get_kitchen_station(item.item_code),
        "preparation_time": get_preparation_time(item.item_code),
        "priority": kot_doc.priority,
        "creation": frappe.utils.now(),
        "owner": frappe.session.user
    })
    
    kitchen_station.insert(ignore_permissions=True)
    
    # Notify creation
    notify_kitchen_update(kitchen_station)

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

def log_creation_success(kot_id: str, items_created: int) -> None:
    """
    Log successful kitchen station creation
    
    Args:
        kot_id: KOT document ID
        items_created: Number of items created
    """
    frappe.logger().info(
        f"✅ Kitchen Station Creation Success\n"
        f"KOT: {kot_id}\n"
        f"Items Created: {items_created}\n"
        f"Created by: {frappe.session.user}\n"
        f"Timestamp: {frappe.utils.now()}"
    )

def log_error(error: Exception, kot_id: str) -> None:
    """
    Log kitchen station creation error
    
    Args:
        error: Exception object
        kot_id: Related KOT ID
    """
    error_msg = f"""
    Kitchen Station Creation Error
    ----------------------------
    KOT: {kot_id}
    User: {frappe.session.user}
    Time: {frappe.utils.now()}
    Error: {str(error)}
    Traceback: {frappe.get_traceback()}
    """
    
    frappe.log_error(
        message=error_msg,
        title="❌ Kitchen Station Creation Error"
    )