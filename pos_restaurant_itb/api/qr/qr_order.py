# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 01:37:12'
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
    CacheKeys,
    QR_ORDER_STATUSES
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
    
    # Create QR Order
    qr_order = frappe.get_doc({
        "doctype": "QR Order",
        "posting_date": frappe.utils.today(),
        "posting_time": frappe.utils.nowtime(),
        "table": session.table,
        "branch": table_doc.branch,
        "qr_session": session_id,
        "customer_name": session.customer_name,
        "device_id": device_id,
        "special_instructions": special_instructions,
        "status": "Draft",
        "payment_status": "Pending",
        "source": "QR",
        "created_via_api": 1
    })
    
    # Add items to QR Order with full item details
    for item in items:
        item_doc = frappe.get_doc("Item", item.get("item_code"))
        qr_order.append("items", {
            "item_code": item.get("item_code"),
            "item_name": item_doc.item_name,
            "qty": item.get("qty", 1),
            "rate": item_doc.rate,
            "amount": item_doc.rate * item.get("qty", 1),
            "note": item.get("note"),
            "kitchen_station": item_doc.kitchen_station
        })
    
    # Calculate totals
    qr_order.calculate_totals()
    qr_order.insert()
    # Create KOT
    kot_doc = frappe.get_doc({
        "doctype": "KOT",
        "posting_date": qr_order.posting_date,
        "posting_time": qr_order.posting_time,
        "table": qr_order.table,
        "branch": qr_order.branch,
        "qr_session": session_id,
        "qr_order": qr_order.name,
        "customer_name": qr_order.customer_name,
        "device_id": device_id,
        "special_instructions": special_instructions,
        "source": "QR"
    })
    
    # Copy items to KOT with detailed information
    for item in qr_order.items:
        kot_doc.append("kot_items", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "rate": item.rate,
            "amount": item.amount,
            "note": item.note,
            "kitchen_station": item.kitchen_station,
            "qr_order_item": item.name
        })
    
    kot_doc.insert()
    
    # Create Kitchen Display Orders
    create_kitchen_orders(kot_doc)
    
    # Update QR Order with KOT reference and status
    qr_order.db_set({
        'kot': kot_doc.name,
        'status': 'In Progress'
    })
    
    # Notify order creation
    notify_order_update({
        'qr_order': {
            'id': qr_order.name,
            'status': qr_order.status
        },
        'kot': {
            'id': kot_doc.name,
            'status': kot_doc.status
        }
    })
    
    return {
        "success": True,
        "data": {
            "order": {
                "id": qr_order.name,
                "status": qr_order.status,
                "payment_status": qr_order.payment_status,
                "grand_total": qr_order.grand_total,
                "created_at": qr_order.creation,
                "items": [{
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "qty": item.qty,
                    "rate": item.rate,
                    "amount": item.amount,
                    "note": item.note,
                    "kitchen_station": item.kitchen_station
                } for item in qr_order.items]
            },
            "kot": {
                "id": kot_doc.name,
                "status": kot_doc.status,
                "created_at": kot_doc.creation
            }
        },
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
        order_id: ID pesanan QR
        device_id: ID perangkat customer
        
    Returns:
        Dict: Order status
    """
    # Check cache first
    cache_key = f"{CacheKeys.QR_ORDER}:{order_id}"
    order_status = frappe.cache().get_value(cache_key)
    
    if not order_status:
        qr_order = frappe.get_doc("QR Order", order_id)
        
        if qr_order.device_id != device_id:
            frappe.throw(_(ErrorMessages.INVALID_DEVICE))
        
        # Get KOT status
        kot_status = None
        kitchen_orders = []
        if qr_order.kot:
            kot_doc = frappe.get_doc("KOT", qr_order.kot)
            kot_status = kot_doc.status
            
            # Get kitchen orders status
            kitchen_orders = frappe.get_all(
                "Kitchen Display Order",
                filters={"kot_id": qr_order.kot},
                fields=["status", "kitchen_station"]
            )
        
        order_status = {
            "success": True,
            "data": {
                "order": {
                    "id": order_id,
                    "status": qr_order.status,
                    "payment_status": qr_order.payment_status,
                    "grand_total": qr_order.grand_total,
                    "created_at": qr_order.creation,
                    "modified_at": qr_order.modified,
                    "items": [{
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "qty": item.qty,
                        "rate": item.rate,
                        "amount": item.amount,
                        "note": item.note,
                        "kitchen_station": item.kitchen_station
                    } for item in qr_order.items]
                },
                "kot": {
                    "id": qr_order.kot,
                    "status": kot_status,
                    "kitchen_status": {
                        order.kitchen_station: order.status
                        for order in kitchen_orders
                    } if kitchen_orders else {}
                }
            },
            "timestamp": frappe.utils.now()
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
        order_id: ID pesanan QR
        device_id: ID perangkat customer
        modifications: Perubahan pesanan
        
    Returns:
        Dict: Modification status
    """
    qr_order = frappe.get_doc("QR Order", order_id)
    
    if qr_order.device_id != device_id:
        frappe.throw(_(ErrorMessages.INVALID_DEVICE))
    
    if qr_order.status not in ["Draft", "In Progress"]:
        frappe.throw(_(ErrorMessages.ORDER_MODIFICATION_DENIED))
        
    # Validate if order can be modified based on status
    if qr_order.status not in QR_ORDER_STATUSES or not QR_ORDER_STATUSES[qr_order.status]:
        frappe.throw(_(ErrorMessages.ORDER_MODIFICATION_DENIED))
    
    # Get associated KOT
    kot_doc = None
    if qr_order.kot:
        kot_doc = frappe.get_doc("KOT", qr_order.kot)
        if kot_doc.status not in [OrderStatus.NEW, OrderStatus.IN_PROGRESS]:
            frappe.throw(_(ErrorMessages.ORDER_MODIFICATION_DENIED))
    
    # Handle modifications
    if "add_items" in modifications:
        for item in modifications["add_items"]:
            item_doc = frappe.get_doc("Item", item.get("item_code"))
            # Add to QR Order with full item details
            qr_item = qr_order.append("items", {
                "item_code": item.get("item_code"),
                "item_name": item_doc.item_name,
                "qty": item.get("qty", 1),
                "rate": item_doc.rate,
                "amount": item_doc.rate * item.get("qty", 1),
                "note": item.get("note"),
                "kitchen_station": item_doc.kitchen_station
            })
            
            # Add to KOT if exists
            if kot_doc:
                kot_doc.append("kot_items", {
                    "item_code": item.get("item_code"),
                    "item_name": item_doc.item_name,
                    "qty": item.get("qty", 1),
                    "rate": item_doc.rate,
                    "amount": item_doc.rate * item.get("qty", 1),
                    "note": item.get("note"),
                    "kitchen_station": qr_item.kitchen_station,
                    "qr_order_item": qr_item.name
                })
    
    if "remove_items" in modifications:
        # Remove from QR Order
        qr_order.items = [
            item for item in qr_order.items
            if item.name not in modifications["remove_items"]
        ]
        
        # Remove from KOT if exists
        if kot_doc:
            kot_doc.kot_items = [
                item for item in kot_doc.kot_items
                if item.qr_order_item not in modifications["remove_items"]
            ]
    
    if "modify_items" in modifications:
        for mod in modifications["modify_items"]:
            # Modify QR Order items
            for item in qr_order.items:
                if item.name == mod.get("item_name"):
                    if "qty" in mod:
                        item.qty = mod["qty"]
                        item.amount = item.rate * item.qty
                    if "note" in mod:
                        item.note = mod["note"]
                        
            # Modify KOT items if exists
            if kot_doc:
                for item in kot_doc.kot_items:
                    if item.qr_order_item == mod.get("item_name"):
                        if "qty" in mod:
                            item.qty = mod["qty"]
                            item.amount = item.rate * item.qty
                        if "note" in mod:
                            item.note = mod["note"]
    
    if "special_instructions" in modifications:
        qr_order.special_instructions = modifications["special_instructions"]
        if kot_doc:
            kot_doc.special_instructions = modifications["special_instructions"]
    
    # Recalculate totals
    qr_order.calculate_totals()
    
    # Save documents
    qr_order.save()
    if kot_doc:
        kot_doc.save()
        update_kitchen_orders(kot_doc)
    
    # Clear cache
    frappe.cache().delete_value(f"{CacheKeys.QR_ORDER}:{order_id}")
    
    # Notify modification
    notify_order_update({
        'qr_order': {
            'id': qr_order.name,
            'status': qr_order.status
        },
        'kot': {
            'id': kot_doc.name if kot_doc else None,
            'status': kot_doc.status if kot_doc else None
        }
    })
    
    return {
        "success": True,
        "data": {
            "order": {
                "id": order_id,
                "status": qr_order.status,
                "payment_status": qr_order.payment_status,
                "grand_total": qr_order.grand_total,
                "modified_at": qr_order.modified,
                "items": [{
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "qty": item.qty,
                    "rate": item.rate,
                    "amount": item.amount,
                    "note": item.note,
                    "kitchen_station": item.kitchen_station
                } for item in qr_order.items]
            },
            "kot": {
                "id": kot_doc.name if kot_doc else None,
                "status": kot_doc.status if kot_doc else None
            }
        },
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
            "branch": kot_doc.branch,
            "qr_order": kot_doc.qr_order,
            "source": "QR"
        })
        
        for item in items:
            kds_doc.append("items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "note": item.note,
                "qr_order_item": item.qr_order_item
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
                    "item_name": item.item_name,
                    "qty": item.qty,
                    "rate": item.rate,
                    "amount": item.amount,
                    "note": item.note,
                    "qr_order_item": item.qr_order_item
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
                "branch": kot_doc.branch,
                "qr_order": kot_doc.qr_order,
                "source": "QR"
            })
            
            for item in items:
                kds_doc.append("items", {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "qty": item.qty,
                    "rate": item.rate,
                    "amount": item.amount,
                    "note": item.note,
                    "qr_order_item": item.qr_order_item
                })
            
            kds_doc.insert()

def calculate_estimated_time(kot_doc) -> int:
    """Calculate estimated preparation time in minutes"""
    max_prep_time = 0
    
    for item in kot_doc.kot_items:
        item_doc = frappe.get_cached_doc("Item", item.item_code)
        prep_time = item_doc.preparation_time or 0
        max_prep_time = max(max_prep_time, prep_time)
    
    return max_prep_time

def calculate_totals(self):
    """Calculate totals for QR Order"""
    total = 0
    for item in self.items:
        item.amount = flt(item.qty * item.rate)
        total += item.amount
    
    self.grand_total = flt(total)
    
    return self.grand_total