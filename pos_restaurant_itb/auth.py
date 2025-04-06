import frappe
from frappe import _

def has_pos_permission(doc=None):
    """
    Check if user has permission to access POS features
    """
    if not frappe.session.user:
        return False
        
    roles = frappe.get_roles()
    allowed_roles = ['Outlet Manager', 'Waiter', 'Cashier', 'System Manager']
    
    return any(role in roles for role in allowed_roles)

def has_kitchen_permission(doc=None):
    """
    Check if user has permission to access kitchen features
    """
    if not frappe.session.user:
        return False
        
    roles = frappe.get_roles()
    allowed_roles = ['Kitchen Staff', 'Outlet Manager', 'System Manager']
    
    return any(role in roles for role in allowed_roles)

def has_manager_permission(doc=None):
    """
    Check if user has manager level permissions
    """
    if not frappe.session.user:
        return False
        
    roles = frappe.get_roles()
    allowed_roles = ['Outlet Manager', 'System Manager']
    
    return any(role in roles for role in allowed_roles)

def has_cashier_permission(doc=None):
    """
    Check if user has cashier level permissions
    """
    if not frappe.session.user:
        return False
        
    roles = frappe.get_roles()
    allowed_roles = ['Cashier', 'Outlet Manager', 'System Manager']
    
    return any(role in roles for role in allowed_roles)

def has_invoice_permission(doc=None):
    """
    Check if user has permission to handle invoices and payments
    """
    if not frappe.session.user:
        return False
        
    roles = frappe.get_roles()
    allowed_roles = ['Cashier', 'Outlet Manager', 'System Manager']
    
    return any(role in roles for role in allowed_roles)