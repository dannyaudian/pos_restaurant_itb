# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 07:41:12'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

"""
POS Restaurant ITB - Utilities Module
-----------------------------------
Collection of utility functions and helpers for POS Restaurant ITB.

Modules:
- attributes: Item attribute handling utilities
- common: Common utility functions
- constants: System-wide constants and messages
- error_handlers: Error handling and logging
- jinja_filters: Custom Jinja template filters
- optimization: Performance optimization utilities
- price: Price calculation utilities
- security: Security and permission utilities
"""

import frappe
from frappe import _
from frappe.utils import get_traceback

from . import (
    attributes,
    common,
    constants,
    error_handlers,
    jinja_filters,
    optimization,
    price,
    security,
    realtime
)

# Constants
from .constants import (
    KOT_STATUSES,
    ORDER_STATUSES,
    TABLE_STATUSES,
    MSGS,
    OrderStatus,
    PaymentStatus,
    ErrorMessages,
    CacheKeys,
    QR_ORDER_STATUSES,
    POS_ORDER_STATUSES,
    QR_POS_ORDER_STATUSES
)

# Common Functions
from .common import (
    get_branch_from_user,
    get_new_order_id,
    update_kot_item_status,
    is_pos_profile_authorized,
    get_pos_settings,
    validate_working_day,
    get_table_status,
    calculate_cooking_time,
    create_logs,
    get_pos_profile,
    get_user_profile,
    get_user_branch,
    get_kot_in_progress,
    get_draft_qr_orders,
    get_user_roles,
    get_system_settings,
    validate_permissions
)

# Price Functions
from .price import (
    get_item_price,
    calculate_item_amount,
    get_price_list_details
)

# Attribute Functions
from .attributes import (
    validate_item_attributes,
    get_variant_attributes,
    find_variant
)

# Security Functions
from .security import (
    validate_user_permission,
    get_user_restrictions,
    validate_branch_access
)

# Optimization Functions
from .optimization import (
    cleanup_old_data,
    update_stats,
    optimize_db_queries
)

# Jinja Filters
from .jinja_filters import (
    format_currency,
    format_datetime,
    format_status
)

# Error Handlers
from .error_handlers import (
    POSRestaurantError,
    TableError,
    OrderError,
    KitchenError,
    ValidationError,
    handle_api_error,
    handle_doc_error,
    handle_pos_errors,
    log_pos_activity,
    notify_error,
    handle_transaction_error,
    cleanup_failed_documents
)

# Realtime Functions
from .realtime import (
    notify_order_update,
    notify_kot_update,
    notify_kitchen_update
)

# Version and metadata
__version__ = '1.0.0'

# Module exports
__all__ = [
    # Modules
    'attributes',
    'common',
    'constants',
    'error_handlers',
    'jinja_filters',
    'optimization',
    'price',
    'security',
    'realtime',
    
    # Constants
    'KOT_STATUSES',
    'ORDER_STATUSES', 
    'TABLE_STATUSES',
    'MSGS',
    'OrderStatus',
    'PaymentStatus',
    'ErrorMessages',
    'CacheKeys',
    'QR_ORDER_STATUSES',
    'POS_ORDER_STATUSES',
    'QR_POS_ORDER_STATUSES',
    
    # Error Classes
    'POSRestaurantError',
    'TableError',
    'OrderError',
    'KitchenError',
    'ValidationError',
    
    # Common Functions
    'get_branch_from_user',
    'get_new_order_id',
    'update_kot_item_status',
    'is_pos_profile_authorized',
    'get_pos_settings',
    'validate_working_day',
    'get_table_status',
    'calculate_cooking_time',
    'create_logs',
    'get_pos_profile',
    'get_user_profile',
    'get_user_branch',
    'get_kot_in_progress',
    'get_draft_qr_orders',
    'get_user_roles',
    'get_system_settings',
    'validate_permissions',
    
    # Error Handlers
    'handle_api_error',
    'handle_doc_error',
    'handle_pos_errors',
    'log_pos_activity',
    'notify_error',
    'handle_transaction_error',
    'cleanup_failed_documents',
    
    # Price Functions
    'get_item_price',
    'calculate_item_amount',
    'get_price_list_details',
    
    # Attribute Functions
    'validate_item_attributes',
    'get_variant_attributes',
    'find_variant',
    
    # Security Functions
    'validate_user_permission',
    'get_user_restrictions',
    'validate_branch_access',
    
    # Optimization Functions
    'cleanup_old_data',
    'update_stats',
    'optimize_db_queries',
    
    # Jinja Filter Functions
    'format_currency',
    'format_datetime',
    'format_status',
    
    # Realtime Functions
    'notify_order_update',
    'notify_kot_update',
    'notify_kitchen_update'
]