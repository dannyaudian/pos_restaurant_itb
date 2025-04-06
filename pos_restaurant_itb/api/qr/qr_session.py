# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:45:30'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid

from pos_restaurant_itb.utils.error_handlers import handle_api_error
from pos_restaurant_itb.utils.constants import (
    SessionStatus,
    ErrorMessages,
    CacheKeys
)
from pos_restaurant_itb.utils.realtime import notify_session_update

@frappe.whitelist(allow_guest=True)
@handle_api_error
def create_qr_session(
    table: str,
    device_id: str,
    customer_name: Optional[str] = None
) -> Dict:
    """
    Create sesi pemesanan via QR
    
    Args:
        table: ID meja
        device_id: ID perangkat customer
        customer_name: Nama customer (optional)
        
    Returns:
        Dict: Session details
    """
    # Validate table
    table_doc = frappe.get_doc("POS Table", table)
    if table_doc.status != "Available":
        frappe.throw(_(ErrorMessages.TABLE_NOT_AVAILABLE))
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Create session
    session_doc = frappe.get_doc({
        "doctype": "QR Session",
        "session_id": session_id,
        "table": table,
        "device_id": device_id,
        "customer_name": customer_name,
        "status": SessionStatus.ACTIVE,
        "created_at": frappe.utils.now(),
        "branch": table_doc.branch
    })
    
    session_doc.insert()
    
    # Update table status
    table_doc.status = "Occupied"
    table_doc.current_session = session_id
    table_doc.save()
    
    # Notify session creation
    notify_session_update(session_doc)
    
    return {
        "success": True,
        "session_id": session_id,
        "table": table,
        "timestamp": frappe.utils.now(),
        "expires_at": frappe.utils.add_to_date(
            frappe.utils.now(),
            hours=4  # Session expires in 4 hours
        )
    }

@frappe.whitelist(allow_guest=True)
@handle_api_error
def validate_session(
    session_id: str,
    device_id: str
) -> Dict:
    """
    Validasi sesi QR
    
    Args:
        session_id: ID sesi
        device_id: ID perangkat customer
        
    Returns:
        Dict: Session validation status
    """
    # Check cache first
    cache_key = f"{CacheKeys.QR_SESSION}:{session_id}"
    session = frappe.cache().get_value(cache_key)
    
    if not session:
        session = frappe.get_doc("QR Session", {"session_id": session_id})
        
        # Cache for 5 minutes
        frappe.cache().set_value(
            cache_key,
            session.as_dict(),
            expires_in_sec=300
        )
    
    if session.device_id != device_id:
        frappe.throw(_(ErrorMessages.INVALID_DEVICE))
        
    if session.status != SessionStatus.ACTIVE:
        frappe.throw(_(ErrorMessages.SESSION_INACTIVE))
        
    # Check expiry
    created_at = frappe.utils.get_datetime(session.created_at)
    if frappe.utils.now_datetime() > (created_at + timedelta(hours=4)):
        session.status = SessionStatus.EXPIRED
        session.save()
        frappe.throw(_(ErrorMessages.SESSION_EXPIRED))
    
    return {
        "valid": True,
        "session_id": session_id,
        "table": session.table,
        "customer_name": session.customer_name,
        "created_at": session.created_at
    }

@frappe.whitelist(allow_guest=True)
@handle_api_error
def end_session(
    session_id: str,
    device_id: str
) -> Dict:
    """
    Akhiri sesi QR
    
    Args:
        session_id: ID sesi
        device_id: ID perangkat customer
        
    Returns:
        Dict: Session end status
    """
    session = frappe.get_doc("QR Session", {"session_id": session_id})
    
    if session.device_id != device_id:
        frappe.throw(_(ErrorMessages.INVALID_DEVICE))
    
    if session.status != SessionStatus.ACTIVE:
        frappe.throw(_(ErrorMessages.SESSION_INACTIVE))
    
    # Update session
    session.status = SessionStatus.ENDED
    session.ended_at = frappe.utils.now()
    session.save()
    
    # Update table status if no other active sessions
    table_doc = frappe.get_doc("POS Table", session.table)
    active_sessions = frappe.get_all(
        "QR Session",
        filters={
            "table": session.table,
            "status": SessionStatus.ACTIVE
        }
    )
    
    if not active_sessions:
        table_doc.status = "Available"
        table_doc.current_session = None
        table_doc.save()
    
    # Clear cache
    frappe.cache().delete_value(f"{CacheKeys.QR_SESSION}:{session_id}")
    
    # Notify session end
    notify_session_update(session)
    
    return {
        "success": True,
        "session_id": session_id,
        "timestamp": frappe.utils.now()
    }

@frappe.whitelist()
@handle_api_error
def get_active_sessions(branch: str) -> List[Dict]:
    """
    Get sesi QR aktif
    
    Args:
        branch: ID branch
        
    Returns:
        List[Dict]: Active sessions
    """
    sessions = frappe.get_all(
        "QR Session",
        filters={
            "branch": branch,
            "status": SessionStatus.ACTIVE
        },
        fields=[
            "session_id", "table", "customer_name",
            "created_at", "device_id"
        ]
    )
    
    for session in sessions:
        # Get associated orders
        orders = frappe.get_all(
            "KOT",
            filters={
                "table": session.table,
                "qr_session": session.session_id,
                "docstatus": 1
            },
            fields=[
                "name", "status", "creation",
                "grand_total"
            ]
        )
        
        session["orders"] = orders
        session["total_spent"] = sum(order.grand_total for order in orders)
        
        # Get table details
        table = frappe.get_cached_doc("POS Table", session.table)
        session["table_number"] = table.table_number
        session["table_capacity"] = table.capacity
    
    return sessions

@frappe.whitelist()
@handle_api_error
def extend_session(
    session_id: str,
    device_id: str,
    duration_hours: int = 1
) -> Dict:
    """
    Perpanjang sesi QR
    
    Args:
        session_id: ID sesi
        device_id: ID perangkat customer
        duration_hours: Durasi perpanjangan (jam)
        
    Returns:
        Dict: Session extension status
    """
    if duration_hours < 1 or duration_hours > 4:
        frappe.throw(_(ErrorMessages.INVALID_EXTENSION_DURATION))
    
    session = frappe.get_doc("QR Session", {"session_id": session_id})
    
    if session.device_id != device_id:
        frappe.throw(_(ErrorMessages.INVALID_DEVICE))
    
    if session.status != SessionStatus.ACTIVE:
        frappe.throw(_(ErrorMessages.SESSION_INACTIVE))
    
    # Calculate new expiry
    current_expiry = frappe.utils.get_datetime(session.created_at) + timedelta(hours=4)
    new_expiry = current_expiry + timedelta(hours=duration_hours)
    
    # Update session
    session.extended_at = frappe.utils.now()
    session.extension_hours = (session.extension_hours or 0) + duration_hours
    session.save()
    
    # Clear cache
    frappe.cache().delete_value(f"{CacheKeys.QR_SESSION}:{session_id}")
    
    return {
        "success": True,
        "session_id": session_id,
        "new_expiry": new_expiry,
        "timestamp": frappe.utils.now()
    }