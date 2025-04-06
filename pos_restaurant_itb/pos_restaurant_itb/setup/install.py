# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 08:53:56'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _

def after_install():
    """Setup after app installation"""
    setup_custom_roles()
    setup_pos_settings()
    setup_print_formats()
    create_custom_fields()

def setup_custom_roles():
    """Setup custom roles for POS Restaurant"""
    roles = [
        {
            "role_name": "Restaurant Manager",
            "desk_access": 1,
            "description": "Full access to restaurant operations and settings"
        },
        {
            "role_name": "Outlet Manager",
            "desk_access": 1,
            "description": "Manage specific outlet/branch operations"
        },
        {
            "role_name": "Waiter",
            "desk_access": 1,
            "description": "Handle orders and table service"
        },
        {
            "role_name": "Kitchen User",
            "desk_access": 1,
            "description": "Manage kitchen operations and order preparation"
        },
        {
            "role_name": "Cashier",
            "desk_access": 1,
            "description": "Handle payments and billing"
        }
    ]
    
    for role in roles:
        if not frappe.db.exists("Role", role["role_name"]):
            doc = frappe.new_doc("Role")
            doc.update(role)
            doc.save()
            frappe.msgprint(_(f"✅ Created role: {role['role_name']}"))

def setup_pos_settings():
    """Setup POS Settings"""
    if not frappe.db.exists("POS Settings", "POS Settings"):
        doc = frappe.new_doc("POS Settings")
        doc.update({
            "disable_rounded_total": 0,
            "allow_delete": 1,
            "allow_user_to_edit_rate": 0,
            "allow_user_to_edit_discount": 0,
            "print_format": "POS Invoice",
            "pos_session_timeout": 0,
            "validate_stock_on_save": 0
        })
        doc.save()
        frappe.msgprint(_("✅ POS Settings created"))

def setup_print_formats():
    """Setup print formats for POS"""
    from frappe.modules.utils import sync_customizations
    sync_customizations("pos_restaurant_itb")
    frappe.msgprint(_("✅ Print formats synchronized"))

def create_custom_fields():
    """Create custom fields"""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    
    custom_fields = {
        "POS Profile": [
            {
                "fieldname": "branch",
                "label": "Branch",
                "fieldtype": "Link",
                "options": "Branch",
                "insert_after": "company",
                "reqd": 1
            },
            {
                "fieldname": "restaurant_settings_section",
                "label": "Restaurant Settings",
                "fieldtype": "Section Break",
                "insert_after": "branch"
            },
            {
                "fieldname": "default_order_type",
                "label": "Default Order Type",
                "fieldtype": "Select",
                "options": "\nDine In\nTakeaway\nDelivery",
                "insert_after": "restaurant_settings_section"
            }
        ],
        "Item": [
            {
                "fieldname": "restaurant_item_settings_section",
                "label": "Restaurant Item Settings",
                "fieldtype": "Section Break",
                "insert_after": "item_group"
            },
            {
                "fieldname": "is_restaurant_item",
                "label": "Is Restaurant Item",
                "fieldtype": "Check",
                "insert_after": "restaurant_item_settings_section",
                "default": 0
            },
            {
                "fieldname": "preparation_time",
                "label": "Preparation Time (minutes)",
                "fieldtype": "Int",
                "insert_after": "is_restaurant_item",
                "depends_on": "eval:doc.is_restaurant_item==1"
            }
        ]
    }
    
    create_custom_fields(custom_fields)
    frappe.msgprint(_("✅ Custom fields created"))