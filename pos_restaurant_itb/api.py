# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

"""
POS Restaurant ITB API
---------------------
Main API endpoints for POS Restaurant ITB.

This module serves as:
1. Central point for common API functions
2. Re-exports of frequently used functions
3. Version and metadata information

Most specific functionalities have been moved to their respective modules
under the pos_restaurant_itb/api/ directory.

Core Features:
- Kitchen Management (KOT, KDS, Kitchen Station)
- Order Management and Analytics 
- Table Management and Queue System
- QR-based Ordering and Payment
- Operational Metrics and Analytics

Documentation: https://github.com/PT-ITB/pos_restaurant_itb/wiki/API-Reference
"""

__created_date__ = '2025-04-06 15:23:21'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'
__version__ = '1.0.0'

import frappe
from frappe import _
from typing import Dict, Optional, List, Union, Any
from datetime import datetime

#
# Base Imports
#

# Error Handlers
from pos_restaurant_itb.utils.error_handlers import (
    handle_api_error,
    ValidationError,
    KitchenError,
    PaymentError,
    QRError,
    QueueError
)

# Security Utils
from pos_restaurant_itb.utils.security import (
    validate_branch_operation,
    validate_pos_profile_access,
    validate_manager_role
)

# Constants
from pos_restaurant_itb.utils.constants import (
    KOTStatus,
    KDSStatus,
    OrderStatus,
    PaymentStatus,
    QRSessionStatus, 
    QueueStatus,
    ErrorMessages,
    CacheKeys
)

# Realtime Updates
from pos_restaurant_itb.utils.realtime import (
    notify_kot_update,
    notify_kds_update,
    notify_table_update,
    notify_order_update,
    notify_queue_update
)

# Common Utils
from pos_restaurant_itb.utils.common import (
    get_new_order_id,
    get_branch_from_user,
    format_currency,
    get_pos_profile,
    get_business_date
)

#
# Feature Imports
#

# Kitchen Management
from .api.create_kot import create_kot_from_pos_order
from .api.kot_status_update import (
    update_kds_status_from_kot,
    bulk_update_kot_status
)
from .api.kitchen_station import (
    get_kitchen_station_items,
    update_kitchen_item_status
)
from .api.kitchen_analytics import (
    get_kitchen_performance_metrics,
    get_preparation_time_analysis
)

# Table Management
from .api.table_status import (
    get_table_status,
    update_table_status,
    get_section_occupancy
)

# Queue Management  
from .api.queue_manager import (
    create_queue_entry,
    update_queue_status,
    get_queue_status
)

# Order Management
from .api.order_notes import (
    add_order_note,
    update_order_note,
    get_order_notes
)
from .api.order_analytics import (
    get_order_trends,
    get_revenue_analysis
)

# QR System
from .api.qr_session import (
    create_qr_session,
    validate_qr_session
)
from .api.qr_order import (
    create_qr_order,
    update_qr_order
)
from .api.qr_payment import (
    generate_payment_qr,
    verify_qr_payment
)

# Operational Metrics
from .api.operational_metrics import (
    get_daily_metrics,
    get_efficiency_metrics
)

#
# Type Definitions
#

APIResponse = Dict[str, Any]
ItemList = List[Dict[str, Any]]
StatusResponse = Dict[str, Union[bool, str, datetime]]
MetricsData = Dict[str, Union[float, int, str]]
AnalyticsResult = Dict[str, Union[Dict, List, Any]]

#
# Core KDS Implementation
#

@frappe.whitelist()
@handle_api_error
def create_kds_from_kot(kot_id: str) -> Dict:
    """
    Create Kitchen Display Order from KOT
    
    Args:
        kot_id: KOT ID to create KDS from
        
    Returns:
        Dict: Creation status
            {
                "success": bool,
                "kds_id": str,
                "kot_id": str,
                "items_count": int,
                "timestamp": datetime
            }
    """
    if not kot_id:
        raise ValidationError(
            "KOT ID is required",
            "Missing Data"
        )

    # Check cache first
    cache_key = f"{CacheKeys.KDS_CREATE}:{kot_id}"
    kds_data = frappe.cache().get_value(cache_key)
    
    if not kds_data:
        # Check for existing KDS
        existing_kds = get_existing_kds(kot_id)
        if existing_kds:
            return format_kds_response(existing_kds)

        try:
            # Create new KDS
            kds = create_kds_document(kot_id)
            
            # Process items
            items_added = add_items_to_kds(kds)
            
            if not items_added:
                raise KitchenError(
                    "No valid items to add to KDS",
                    "No Items"
                )
            
            # Save and notify
            kds.insert(ignore_permissions=True)
            notify_kds_update(kds)
            
            # Format response
            kds_data = format_kds_response(kds.name)
            
            # Cache for 5 minutes
            frappe.cache().set_value(
                cache_key,
                kds_data,
                expires_in_sec=300
            )
            
            # Log creation
            log_kds_creation(kds)
            
        except Exception as e:
            log_error(e, kot_id)
            raise
    
    return kds_data

def get_existing_kds(kot_id: str) -> Optional[str]:
    """
    Check for existing KDS
    
    Args:
        kot_id: KOT ID to check
        
    Returns:
        Optional[str]: Existing KDS ID if found
    """
    return frappe.db.get_value(
        "Kitchen Display Order",
        {"kot_id": kot_id},
        "name"
    )

def create_kds_document(kot_id: str) -> "Document":
    """
    Create new KDS document
    
    Args:
        kot_id: KOT ID to create from
        
    Returns:
        Document: Created KDS document
    """
    kot = frappe.get_doc("KOT", kot_id)
    
    # Validate branch permission
    validate_branch_operation(
        kot.branch,
        "create_kds",
        frappe.session.user
    )
    
    return frappe.get_doc({
        "doctype": "Kitchen Display Order",
        "kot_id": kot.name,
        "table": kot.table,
        "branch": kot.branch,
        "waiter": kot.waiter,
        "customer_name": kot.customer_name,
        "status": KDSStatus.NEW,
        "priority": kot.priority,
        "creation": frappe.utils.now(),
        "owner": frappe.session.user
    })

def add_items_to_kds(kds) -> int:
    """
    Add items from KOT to KDS
    
    Args:
        kds: KDS document
        
    Returns:
        int: Number of items added
    """
    kot = frappe.get_doc("KOT", kds.kot_id)
    items_added = 0
    
    for item in kot.kot_items:
        if item.is_cancelled:
            continue
            
        kds.append("items", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "status": item.kot_status,
            "attributes": item.dynamic_attributes,
            "note": item.note,
            "preparation_time": get_preparation_time(item),
            "kitchen_station": get_kitchen_station(item)
        })
        items_added += 1
    
    return items_added

def get_preparation_time(item) -> int:
    """Get standard preparation time for item"""
    return frappe.get_cached_value(
        "Item",
        item.item_code,
        "preparation_time"
    ) or 30  # Default 30 minutes

def get_kitchen_station(item) -> str:
    """Get assigned kitchen station for item"""
    return frappe.get_cached_value(
        "Item",
        item.item_code,
        "kitchen_station"
    )

def format_kds_response(kds_id: str) -> Dict:
    """
    Format KDS response data
    
    Args:
        kds_id: KDS document ID
        
    Returns:
        Dict: Formatted response
    """
    kds = frappe.get_doc("Kitchen Display Order", kds_id)
    return {
        "success": True,
        "kds_id": kds_id,
        "kot_id": kds.kot_id,
        "items_count": len(kds.items),
        "timestamp": frappe.utils.now()
    }

def log_kds_creation(kds) -> None:
    """
    Log KDS creation event
    
    Args:
        kds: Created KDS document
    """
    frappe.logger().info(
        f"✅ KDS Creation Success\n"
        f"KDS: {kds.name}\n"
        f"KOT: {kds.kot_id}\n"
        f"Items: {len(kds.items)}\n"
        f"Created by: {frappe.session.user}\n"
        f"Time: {frappe.utils.now()}"
    )

def log_error(error: Exception, kot_id: str) -> None:
    """
    Log KDS creation error
    
    Args:
        error: Exception object
        kot_id: Related KOT ID
    """
    error_msg = f"""
    KDS Creation Error
    -----------------
    KOT: {kot_id}
    User: {frappe.session.user}
    Time: {frappe.utils.now()}
    Error: {str(error)}
    Traceback: {frappe.get_traceback()}
    """
    
    frappe.log_error(
        message=error_msg,
        title="❌ KDS Creation Error"
    )