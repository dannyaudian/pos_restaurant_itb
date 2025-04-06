"""
POS Restaurant ITB API Module
----------------------------

Module ini berisi seluruh API endpoints untuk POS Restaurant ITB.
Termasuk fungsi-fungsi untuk:
- Kitchen Order Ticket (KOT)
- Kitchen Display System (KDS)
- Kitchen Station Management
- POS Order Management

Author: Danny Audian
Date: 2025-04-06
"""

import frappe
from frappe import _
from frappe.utils import now

# Version dan metadata
__version__ = "1.0.0"
__author__ = "Danny Audian"
__email__ = "dannyaudian@gmail.com"

# -----------------------------------------------------------------------------
# POS Configuration & Utilities
# -----------------------------------------------------------------------------
from .load_pos_restaurant_config import load_pos_restaurant_config
from pos_restaurant_itb.utils.common import (
    get_new_order_id,
    update_kot_item_status
)

# -----------------------------------------------------------------------------
# Kitchen Order Ticket (KOT) Management
# -----------------------------------------------------------------------------
from .create_kot import create_kot_from_pos_order
from .sendkitchenandcancel import (
    send_to_kitchen,
    cancel_pos_order_item
)
from .kot_status_update import update_kds_status_from_kot

# -----------------------------------------------------------------------------
# Kitchen Display System (KDS)
# -----------------------------------------------------------------------------
from .kds_handler import create_kds_from_kot
from .kds import create_kds_from_kot as create_kds_from_kot_manual

# -----------------------------------------------------------------------------
# Kitchen Station Management
# -----------------------------------------------------------------------------
from .kitchen_station import create_kitchen_station_items_from_kot
from .kitchen_station_handler import (
    get_kitchen_items_by_station,
    update_kitchen_item_status,
    cancel_kitchen_item
)

# -----------------------------------------------------------------------------
# Item & Table Management
# -----------------------------------------------------------------------------
from .resolve_variant import resolve_variant
from .get_attributes_for_item import get_attributes_for_item
from .get_available_tables import get_available_tables

# -----------------------------------------------------------------------------
# API Health Check & Logging
# -----------------------------------------------------------------------------
def check_api_health():
    """
    Memeriksa status API dan koneksinya
    Returns:
        dict: Status kesehatan API
    """
    try:
        return {
            "status": "healthy",
            "timestamp": now(),
            "version": __version__,
            "user": frappe.session.user,
            "modules": {
                "kot": bool(create_kot_from_pos_order),
                "kds": bool(create_kds_from_kot),
                "kitchen_station": bool(create_kitchen_station_items_from_kot)
            }
        }
    except Exception as e:
        frappe.log_error(
            message=f"API Health Check Failed: {str(e)}",
            title="API Health Check"
        )
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": now()
        }

def log_api_call(method_name, args=None):
    """
    Log pemanggilan API untuk monitoring
    
    Args:
        method_name (str): Nama method yang dipanggil
        args (dict, optional): Arguments yang diberikan
    """
    try:
        frappe.logger().info(
            f"API Call: {method_name} | "
            f"User: {frappe.session.user} | "
            f"Args: {args or 'None'} | "
            f"Time: {now()}"
        )
    except Exception:
        pass  # Silent fail untuk logging

# -----------------------------------------------------------------------------
# API Decorators
# -----------------------------------------------------------------------------
def api_handler(f):
    """
    Decorator untuk handling API calls
    
    Features:
    - Automatic logging
    - Error handling
    - Response formatting
    """
    def wrapper(*args, **kwargs):
        method_name = f.__name__
        try:
            # Log API call
            log_api_call(method_name, kwargs)
            
            # Execute function
            result = f(*args, **kwargs)
            
            return {
                "success": True,
                "data": result,
                "timestamp": now()
            }
            
        except Exception as e:
            frappe.log_error(
                message=f"API Error in {method_name}: {str(e)}",
                title=f"API Error: {method_name}"
            )
            return {
                "success": False,
                "error": str(e),
                "timestamp": now()
            }
            
    wrapper.__name__ = f.__name__
    wrapper.__doc__ = f.__doc__
    return wrapper

# -----------------------------------------------------------------------------
# Export all public APIs
# -----------------------------------------------------------------------------
__all__ = [
    # POS Configuration
    'load_pos_restaurant_config',
    'get_new_order_id',
    
    # KOT Management
    'create_kot_from_pos_order',
    'send_to_kitchen',
    'cancel_pos_order_item',
    'update_kds_status_from_kot',
    'update_kot_item_status',
    
    # KDS
    'create_kds_from_kot',
    'create_kds_from_kot_manual',
    
    # Kitchen Station
    'create_kitchen_station_items_from_kot',
    'get_kitchen_items_by_station',
    'update_kitchen_item_status',
    'cancel_kitchen_item',
    
    # Item & Table
    'resolve_variant',
    'get_attributes_for_item',
    'get_available_tables',
    
    # Utilities
    'check_api_health',
    'api_handler'
]
