# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 10:33:09'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _

# Lazy loading untuk menghindari circular imports
def get_constants():
    from pos_restaurant_itb.utils import constants
    return constants

def get_security():
    from pos_restaurant_itb.utils.security import validate_permission
    return validate_permission

def validate_pos_order(doc, method=None):
    """Validate POS Order document before save.
    
    Args:
        doc: POS Order document object
        method: Trigger method
    """
    constants = get_constants()
    security = get_security()
    
    if not security(doc):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
        
    validate_items(doc)
    validate_payments(doc)
    calculate_totals(doc)
    
def validate_items(doc):
    """Validate POS Order items.
    
    Args:
        doc: POS Order document object
    """
    if not doc.items:
        frappe.throw(_("Order must have at least one item"))
        
    for item in doc.items:
        if not item.qty or item.qty <= 0:
            frappe.throw(_("Item quantity must be greater than zero"))
            
        if not item.rate or item.rate <= 0:
            frappe.throw(_("Item rate must be greater than zero"))
            
def validate_payments(doc):
    """Validate POS Order payments.
    
    Args:
        doc: POS Order document object  
    """
    if not doc.payments:
        frappe.throw(_("Order must have at least one payment"))
        
    total_paid = sum(payment.amount for payment in doc.payments)
    if total_paid < doc.grand_total:
        frappe.throw(_("Total payment amount must be equal to grand total"))
        
def calculate_totals(doc):
    """Calculate POS Order totals.
    
    Args:
        doc: POS Order document object
    """
    constants = get_constants()
    
    doc.total = sum(item.amount for item in doc.items)
    doc.tax_amount = doc.total * (constants.TAX_RATE / 100)
    doc.grand_total = doc.total + doc.tax_amount
    
    if doc.discount_type == "Percentage":
        doc.discount_amount = doc.total * (doc.discount_percentage / 100)
    doc.grand_total -= doc.discount_amount