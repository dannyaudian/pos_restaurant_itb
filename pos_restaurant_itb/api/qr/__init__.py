# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 16:22:00'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

"""
POS Restaurant ITB - QR API Package
-----------------------------------
Provides API endpoints for QR-based ordering, sessions, and payments.

Modules:
- qr_order: Create and manage QR Orders
- qr_payment: Handle QR-based payment requests and verification
- qr_session: Manage QR Sessions including start, end, and extension
"""

# QR Session APIs
from .qr_session import (
    create_qr_session,
    validate_session,
    end_session,
    get_active_sessions,
    extend_session
)

# QR Order APIs
from .qr_order import (
    create_qr_order,
    get_order_status,
    modify_order
)

# QR Payment APIs
from .qr_payment import (
    create_payment_request,
    verify_payment,
    get_payment_status,
    get_payment_methods
)
