# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:48:29'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional
from datetime import datetime
import json

from pos_restaurant_itb.utils.error_handlers import handle_api_error
from pos_restaurant_itb.utils.constants import (
    PaymentStatus,
    PaymentMethod,
    ErrorMessages,
    CacheKeys
)
from pos_restaurant_itb.utils.realtime import notify_payment_update

@frappe.whitelist(allow_guest=True)
@handle_api_error
def create_payment_request(
    order_id: str,
    device_id: str,
    payment_method: str,
    amount: float
) -> Dict:
    """
    Create permintaan pembayaran
    
    Args:
        order_id: ID pesanan
        device_id: ID perangkat customer
        payment_method: Metode pembayaran
        amount: Jumlah pembayaran
        
    Returns:
        Dict: Payment request details
    """
    if payment_method not in PaymentMethod.ALL:
        frappe.throw(_(ErrorMessages.INVALID_PAYMENT_METHOD))
    
    # Validate order
    kot_doc = frappe.get_doc("KOT", order_id)
    
    if kot_doc.device_id != device_id:
        frappe.throw(_(ErrorMessages.INVALID_DEVICE))
    
    if kot_doc.payment_status != PaymentStatus.PENDING:
        frappe.throw(_(ErrorMessages.PAYMENT_ALREADY_PROCESSED))
    
    if amount != kot_doc.grand_total:
        frappe.throw(_(ErrorMessages.INVALID_PAYMENT_AMOUNT))
    
    # Create payment request
    payment_doc = frappe.get_doc({
        "doctype": "QR Payment",
        "order": order_id,
        "session": kot_doc.qr_session,
        "payment_method": payment_method,
        "amount": amount,
        "status": PaymentStatus.PENDING,
        "device_id": device_id,
        "branch": kot_doc.branch,
        "created_at": frappe.utils.now()
    })
    
    payment_doc.insert()
    
    # Generate payment gateway URL/data
    payment_data = generate_payment_data(payment_doc)
    
    # Notify payment request creation
    notify_payment_update(payment_doc)
    
    return {
        "success": True,
        "payment_id": payment_doc.name,
        "payment_data": payment_data,
        "timestamp": frappe.utils.now(),
        "expires_at": frappe.utils.add_to_date(
            frappe.utils.now(),
            minutes=15  # Payment request expires in 15 minutes
        )
    }

@frappe.whitelist(allow_guest=True)
@handle_api_error
def verify_payment(
    payment_id: str,
    device_id: str,
    verification_data: Dict
) -> Dict:
    """
    Verifikasi pembayaran
    
    Args:
        payment_id: ID pembayaran
        device_id: ID perangkat customer
        verification_data: Data verifikasi dari payment gateway
        
    Returns:
        Dict: Payment verification status
    """
    payment_doc = frappe.get_doc("QR Payment", payment_id)
    
    if payment_doc.device_id != device_id:
        frappe.throw(_(ErrorMessages.INVALID_DEVICE))
    
    if payment_doc.status != PaymentStatus.PENDING:
        frappe.throw(_(ErrorMessages.PAYMENT_ALREADY_PROCESSED))
    
    # Verify with payment gateway
    verification_result = verify_with_gateway(
        payment_doc,
        verification_data
    )
    
    if verification_result.get("success"):
        # Update payment status
        payment_doc.status = PaymentStatus.COMPLETED
        payment_doc.transaction_id = verification_result.get("transaction_id")
        payment_doc.completed_at = frappe.utils.now()
        payment_doc.gateway_response = json.dumps(verification_result)
        payment_doc.save()
        
        # Update order payment status
        kot_doc = frappe.get_doc("KOT", payment_doc.order)
        kot_doc.payment_status = PaymentStatus.COMPLETED
        kot_doc.payment_id = payment_id
        kot_doc.save()
        
        # Notify payment completion
        notify_payment_update(payment_doc)
        
        return {
            "success": True,
            "payment_id": payment_id,
            "status": PaymentStatus.COMPLETED,
            "timestamp": frappe.utils.now()
        }
    else:
        # Handle failed verification
        payment_doc.status = PaymentStatus.FAILED
        payment_doc.gateway_response = json.dumps(verification_result)
        payment_doc.save()
        
        return {
            "success": False,
            "payment_id": payment_id,
            "status": PaymentStatus.FAILED,
            "error": verification_result.get("error"),
            "timestamp": frappe.utils.now()
        }

@frappe.whitelist(allow_guest=True)
@handle_api_error
def get_payment_status(
    payment_id: str,
    device_id: str
) -> Dict:
    """
    Get status pembayaran
    
    Args:
        payment_id: ID pembayaran
        device_id: ID perangkat customer
        
    Returns:
        Dict: Payment status details
    """
    # Check cache first
    cache_key = f"{CacheKeys.QR_PAYMENT}:{payment_id}"
    payment_status = frappe.cache().get_value(cache_key)
    
    if not payment_status:
        payment_doc = frappe.get_doc("QR Payment", payment_id)
        
        if payment_doc.device_id != device_id:
            frappe.throw(_(ErrorMessages.INVALID_DEVICE))
        
        payment_status = {
            "payment_id": payment_id,
            "status": payment_doc.status,
            "amount": payment_doc.amount,
            "payment_method": payment_doc.payment_method,
            "created_at": payment_doc.created_at,
            "completed_at": payment_doc.completed_at
        }
        
        # Cache for 30 seconds
        frappe.cache().set_value(
            cache_key,
            payment_status,
            expires_in_sec=30
        )
    
    return payment_status

@frappe.whitelist()
@handle_api_error
def get_payment_methods(branch: str) -> List[Dict]:
    """
    Get metode pembayaran yang tersedia
    
    Args:
        branch: ID branch
        
    Returns:
        List[Dict]: Available payment methods
    """
    # Get from cache
    cache_key = f"{CacheKeys.PAYMENT_METHODS}:{branch}"
    methods = frappe.cache().get_value(cache_key)
    
    if not methods:
        methods = frappe.get_all(
            "Payment Method",
            filters={
                "enabled": 1,
                "branch": branch
            },
            fields=[
                "name", "method_name", "method_type",
                "description", "icon", "min_amount",
                "max_amount", "settings_json"
            ]
        )
        
        # Cache for 1 hour
        frappe.cache().set_value(
            cache_key,
            methods,
            expires_in_sec=3600
        )
    
    return methods

def generate_payment_data(payment_doc) -> Dict:
    """Generate payment gateway specific data"""
    method_settings = frappe.get_cached_doc(
        "Payment Method",
        payment_doc.payment_method
    )
    
    settings = json.loads(method_settings.settings_json)
    
    # Generate data based on payment method
    if payment_doc.payment_method == PaymentMethod.QRIS:
        return generate_qris_data(payment_doc, settings)
    elif payment_doc.payment_method == PaymentMethod.VIRTUAL_ACCOUNT:
        return generate_va_data(payment_doc, settings)
    elif payment_doc.payment_method == PaymentMethod.E_WALLET:
        return generate_ewallet_data(payment_doc, settings)
    else:
        frappe.throw(_(ErrorMessages.UNSUPPORTED_PAYMENT_METHOD))

def verify_with_gateway(
    payment_doc,
    verification_data: Dict
) -> Dict:
    """Verify payment with gateway"""
    method_settings = frappe.get_cached_doc(
        "Payment Method",
        payment_doc.payment_method
    )
    
    settings = json.loads(method_settings.settings_json)
    
    # Verify based on payment method
    if payment_doc.payment_method == PaymentMethod.QRIS:
        return verify_qris_payment(payment_doc, verification_data, settings)
    elif payment_doc.payment_method == PaymentMethod.VIRTUAL_ACCOUNT:
        return verify_va_payment(payment_doc, verification_data, settings)
    elif payment_doc.payment_method == PaymentMethod.E_WALLET:
        return verify_ewallet_payment(payment_doc, verification_data, settings)
    else:
        frappe.throw(_(ErrorMessages.UNSUPPORTED_PAYMENT_METHOD))

# Payment method specific functions
def generate_qris_data(payment_doc, settings: Dict) -> Dict:
    """Generate QRIS payment data"""
    # Implementation specific to QRIS
    pass

def generate_va_data(payment_doc, settings: Dict) -> Dict:
    """Generate Virtual Account payment data"""
    # Implementation specific to Virtual Account
    pass

def generate_ewallet_data(payment_doc, settings: Dict) -> Dict:
    """Generate E-wallet payment data"""
    # Implementation specific to E-wallet
    pass

def verify_qris_payment(
    payment_doc,
    verification_data: Dict,
    settings: Dict
) -> Dict:
    """Verify QRIS payment"""
    # Implementation specific to QRIS
    pass

def verify_va_payment(
    payment_doc,
    verification_data: Dict,
    settings: Dict
) -> Dict:
    """Verify Virtual Account payment"""
    # Implementation specific to Virtual Account
    pass

def verify_ewallet_payment(
    payment_doc,
    verification_data: Dict,
    settings: Dict
) -> Dict:
    """Verify E-wallet payment"""
    # Implementation specific to E-wallet
    pass