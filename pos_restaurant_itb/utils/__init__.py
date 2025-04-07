# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 07:47:42'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

"""
POS Restaurant ITB - Utilities Module
-------------------------------------
Kumpulan fungsi utilitas dan helper untuk modul POS Restaurant ITB.

Submodules:
- attributes         : Penanganan atribut item & varian
- common             : Fungsi umum (branch, order ID, validasi, dsb)
- constants          : Konstanta status, pesan, naming series
- error_handlers     : Penanganan error & log
- jinja_filters      : Filter untuk jinja templates
- optimization       : Optimasi dan pembersihan data
- price              : Perhitungan harga & diskon
- security           : Validasi otorisasi & keamanan
- status_manager     : Pengaturan transisi status
- realtime           : Komunikasi realtime via socketio
"""

from . import (
    attributes,
    common,
    constants,
    error_handlers,
    jinja_filters,
    optimization,
    price,
    security,
    status_manager,
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
    QR_POS_ORDER_STATUSES,
    NamingSeries
)

# Common Utilities
from .common import (
    get_branch_from_user,
    get_new_order_id,
    update_kot_item_status,
    is_pos_profile_authorized,
    get_pos_settings,
    validate_working_day,
    get_table_status,
    calculate_cooking_time
)

# Error Handling
from .error_handlers import (
    POSRestaurantError,
    TableError,
    OrderError,
    KitchenError,
    ValidationError,
    handle_pos_errors,
    log_pos_activity,
    notify_error,
    handle_transaction_error,
    cleanup_failed_documents,
    handle_api_error,
    handle_doc_error
)

# Price Calculation
from .price import (
    get_item_price,
    calculate_item_amount,
    get_price_list_details
)

# Attribute Handling
from .attributes import (
    validate_item_attributes,
    get_variant_attributes,
    find_variant
)

# Security & Permission
from .security import (
    validate_user_permission,
    get_user_restrictions,
    validate_branch_access,
    update_order_status,
    get_valid_status_transitions
)

# Optimization
from .optimization import (
    cleanup_old_data,
    update_stats,
    optimize_db_queries,
    update_pos_order_stats
)

# Jinja Filters
from .jinja_filters import (
    format_currency,
    format_datetime,
    format_status
)

# Status Manager
from .status_manager import (
    StatusManager,
    handle_qr_order_status_update,
    get_qr_order_status_info,
    update_document_status
)

# Realtime Utilities
from .realtime import (
    notify_session_update,
    notify_order_update,
    notify_kitchen_status,
    broadcast_to_kitchen
)

# Version Info
__version__ = '1.0.0'

__all__ = [
    # Modules
    'attributes', 'common', 'constants', 'error_handlers', 'jinja_filters',
    'optimization', 'price', 'security', 'status_manager', 'realtime',

    # Constants
    'KOT_STATUSES', 'ORDER_STATUSES', 'TABLE_STATUSES', 'MSGS',
    'OrderStatus', 'PaymentStatus', 'ErrorMessages', 'CacheKeys',
    'QR_ORDER_STATUSES', 'POS_ORDER_STATUSES', 'QR_POS_ORDER_STATUSES',
    'NamingSeries',

    # Exception Classes
    'POSRestaurantError', 'TableError', 'OrderError', 'KitchenError', 'ValidationError',

    # Common
    'get_branch_from_user', 'get_new_order_id', 'update_kot_item_status',
    'is_pos_profile_authorized', 'get_pos_settings', 'validate_working_day',
    'get_table_status', 'calculate_cooking_time',

    # Error
    'handle_pos_errors', 'log_pos_activity', 'notify_error',
    'handle_transaction_error', 'cleanup_failed_documents',
    'handle_api_error', 'handle_doc_error',

    # Price
    'get_item_price', 'calculate_item_amount', 'get_price_list_details',

    # Attributes
    'validate_item_attributes', 'get_variant_attributes', 'find_variant',

    # Security
    'validate_user_permission', 'get_user_restrictions', 'validate_branch_access',
    'update_order_status', 'get_valid_status_transitions',

    # Optimization
    'cleanup_old_data', 'update_stats', 'optimize_db_queries', 'update_pos_order_stats',

    # Jinja
    'format_currency', 'format_datetime', 'format_status',

    # Status
    'StatusManager', 'handle_qr_order_status_update', 'get_qr_order_status_info',
    'update_document_status',

    # Realtime
    'notify_session_update', 'notify_order_update',
    'notify_kitchen_status', 'broadcast_to_kitchen'
]
