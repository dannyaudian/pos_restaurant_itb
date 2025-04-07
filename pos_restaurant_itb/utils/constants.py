# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 07:47:42'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

from enum import Enum
from typing import Dict, List


# -------------------------
# Status Enums & Constants
# -------------------------

class OrderStatus:
    DRAFT = "Draft"
    NEW = "New"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    PARTIAL = "Partial"
    PENDING = "Pending"
    DELIVERED = "Delivered"
    READY = "Ready"
    RECEIVED = "Received"
    PROCESSING = "Processing"
    MERGED = "Merged"
    VOID = "Void"

class PaymentStatus:
    PENDING = "Pending"
    PAID = "Paid"
    PARTIALLY_PAID = "Partially Paid"
    REFUNDED = "Refunded"
    CANCELLED = "Cancelled"
    FAILED = "Failed"
    PROCESSING = "Processing"
    AUTHORIZED = "Authorized"
    SETTLED = "Settled"
    VOID = "Void"

class TableStatus(str, Enum):
    AVAILABLE = "Available"
    OCCUPIED = "Occupied"
    RESERVED = "Reserved"
    MAINTENANCE = "Maintenance"
    MERGED = "Merged"
    SPLIT = "Split"


# -------------------------
# Status Transition Maps
# -------------------------

QR_ORDER_STATUSES: Dict[str, List[str]] = {
    "Draft": ["In Progress", "Cancelled"],
    "In Progress": ["Ready for Billing", "Cancelled"],
    "Ready for Billing": ["Completed", "Cancelled"],
    "Completed": [],
    "Cancelled": []
}

POS_ORDER_STATUSES: Dict[str, List[str]] = {
    "Draft": ["In Progress", "Cancelled"],
    "In Progress": ["Ready for Billing", "Cancelled"],
    "Ready for Billing": ["Completed", "Cancelled"],
    "Completed": [],
    "Cancelled": [],
    "Merged": [],
    "Void": []
}

QR_POS_ORDER_STATUSES = POS_ORDER_STATUSES.copy()

KOT_STATUSES = {
    "New": ["In Progress", "Cancelled"],
    "In Progress": ["Completed", "Cancelled"],
    "Completed": [],
    "Cancelled": [],
    "Void": []
}

KITCHEN_DISPLAY_STATUSES = {
    "New": ["Processing", "Cancelled"],
    "Processing": ["Ready", "Cancelled"],
    "Ready": ["Delivered"],
    "Delivered": [],
    "Cancelled": []
}

PAYMENT_STATUSES = {
    "Pending": ["Paid", "Partially Paid", "Cancelled"],
    "Partially Paid": ["Paid", "Cancelled"],
    "Paid": ["Refunded", "Void"],
    "Refunded": [],
    "Cancelled": [],
    "Void": []
}

TABLE_STATUSES = {
    TableStatus.AVAILABLE: [TableStatus.OCCUPIED, TableStatus.RESERVED, TableStatus.MAINTENANCE],
    TableStatus.OCCUPIED: [TableStatus.AVAILABLE, TableStatus.MAINTENANCE],
    TableStatus.RESERVED: [TableStatus.AVAILABLE, TableStatus.OCCUPIED, TableStatus.MAINTENANCE],
    TableStatus.MAINTENANCE: [TableStatus.AVAILABLE],
    TableStatus.MERGED: [TableStatus.AVAILABLE],
    TableStatus.SPLIT: [TableStatus.AVAILABLE]
}


# -------------------------
# Document Status Mapping
# -------------------------

DOCUMENT_STATUS_MAP = {
    "QR Order": {
        "status_field": "status",
        "statuses": QR_ORDER_STATUSES,
        "default": "Draft"
    },
    "POS Order": {
        "status_field": "status",
        "statuses": POS_ORDER_STATUSES,
        "default": "Draft"
    },
    "QR POS Order": {
        "status_field": "status",
        "statuses": QR_POS_ORDER_STATUSES,
        "default": "Draft"
    },
    "KOT": {
        "status_field": "status",
        "statuses": KOT_STATUSES,
        "default": "New"
    },
    "POS Table": {
        "status_field": "status",
        "statuses": TABLE_STATUSES,
        "default": TableStatus.AVAILABLE
    },
    "Kitchen Display Order": {
        "status_field": "status",
        "statuses": KITCHEN_DISPLAY_STATUSES,
        "default": "New"
    }
}


STATUS_TRANSITIONS: Dict[str, Dict[str, List[str]]] = {
    key: value["statuses"] for key, value in DOCUMENT_STATUS_MAP.items()
}


# -------------------------
# Cache & Error Constants
# -------------------------

class ErrorMessages:
    INVALID_DEVICE = "Invalid device ID"
    SESSION_INACTIVE = "Session is not active"
    ORDER_NOT_FOUND = "Order not found"
    ORDER_MODIFICATION_DENIED = "Order modification not allowed"
    INVALID_STATUS = "Invalid status"
    INVALID_PAYMENT = "Invalid payment"
    PERMISSION_DENIED = "Permission denied"
    BRANCH_UNAUTHORIZED = "Branch access unauthorized"
    TABLE_UNAVAILABLE = "Table is not available"
    KOT_ERROR = "Error processing KOT"
    INVALID_CONFIGURATION = "Invalid configuration"
    SESSION_EXPIRED = "Session has expired"
    INVALID_CREDENTIALS = "Invalid credentials"
    SYSTEM_ERROR = "System error occurred"
    ITEMS_REQUIRED = "At least one item is required."


class CacheKeys:
    QR_ORDER = "qr_order"
    POS_ORDER = "pos_order"
    KOT = "kot"
    TABLE = "table"
    SESSION = "session"
    USER_PROFILE = "user_profile"
    POS_PROFILE = "pos_profile"
    SYSTEM_SETTINGS = "system_settings"
    BRANCH_SETTINGS = "branch_settings"
    KITCHEN_SETTINGS = "kitchen_settings"


# -------------------------
# UI Message Sets
# -------------------------

MSGS = {
    "success": {
        "create": "Created successfully",
        "update": "Updated successfully",
        "delete": "Deleted successfully",
        "cancel": "Cancelled successfully",
        "submit": "Submitted successfully",
        "payment": "Payment processed successfully",
        "order": "Order processed successfully",
        "merge": "Merged successfully",
        "split": "Split successfully",
        "void": "Voided successfully"
    },
    "error": {
        "not_found": "Record not found",
        "invalid_status": "Invalid status",
        "permission": "Permission denied",
        "validation": "Validation failed",
        "system": "System error occurred",
        "configuration": "Configuration error",
        "connection": "Connection error",
        "duplicate": "Duplicate record",
        "dependency": "Dependency error"
    },
    "warning": {
        "status_change": "Status cannot be changed",
        "incomplete": "Required fields missing",
        "duplicate": "Record already exists",
        "pending": "Action pending",
        "maintenance": "System under maintenance",
        "deprecated": "Feature deprecated"
    },
    "info": {
        "processing": "Processing request",
        "pending": "Action pending",
        "awaiting": "Awaiting response",
        "scheduled": "Action scheduled",
        "background": "Running in background",
        "sync": "Synchronizing data"
    }
}


# -------------------------
# Naming Series by Branch
# -------------------------

NamingSeries: Dict[str, str] = {
    "POS Order": "POS-{branch_code}-",
    "QR Order": "QR-{branch_code}-",
    "KOT": "KOT-{branch_code}-",
    "Kitchen Station": "KS-{branch_code}-",
    "Kitchen Station Setup": "KSS-{branch_code}-",
    "Printer Mapping POS Restaurant": "PRN-{branch_code}-"
}
