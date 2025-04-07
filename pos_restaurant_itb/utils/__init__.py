# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 07:31:25'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'
__version__ = '1.0.0'

import frappe

from . import (
    common,
    constants,
    error_handlers,
    realtime
)

# Version
__version__ = '1.0.0'

# Module level imports
from .common import (
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

from .constants import (
    OrderStatus,
    PaymentStatus,
    ErrorMessages,
    CacheKeys,
    QR_ORDER_STATUSES,
    POS_ORDER_STATUSES,
    QR_POS_ORDER_STATUSES,
    KOT_STATUSES
)

from .error_handlers import (
    handle_api_error,
    handle_doc_error
)

from .realtime import (
    notify_order_update,
    notify_kot_update,
    notify_kitchen_update
)

# Module exports
__all__ = [
    # Common
    'create_logs',
    'get_pos_profile',
    'get_user_profile', 
    'get_user_branch',
    'get_kot_in_progress',
    'get_draft_qr_orders',
    'get_user_roles',
    'get_system_settings',
    'validate_permissions',

    # Constants
    'OrderStatus',
    'PaymentStatus',
    'ErrorMessages',
    'CacheKeys',
    'QR_ORDER_STATUSES',
    'POS_ORDER_STATUSES',
    'QR_POS_ORDER_STATUSES',
    'KOT_STATUSES',

    # Error Handlers
    'handle_api_error',
    'handle_doc_error',

    # Realtime
    'notify_order_update',
    'notify_kot_update', 
    'notify_kitchen_update'
]