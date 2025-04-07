# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 09:03:48'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.utils import now, cint, flt
from pos_restaurant_itb.api.utils import get_default_company

# Lazy loading untuk menghindari circular imports
def get_security():
    from pos_restaurant_itb.utils import security
    return security

def get_error_handler():
    from pos_restaurant_itb.utils.error_handlers import handle_api_error
    return handle_api_error

@get_error_handler()
def create_kot_from_pos_order(pos_order_name):
    """Create Kitchen Order Ticket (KOT) from POS Order.
    
    Args:
        pos_order_name (str): Name of the POS Order document
        
    Returns:
        dict: Created KOT document data
    """
    security = get_security()
    if not security.has_permission("POS Order", pos_order_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    pos_order = frappe.get_doc("POS Order", pos_order_name)
    
    # Validate if KOT already exists
    if frappe.db.exists("Kitchen Order Ticket", {"pos_order": pos_order_name}):
        frappe.throw(_("KOT already exists for this order"))
        
    # Create new KOT
    kot = frappe.new_doc("Kitchen Order Ticket")
    kot.pos_order = pos_order_name
    kot.company = get_default_company()
    kot.table = pos_order.table
    kot.order_type = pos_order.order_type
    kot.customer = pos_order.customer
    kot.posting_date = now()
    
    # Add items from POS Order
    for item in pos_order.items:
        if not item.is_food_item:
            continue
            
        kot.append("items", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "rate": item.rate,
            "amount": item.amount,
            "notes": item.notes
        })
        
    kot.insert(ignore_permissions=True)
    
    return {
        "kot": kot.name,
        "message": _("KOT created successfully")
    }

def create_kot_items(kot, pos_order):
    """Create KOT items from POS Order items.
    
    Args:
        kot (object): KOT document object
        pos_order (object): POS Order document object
    """
    for item in pos_order.items:
        if not item.is_food_item:
            continue
            
        kot.append("items", {
            "item_code": item.item_code,
            "item_name": item.item_name, 
            "qty": item.qty,
            "rate": item.rate,
            "amount": item.amount,
            "notes": item.notes
        })

def get_kot_items(pos_order_name):
    """Get KOT items for POS Order.
    
    Args:
        pos_order_name (str): Name of the POS Order document
        
    Returns:
        list: List of KOT items
    """
    security = get_security()
    if not security.has_permission("POS Order", pos_order_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
        
    kot_list = frappe.get_all(
        "Kitchen Order Ticket",
        filters={"pos_order": pos_order_name},
        fields=["name"]
    )
    
    items = []
    for kot in kot_list:
        kot_doc = frappe.get_doc("Kitchen Order Ticket", kot.name)
        for item in kot_doc.items:
            items.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "notes": item.notes,
                "kot": kot.name
            })
            
    return items