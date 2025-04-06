# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

"""
Order Voiding API
--------------
Handles order cancellation and voiding operations.

Features:
- Order voiding
- Reason tracking
- Inventory reversal
- Payment refunds
- Void reporting
"""

__created_date__ = '2025-04-06 16:08:35'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta

from pos_restaurant_itb.utils.error_handlers import handle_api_error, VoidError
from pos_restaurant_itb.utils.security import validate_void_permission
from pos_restaurant_itb.utils.constants import VoidReason, PaymentStatus

@frappe.whitelist()
@handle_api_error
def void_order(
    order_id: str,
    reason: str,
    notes: Optional[str] = None,
    refund_payment: bool = False
) -> Dict:
    """
    Void a POS order
    
    Args:
        order_id: Order ID to void
        reason: Reason for voiding
        notes: Optional additional notes
        refund_payment: Whether to process refund
        
    Returns:
        Dict containing void status
    """
    try:
        # Validate permissions
        validate_void_permission("void_order")
        
        # Validate reason
        if reason not in VoidReason.__members__:
            raise VoidError(f"Invalid void reason: {reason}")
            
        # Get order
        order = frappe.get_doc("POS Order", order_id)
        
        # Validate order status
        validate_void_status(order)
        
        # Create void record
        void_record = create_void_record(
            order,
            reason,
            notes
        )
        
        # Process void operations
        process_void_operations(order, void_record)
        
        # Handle payment refund if needed
        if refund_payment and order.payment_status == PaymentStatus.PAID:
            process_refund(order, void_record)
            
        # Update order status
        update_order_status(order, void_record)
        
        # Notify relevant parties
        notify_void_completion(void_record)
        
        return {
            "success": True,
            "void_id": void_record.name,
            "order_id": order_id,
            "refund_status": void_record.refund_status,
            "timestamp": frappe.utils.now()
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Order Void Error: {str(e)}\n{frappe.get_traceback()}",
            title="Void Error"
        )
        return {"success": False, "error": str(e)}

@frappe.whitelist()
@handle_api_error
def get_void_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    reason: Optional[str] = None
) -> Dict:
    """
    Get void order report
    
    Args:
        start_date: Report start date
        end_date: Report end date
        reason: Optional reason filter
        
    Returns:
        Dict containing void report
    """
    try:
        # Validate permissions
        validate_void_permission("view_report")
        
        # Set default dates
        end_date = end_date or frappe.utils.today()
        start_date = start_date or frappe.utils.add_days(end_date, -30)
        
        # Build filters
        filters = {
            "creation": ["between", [start_date, end_date]]
        }
        if reason:
            if reason not in VoidReason.__members__:
                raise VoidError(f"Invalid void reason: {reason}")
            filters["void_reason"] = reason
            
        # Get void records
        void_records = frappe.get_all(
            "Order Void Record",
            filters=filters,
            fields=[
                "name",
                "order",
                "void_reason",
                "notes",
                "voided_by",
                "void_time",
                "refund_status",
                "refund_amount"
            ],
            order_by="void_time desc"
        )
        
        # Calculate statistics
        stats = calculate_void_statistics(void_records)
        
        return {
            "success": True,
            "start_date": start_date,
            "end_date": end_date,
            "void_records": void_records,
            "statistics": stats,
            "timestamp": frappe.utils.now()
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Void Report Error: {str(e)}\n{frappe.get_traceback()}",
            title="Report Error"
        )
        return {"success": False, "error": str(e)}

def validate_void_status(order: "POS Order") -> None:
    """Validate if order can be voided"""
    if order.docstatus == 2:
        raise VoidError("Order is already voided")
        
    if order.status == "Delivered":
        raise VoidError("Cannot void delivered orders")
        
    # Check if any items are already served
    served_items = [
        item for item in order.items
        if item.status == "Served"
    ]
    if served_items:
        raise VoidError("Cannot void order with served items")

def create_void_record(
    order: "POS Order",
    reason: str,
    notes: Optional[str]
) -> "Order Void Record":
    """Create void record document"""
    void_record = frappe.get_doc({
        "doctype": "Order Void Record",
        "order": order.name,
        "void_reason": reason,
        "notes": notes,
        "voided_by": frappe.session.user,
        "void_time": frappe.utils.now(),
        "order_amount": order.grand_total,
        "payment_status": order.payment_status
    })
    
    void_record.insert()
    return void_record

def process_void_operations(
    order: "POS Order",
    void_record: "Order Void Record"
) -> None:
    """Process void-related operations"""
    # Cancel KOTs
    cancel_order_kots(order)
    
    # Reverse inventory
    reverse_inventory(order)
    
    # Update table status
    update_table_status(order.table_no)
    
    # Log void event
    log_void_event(order, void_record)

def process_refund(
    order: "POS Order",
    void_record: "Order Void Record"
) -> None:
    """Process payment refund"""
    payment_entry = frappe.get_doc("Payment Entry", order.payment_entry)
    
    refund = create_refund_entry(
        payment_entry,
        void_record
    )
    
    void_record.refund_status = "Completed"
    void_record.refund_amount = refund.amount
    void_record.refund_reference = refund.name
    void_record.save()