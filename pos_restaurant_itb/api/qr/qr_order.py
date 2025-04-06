# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:46:59'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional
from datetime import datetime

from pos_restaurant_itb.utils.error_handlers import handle_api_error
from pos_restaurant_itb.utils.constants import (
    OrderStatus,
    PaymentStatus,
    ErrorMessages,
    CacheKeys
)
from pos_restaurant_itb.utils.realtime import notify_order_update

@frappe.whitelist(allow_guest=True)
@handle_api_error
def create_qr_order(
    session_id: str,
    device_id: str,
    items: List[Dict],
    special_instructions: Optional[str] = None
) -> Dict:
    """
    Create pesanan via QR
    
    Args:
        session_id: ID sesi QR
        device_id: ID perangkat customer
        items: List item pesanan
        special_instructions: Instruksi khusus
        
    Returns:
        Dict: Order details
    """
    # Validate session
    session = frappe.get_doc("QR Session", {"session_id": session_id})
    
    if session.device_id != device_id:
        frappe.throw(_(ErrorMessages.INVALID_DEVICE))
    
    if session.status != "Active":
        frappe.throw(_(ErrorMessages.SESSION_INACTIVE))
    
    # Get table and branch
    table_doc = frappe.get_doc("POS Table", session.table)
    
    # Create KOT
    kot_doc = frappe.get_doc({
        "doctype": "KOT",
        "posting_date": frappe.utils.today(),
        "posting_time": frappe.utils.nowtime(),
        "table": session.table,
        "branch": table_doc.branch,
        "qr_session": session_id,
        "customer_name": session.customer_name,
        "device_id": device_id,
        "special_instructions": special_instructions,
        "source": "QR"
    })
    
    # Add items
    for item in items:
        kot_doc.append("kot_items", {
            "item_code": item.get("item_code"),
            "qty": item.get("qty", 1),
            "note": item.get("note"),
            "kitchen_station": get_kitchen_station(item.get("item_code"))
        })
    
    kot_doc.insert()
    
    # Create Kitchen Display Orders
    create_kitchen_orders(kot_doc)
    
    # Notify order creation
    notify_order_update(kot_doc)
    
    return {
        "success": True,
        "order_id": kot_doc.name,
        "timestamp": frappe.utils.now(),
        "estimated_time": calculate_estimated_time(kot_doc)
    }

@frappe.whitelist(allow_guest=True)
@handle_api_error
def get_order_status(
    order_id: str,
    device_id: str
) -> Dict:
    """
    Get status pesanan QR
    
    Args:
        order_id: ID pesanan
        device_id: ID perangkat customer
        
    Returns:
        Dict: Order status
    """
    # Check cache first
    cache_key = f"{CacheKeys.QR_ORDER}:{order_id}"
    order_status = frappe.cache().get_value(cache_key)
    
    if not order_status:
        kot_doc = frappe.get_doc("KOT", order_id)
        
        if kot_doc.device_id != device_id:
            frappe.throw(_(ErrorMessages.INVALID_DEVICE))
        
        # Get kitchen orders status
        kitchen_orders = frappe.get_all(
            "Kitchen Display Order",
            filters={"kot_id": order_id},
            fields=["status", "kitchen_station"]
        )
        
        order_status = {
            "order_id": order_id,
            "status": kot_doc.status,
            "payment_status": kot_doc.payment_status,
            "creation": kot_doc.creation,
            "grand_total": kot_doc.grand_total,
            "kitchen_status": {
                order.kitchen_station: order.status
                for order in kitchen_orders
            }
        }
        
        # Cache for 30 seconds
        frappe.cache().set_value(
            cache_key,
            order_status,
            expires_in_sec=30
        )
    
    return order_status

@frappe.whitelist(allow_guest=True)
@handle_api_error
def modify_order(
    order_id: str,
    device_id: str,
    modifications: Dict
) -> Dict:
    """
    Modifikasi pesanan QR
    
    Args:
        order_id: ID pesanan
        device_id: ID perangkat customer
        modifications: Perubahan pesanan
        
    Returns:
        Dict: Modification status
    """
    kot_doc = frappe.get_doc("KOT", order_id)
    
    if kot_doc.device_id != device_id:
        frappe.throw(_(ErrorMessages.INVALID_DEVICE))
    
    if kot_doc.status not in [OrderStatus.NEW, OrderStatus.IN_PROGRESS]:
        frappe.throw(_(ErrorMessages.ORDER_MODIFICATION_DENIED))
    
    # Handle modifications
    if "add_items" in modifications:
        for item in modifications["add_items"]:
            kot_doc.append("kot_items", {
                "item_code": item.get("item_code"),
                "qty": item.get("qty", 1),
                "note": item.get("note"),
                "kitchen_station": get_kitchen_station(item.get("item_code"))
            })
    
    if "remove_items" in modifications:
        kot_doc.kot_items = [
            item for item in kot_doc.kot_items
            if item.name not in modifications["remove_items"]
        ]
    
    if "modify_items" in modifications:
        for mod in modifications["modify_items"]:
            for item in kot_doc.kot_items:
                if item.name == mod.get("item_name"):
                    if "qty" in mod:
                        item.qty = mod["qty"]
                    if "note" in mod:
                        item.note = mod["note"]
    
    if "special_instructions" in modifications:
        kot_doc.special_instructions = modifications["special_instructions"]
    
    kot_doc.save()
    
    # Update kitchen orders
    update_kitchen_orders(kot_doc)
    
    # Clear cache
    frappe.cache().delete_value(f"{CacheKeys.QR_ORDER}:{order_id}")
    
    # Notify modification
    notify_order_update(kot_doc)
    
    return {
        "success": True,
        "order_id": order_id,
        "timestamp": frappe.utils.now()
    }

def get_kitchen_station(item_code: str) -> str:
    """Get kitchen station for item"""
    return frappe.get_cached_value(
        "Item",
        item_code,
        "kitchen_station"
    )

def create_kitchen_orders(kot_doc) -> None:
    """Create kitchen display orders"""
    # Group items by kitchen station
    station_items = {}
    for item in kot_doc.kot_items:
        station = item.kitchen_station
        if station not in station_items:
            station_items[station] = []
        station_items[station].append(item)
    
    # Create order for each station
    for station, items in station_items.items():
        kds_doc = frappe.get_doc({
            "doctype": "Kitchen Display Order",
            "kot_id": kot_doc.name,
            "table": kot_doc.table,
            "kitchen_station": station,
            "status": OrderStatus.NEW,
            "special_instructions": kot_doc.special_instructions,
            "branch": kot_doc.branch
        })
        
        for item in items:
            kds_doc.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "note": item.note
            })
        
        kds_doc.insert()

def update_kitchen_orders(kot_doc) -> None:
    """Update existing kitchen orders"""
    existing_orders = frappe.get_all(
        "Kitchen Display Order",
        filters={"kot_id": kot_doc.name},
        fields=["name", "kitchen_station"]
    )
    
    # Group current items by station
    station_items = {}
    for item in kot_doc.kot_items:
        station = item.kitchen_station
        if station not in station_items:
            station_items[station] = []
        station_items[station].append(item)
    
    # Update or create orders
    for station, items in station_items.items():
        existing = next(
            (order for order in existing_orders 
             if order.kitchen_station == station),
            None
        )
        
        if existing:
            # Update existing order
            kds_doc = frappe.get_doc("Kitchen Display Order", existing.name)
            kds_doc.items = []
            for item in items:
                kds_doc.append("items", {
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "note": item.note
                })
            kds_doc.save()
        else:
            # Create new order
            kds_doc = frappe.get_doc({
                "doctype": "Kitchen Display Order",
                "kot_id": kot_doc.name,
                "table": kot_doc.table,
                "kitchen_station": station,
                "status": OrderStatus.NEW,
                "special_instructions": kot_doc.special_instructions,
                "branch": kot_doc.branch
            })
            
            for item in items:
                kds_doc.append("items", {
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "note": item.note
                })
            
            kds_doc.insert()

def calculate_estimated_time(kot_doc) -> int:
    """Calculate estimated preparation time in minutes"""
    max_prep_time = 0
    
    for item in kot_doc.kot_items:
        prep_time = frappe.get_cached_value(
            "Item",
            item.item_code,
            "preparation_time"
        ) or 0
        
        max_prep_time = max(max_prep_time, prep_time)
    
    return max_prep_time