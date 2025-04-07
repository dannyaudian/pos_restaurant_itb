# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 09:47:18'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _, whitelist
from frappe.utils import now_datetime, flt, cint
from typing import Dict, List, Optional, Union, Any
from pos_restaurant_itb.utils.error_handlers import handle_pos_errors, ValidationError
from pos_restaurant_itb.api.kitchen.kot_status_update import update_kds_status_from_kot
from pos_restaurant_itb.utils.constants import KOT_STATUSES, WORKING_HOURS

@handle_pos_errors()
def get_waiter_name(user: Optional[str] = None) -> str:
    """
    Get waiter name with caching
    
    Args:
        user (str, optional): User ID. Defaults to current user.
        
    Returns:
        str: Waiter name (employee name or user ID)
        
    Notes:
        - Returns employee name if user is linked to an employee
        - Returns user ID if user is System Manager
        - Caches result for 1 hour
    """
    user = user or frappe.session.user
    cache_key = f"waiter_name:{user}"
    
    # Try to get from cache first
    cached = frappe.cache().get_value(cache_key)
    if cached:
        return cached
        
    # System Manager uses user ID
    if "System Manager" in frappe.get_roles(user):
        result = user
    else:
        # Get employee details
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": user},
            ["employee_name", "name", "branch"],
            as_dict=True,
            cache=True
        )
        result = employee.employee_name if employee else user
    
    # Cache the result
    frappe.cache().set_value(
        cache_key,
        result,
        expires_in_sec=3600
    )
    
    frappe.logger().debug(f"Get waiter name for {user}: {result}")
    return result

@handle_pos_errors()
def get_branch_from_user(user: Optional[str] = None) -> str:
    """
    Get branch assigned to user
    
    Args:
        user (str, optional): User ID. Defaults to current user.
        
    Returns:
        str: Branch code
        
    Raises:
        ValidationError: If no branch is assigned
    """
    user = user or frappe.session.user
    cache_key = f"user_branch:{user}"
    
    # Try cache first
    cached = frappe.cache().get_value(cache_key)
    if cached:
        return cached
    
    # Get from employee record
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["name", "branch"],
        as_dict=True,
        cache=True
    )
    
    if not employee or not employee.branch:
        raise ValidationError(
            "No branch assigned to user",
            "Branch Assignment Error"
        )
    
    # Cache result
    frappe.cache().set_value(
        cache_key,
        employee.branch,
        expires_in_sec=3600
    )
    
    return employee.branch

@whitelist()
@handle_pos_errors()
def get_new_order_id(branch: str) -> str:
    """
    Generate new order ID for branch
    
    Args:
        branch (str): Branch code
        
    Returns:
        str: New order ID
        
    Raises:
        ValidationError: If branch is invalid
    """
    if not branch:
        raise ValidationError("Branch is required", "Validation Error")

    # Get branch code with caching
    branch_code = frappe.db.get_value(
        "Branch",
        branch,
        "branch_code",
        cache=True
    )
    
    if not branch_code:
        raise ValidationError(
            f"Branch code not found for {branch}",
            "Configuration Error"
        )

    branch_code = branch_code.strip().upper()
    today = now_datetime().strftime("%Y%m%d")
    
    # Get last order number for today
    last_order = frappe.db.sql("""
        SELECT name FROM `tabPOS Order`
        WHERE branch = %s 
        AND creation >= %s
        AND creation < DATE_ADD(%s, INTERVAL 1 DAY)
        ORDER BY creation DESC
        LIMIT 1
    """, (branch, today, today))
    
    count = int(last_order[0][0].split("-")[-1]) + 1 if last_order else 1
    
    return f"POS-{branch_code}-{today}-{count:04d}"

@whitelist()
@handle_pos_errors()
def update_kot_item_status(
    order: str,
    item_code: str,
    status: str
) -> Dict[str, str]:
    """
    Update KOT status for item in order
    
    Args:
        order (str): POS Order ID
        item_code (str): Item code
        status (str): New status
        
    Returns:
        Dict: Update status and message
        
    Raises:
        ValidationError: If parameters are invalid
    """
    if status not in KOT_STATUSES:
        raise ValidationError(
            f"Invalid status: {status}. Valid statuses are: {', '.join(KOT_STATUSES)}",
            "Status Error"
        )

    doc = frappe.get_doc("POS Order", order)
    updated = False
    kot_id = None

    for item in doc.pos_order_items:
        if item.item_code == item_code and not item.cancelled:
            item.kot_status = status
            item.kot_last_update = now_datetime()
            updated = True
            kot_id = item.get("kot_id")
            break

    if not updated:
        raise ValidationError(
            f"Item {item_code} not found or cancelled in order {order}",
            "Not Found Error"
        )

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Update KDS if exists
    if kot_id:
        kds_name = frappe.db.get_value(
            "Kitchen Display Order",
            {"kot_id": kot_id},
            cache=True
        )
        if kds_name:
            update_kds_status_from_kot(kds_name)

    return {
        "status": "success",
        "message": _(f"Item {item_code} status updated to {status}")
    }

@handle_pos_errors()
def is_pos_profile_authorized(
    pos_profile: str,
    user: Optional[str] = None
) -> bool:
    """
    Check if user is authorized to use POS Profile
    
    Args:
        pos_profile (str): POS Profile name
        user (str, optional): User ID. Defaults to current user.
        
    Returns:
        bool: True if authorized
    """
    user = user or frappe.session.user
    cache_key = f"pos_auth:{pos_profile}:{user}"
    
    # Try cache first
    cached = frappe.cache().get_value(cache_key)
    if cached is not None:
        return cached
        
    if "System Manager" in frappe.get_roles(user):
        result = True
    else:
        authorized_roles = frappe.get_all(
            "POS Profile User",
            filters={"parent": pos_profile},
            pluck="role",
            cache=True
        )
        
        user_roles = frappe.get_roles(user)
        result = bool(set(authorized_roles) & set(user_roles))
    
    # Cache result
    frappe.cache().set_value(
        cache_key,
        result,
        expires_in_sec=3600
    )
    
    return result

def get_pos_settings() -> Dict[str, Any]:
    """
    Get POS Settings with caching
    
    Returns:
        Dict: POS settings
    """
    return frappe.get_cached_doc("POS Settings", "POS Settings")

@handle_pos_errors()
def validate_working_day() -> bool:
    """
    Validate if current time is within working hours
    
    Returns:
        bool: True if within working hours
        
    Raises:
        ValidationError: If outside working hours
    """
    settings = get_pos_settings()
    
    if not settings.working_hours_enabled:
        return True
        
    current_time = now_datetime().time()
    start_time = settings.working_hours_start
    end_time = settings.working_hours_end
    
    if start_time <= current_time <= end_time:
        return True
        
    raise ValidationError(
        f"Store is closed. Working hours: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
        "Working Hours Error"
    )

def get_table_status(table_no: str) -> Optional[str]:
    """
    Get current table status
    
    Args:
        table_no (str): Table number
        
    Returns:
        str: Table status or None
    """
    if not table_no:
        return None
        
    return frappe.db.get_value(
        "POS Table",
        table_no,
        "current_status",
        cache=True
    ) or "Available"

def calculate_cooking_time(items: List[Dict]) -> int:
    """
    Calculate estimated cooking time for items
    
    Args:
        items (List[Dict]): List of order items
        
    Returns:
        int: Maximum cooking time in minutes
    """
    if not items:
        return 0
        
    item_codes = [item.item_code for item in items]
    prep_times = frappe.db.get_values(
        "Item",
        {"name": ["in", item_codes]},
        ["name", "preparation_time"],
        as_dict=True,
        cache=True
    )
    
    prep_time_dict = {
        item.name: cint(item.preparation_time)
        for item in prep_times
    }
    
    return max(
        (prep_time_dict.get(item.item_code, 0) for item in items),
        default=0
    )
@whitelist()
@handle_pos_errors()
def get_default_company() -> str:
    return frappe.defaults.get_global_default("company") or "Default Company"