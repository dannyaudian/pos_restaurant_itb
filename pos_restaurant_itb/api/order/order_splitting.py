# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

"""
Order Splitting API
----------------
Manages order splitting and bill separation operations.

Features:
- Item splitting
- Bill separation
- Payment allocation
- Split tracking
- Audit logging
"""

__created_date__ = '2025-04-06 16:11:19'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import json

from pos_restaurant_itb.utils.error_handlers import handle_api_error, SplitError
from pos_restaurant_itb.utils.security import validate_split_permission
from pos_restaurant_itb.utils.constants import SplitType, PaymentStatus

@frappe.whitelist()
@handle_api_error
def split_order(
    order_id: str,
    split_config: Dict[str, List[Dict]],
    split_type: str = SplitType.EQUAL,
    notes: Optional[str] = None
) -> Dict:
    """
    Split order into multiple bills
    
    Args:
        order_id: Original order ID
        split_config: Configuration for splitting items
        split_type: Type of split operation
        notes: Optional split notes
        
    Returns:
        Dict containing split details
    """
    try:
        # Validate permissions
        validate_split_permission("split_order")
        
        # Validate split type
        if split_type not in SplitType.__members__:
            raise SplitError(f"Invalid split type: {split_type}")
            
        # Get original order
        original_order = frappe.get_doc("POS Order", order_id)
        
        # Validate order status
        validate_split_status(original_order)
        
        # Validate split configuration
        validate_split_config(original_order, split_config)
        
        # Create split record
        split_record = create_split_record(
            original_order,
            split_type,
            notes
        )
        
        # Process split
        new_orders = process_split_orders(
            original_order,
            split_config,
            split_record
        )
        
        # Update original order
        update_original_order(original_order, split_record)
        
        return {
            "success": True,
            "split_id": split_record.name,
            "original_order": order_id,
            "new_orders": [order.name for order in new_orders],
            "timestamp": frappe.utils.now()
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Order Split Error: {str(e)}\n{frappe.get_traceback()}",
            title="Split Error"
        )
        return {"success": False, "error": str(e)}

@frappe.whitelist()
@handle_api_error
def get_split_preview(
    order_id: str,
    split_config: Dict[str, List[Dict]]
) -> Dict:
    """
    Get preview of split calculation
    
    Args:
        order_id: Order ID to split
        split_config: Proposed split configuration
        
    Returns:
        Dict containing split preview
    """
    try:
        # Get order
        order = frappe.get_doc("POS Order", order_id)
        
        # Calculate splits
        splits = calculate_splits(order, split_config)
        
        # Calculate taxes and charges
        tax_splits = calculate_tax_splits(order, splits)
        
        # Calculate totals
        totals = calculate_split_totals(splits, tax_splits)
        
        return {
            "success": True,
            "order_id": order_id,
            "splits": splits,
            "tax_splits": tax_splits,
            "totals": totals,
            "timestamp": frappe.utils.now()
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Split Preview Error: {str(e)}\n{frappe.get_traceback()}",
            title="Preview Error"
        )
        return {"success": False, "error": str(e)}

def validate_split_status(order: "POS Order") -> None:
    """Validate if order can be split"""
    if order.docstatus != 1:
        raise SplitError("Can only split submitted orders")
        
    if order.split_status == "Split":
        raise SplitError("Order is already split")
        
    if order.payment_status == PaymentStatus.PAID:
        raise SplitError("Cannot split paid orders")

def validate_split_config(
    order: "POS Order",
    split_config: Dict[str, List[Dict]]
) -> None:
    """Validate split configuration"""
    # Check if all items are accounted for
    original_items = {item.name: item.quantity for item in order.items}
    split_items = {}
    
    for split in split_config.values():
        for item in split:
            item_name = item["item_name"]
            quantity = item["quantity"]
            
            if item_name not in original_items:
                raise SplitError(f"Invalid item: {item_name}")
                
            split_items[item_name] = split_items.get(item_name, 0) + quantity
            
    # Verify quantities
    for item_name, original_qty in original_items.items():
        split_qty = split_items.get(item_name, 0)
        if split_qty != original_qty:
            raise SplitError(
                f"Quantity mismatch for {item_name}: "
                f"Original {original_qty}, Split {split_qty}"
            )

def create_split_record(
    order: "POS Order",
    split_type: str,
    notes: Optional[str]
) -> "Order Split Record":
    """Create split record document"""
    split_record = frappe.get_doc({
        "doctype": "Order Split Record",
        "original_order": order.name,
        "split_type": split_type,
        "notes": notes,
        "split_by": frappe.session.user,
        "split_time": frappe.utils.now(),
        "order_amount": order.grand_total
    })
    
    split_record.insert()
    return split_record

def process_split_orders(
    original_order: "POS Order",
    split_config: Dict[str, List[Dict]],
    split_record: "Order Split Record"
) -> List["POS Order"]:
    """Process and create split orders"""
    new_orders = []
    
    for split_name, items in split_config.items():
        # Create new order
        new_order = create_split_order(
            original_order,
            items,
            split_name,
            split_record
        )
        
        # Copy relevant order data
        copy_order_data(original_order, new_order)
        
        # Calculate taxes and totals
        calculate_order_totals(new_order)
        
        new_order.insert()
        new_orders.append(new_order)
        
    return new_orders

def calculate_splits(
    order: "POS Order",
    split_config: Dict[str, List[Dict]]
) -> Dict:
    """Calculate split details"""
    splits = {}
    
    for split_name, items in split_config.items():
        split_total = 0
        split_items = []
        
        for item in items:
            item_doc = frappe.get_doc("POS Order Item", item["item_name"])
            split_amount = (item["quantity"] / item_doc.quantity) * item_doc.amount
            
            split_items.append({
                "item_name": item["item_name"],
                "quantity": item["quantity"],
                "amount": split_amount
            })
            
            split_total += split_amount
            
        splits[split_name] = {
            "items": split_items,
            "subtotal": split_total
        }
        
    return splits