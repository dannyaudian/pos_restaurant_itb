# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 09:54:36'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

from typing import Dict, List, Set, Final
from enum import Enum, auto

# Status Constants as Sets for O(1) lookup
POS_ORDER_STATUSES: Final[Set[str]] = frozenset({
    "Draft",
    "In Progress",
    "Ready for Billing",
    "Completed", 
    "Cancelled"
})

KOT_STATUSES: Final[Set[str]] = frozenset({
    "New",
    "In Progress",
    "Ready",
    "Served",
    "Cancelled"
})

KDS_STATUSES: Final[Set[str]] = frozenset({
    "New",
    "In Progress",
    "Ready",
    "Served",
    "Cancelled"
})

# Table Status as Enum for type safety
class TableStatus(str, Enum):
    AVAILABLE = "Available"
    OCCUPIED = "Occupied"
    RESERVED = "Reserved"
    MAINTENANCE = "Maintenance"

    @classmethod
    def list(cls) -> List[str]:
        return [status.value for status in cls]

# Status Transitions as Final to prevent modification
STATUS_TRANSITIONS: Final[Dict[str, Dict[str, List[str]]]] = {
    "POS Order": {
        "Draft": ["In Progress", "Cancelled"],
        "In Progress": ["Ready for Billing", "Cancelled"],
        "Ready for Billing": ["Completed", "Cancelled"],
        "Completed": [],  # Final state
        "Cancelled": []   # Final state
    },
    "KOT": {
        "New": ["In Progress", "Cancelled"],
        "In Progress": ["Ready", "Cancelled"],
        "Ready": ["Served", "Cancelled"],
        "Served": [],     # Final state
        "Cancelled": []   # Final state
    },
    "KDS": {
        "New": ["In Progress"],
        "In Progress": ["Ready"],
        "Ready": ["Served"],
        "Served": [],     # Final state
        "Cancelled": []   # Final state
    }
}

# UI Constants
class StatusColor(str, Enum):
    """Status colors for UI with semantic meaning"""
    SUCCESS = "green"
    WARNING = "orange"
    ERROR = "red"
    INFO = "blue"
    DEFAULT = "gray"

# Status Colors Mapping
STATUS_COLORS: Final[Dict[str, str]] = {
    # POS Order Status Colors
    "Draft": StatusColor.DEFAULT,
    "In Progress": StatusColor.INFO,
    "Ready for Billing": StatusColor.WARNING,
    "Completed": StatusColor.SUCCESS,
    "Cancelled": StatusColor.ERROR,
    
    # KOT Status Colors
    "New": StatusColor.DEFAULT,
    "Ready": StatusColor.SUCCESS,
    "Served": StatusColor.SUCCESS,
    
    # Common Status Colors
    "In Progress": StatusColor.WARNING,
    "Cancelled": StatusColor.ERROR
}

# Error Messages with formatting
class ErrorMessages:
    """Centralized error messages with formatting support"""
    
    # Validation Errors
    BRANCH_REQUIRED = "Branch is required"
    STORE_CLOSED = "Store is currently closed (Working hours: {start_time} - {end_time})"
    ITEM_NOT_FOUND = "Item {item_code} not found in order {order_id}"
    INVALID_STATUS = "Invalid status: {status}. Valid statuses are: {valid_statuses}"
    NO_BRANCH_ASSIGNED = "No branch assigned to user {user}"
    
    # Permission Errors
    NOT_AUTHORIZED = "User {user} is not authorized to {action}"
    BRANCH_ACCESS_DENIED = "Access to branch {branch} denied for user {user}"
    
    # Configuration Errors
    MISSING_CONFIG = "Missing configuration: {config_name}"
    INVALID_CONFIG = "Invalid configuration for {config_name}: {details}"
    
    # Status Transition Errors
    INVALID_TRANSITION = "Cannot change status from {old_status} to {new_status}"
    FINAL_STATUS = "Cannot change status: {status} is a final state"
    
    @classmethod
    def format(cls, message: str, **kwargs) -> str:
        """Format error message with provided kwargs"""
        try:
            return message.format(**kwargs)
        except KeyError as e:
            return f"Error formatting message: missing key {e}"
        except Exception as e:
            return str(message)

# Document States
class DocStatus:
    """Document statuses"""
    DRAFT = 0
    SUBMITTED = 1
    CANCELLED = 2

# Cache Keys
class CacheKeys:
    """Standard cache key formats"""
    USER_BRANCH = "user_branch:{user}"
    WAITER_NAME = "waiter_name:{user}"
    POS_AUTH = "pos_auth:{profile}:{user}"
    SETTINGS = "pos_settings:{branch}"
    
    @classmethod
    def get_key(cls, key: str, **kwargs) -> str:
        """Get formatted cache key"""
        return key.format(**kwargs)

# Cache Expiration Times (in seconds)
class CacheExpiration:
    """Standard cache expiration times"""
    SHORT = 300       # 5 minutes
    MEDIUM = 3600     # 1 hour
    LONG = 86400      # 24 hours
    PERMANENT = 0     # Never expire

# Document Naming Series
class NamingSeries:
    """Standard naming series patterns"""
    POS_ORDER = "POS-{branch_code}-{date}-{seq:04d}"
    KOT = "KOT-{branch_code}-{date}-{seq:04d}"
    KDS = "KDS-{branch_code}-{date}-{seq:04d}"

# Export all constants
__all__ = [
    'POS_ORDER_STATUSES',
    'KOT_STATUSES',
    'KDS_STATUSES',
    'TableStatus',
    'STATUS_TRANSITIONS',
    'StatusColor',
    'STATUS_COLORS',
    'ErrorMessages',
    'DocStatus',
    'CacheKeys',
    'CacheExpiration',
    'NamingSeries'
]
# Update OPERATION_ROLES dictionary
OPERATION_ROLES: Final[Dict[str, List[str]]] = {
    # ... existing roles ...
    "create_qr_order": ["QR Order User", "Outlet Manager", "Restaurant Manager"],
    "update_qr_order_confirmed": ["QR Order User", "Outlet Manager", "Restaurant Manager"],
    "update_qr_order_rejected": ["Outlet Manager", "Restaurant Manager"],
    "update_qr_order_cancelled": ["Outlet Manager", "Restaurant Manager"]
},
# Tambahkan ke STATUS_TRANSITIONS
"QR Order": {
    "Draft": ["In Progress", "Cancelled"],
    "In Progress": ["Ready for Billing", "Cancelled"],
    "Ready for Billing": ["Completed", "Cancelled"],
    "Completed": [],  # Final state
    "Cancelled": []   # Final state
}