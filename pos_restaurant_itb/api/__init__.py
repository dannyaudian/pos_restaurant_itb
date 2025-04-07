# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 11:17:53'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.utils import now

# Lazy loading untuk menghindari circular imports
def get_constants():
    from pos_restaurant_itb.utils import constants
    return constants

def get_api_handler():
    from pos_restaurant_itb.utils.api import handle_response
    return handle_response

@frappe.whitelist()
def get_pos_settings():
    """Get POS settings."""
    constants = get_constants()
    handler = get_api_handler()
    
    try:
        settings = frappe.get_doc("POS Settings")
        return handler.success_response(settings)
    except Exception as e:
        return handler.error_response(str(e))

@frappe.whitelist()
def get_table_status():
    """Get restaurant table status."""
    constants = get_constants()
    handler = get_api_handler()
    
    try:
        tables = frappe.get_all(
            "Restaurant Table",
            fields=["name", "status", "capacity"],
            filters={"status": ["!=", constants.TABLE_STATUS_INACTIVE]}
        )
        return handler.success_response(tables)
    except Exception as e:
        return handler.error_response(str(e))

@frappe.whitelist()
def get_menu_items():
    """Get restaurant menu items."""
    constants = get_constants()
    handler = get_api_handler()
    
    try:
        items = frappe.get_all(
            "Item",
            fields=["item_code", "item_name", "description", "rate", "image"],
            filters={"is_menu_item": 1, "disabled": 0}
        )
        return handler.success_response(items)
    except Exception as e:
        return handler.error_response(str(e))

@frappe.whitelist()
def create_pos_order(order_data):
    """Create POS order."""
    handler = get_api_handler()
    
    try:
        order = frappe.new_doc("POS Order")
        order.update(order_data)
        order.insert(ignore_permissions=True)
        order.submit()
        
        return handler.success_response({
            "message": _("Order created successfully"),
            "order": order.as_dict()
        })
    except Exception as e:
        return handler.error_response(str(e))

@frappe.whitelist()
def cancel_pos_order(order_name):
    """Cancel POS order."""
    handler = get_api_handler()
    
    try:
        order = frappe.get_doc("POS Order", order_name)
        order.cancel()
        
        return handler.success_response({
            "message": _("Order cancelled successfully")
        })
    except Exception as e:
        return handler.error_response(str(e))