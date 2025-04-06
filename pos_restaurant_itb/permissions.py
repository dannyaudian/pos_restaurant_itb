import frappe
from frappe import _
from frappe.utils import now_datetime

# Add timestamp and author information
__created_date__ = '2025-04-06 07:34:08'
__author__ = 'dannyaudian'

def get_user_permitted_branches(user=None):
    """
    Get list of branches permitted for user using ERPNext's User Permission
    Multiple branches per user are supported
    """
    if not user:
        user = frappe.session.user
        
    if "System Manager" in frappe.get_roles(user):
        # System Manager can access all branches
        return [d.name for d in frappe.get_all("Branch")]
        
    # Get ALL permitted branches from User Permission
    branches = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Branch",
            "enabled": 1
        },
        pluck="for_value"
    )
    
    return branches

def get_pos_order_permission_query(user):
    """
    Permission query untuk POS Order berdasarkan branch permission
    """
    if "System Manager" in frappe.get_roles(user):
        return ""
        
    branches = get_user_permitted_branches(user)
    if not branches:
        return "1=0"
        
    branch_condition = """`tabPOS Order`.branch in ({branches})""".format(
        branches=",".join(["'{}'".format(branch) for branch in branches])
    )
    
    if "Waiter" in frappe.get_roles(user):
        # Waiter hanya bisa lihat order yang dia buat di branch-nya
        return f"{branch_condition} AND (`tabPOS Order`.owner = '{user}' OR `tabPOS Order`.waiter = '{user}')"
    
    if any(role in frappe.get_roles(user) for role in ["Kitchen Staff", "Cashier", "Outlet Manager"]):
        # Staff lain bisa lihat semua order di branch yang diizinkan
        return branch_condition
        
    return "1=0"

def get_kot_permission_query(user):
    """
    Permission query untuk Kitchen Order Ticket (KOT)
    """
    if "System Manager" in frappe.get_roles(user):
        return ""
        
    branches = get_user_permitted_branches(user)
    if not branches:
        return "1=0"
        
    branch_condition = """`tabKOT`.branch in ({branches})""".format(
        branches=",".join(["'{}'".format(branch) for branch in branches])
    )
    
    if "Kitchen Staff" in frappe.get_roles(user):
        # Kitchen staff bisa akses penuh KOT di branch-nya
        return branch_condition
        
    if "Waiter" in frappe.get_roles(user):
        # Waiter hanya bisa lihat KOT yang dia buat di branch-nya
        return f"{branch_condition} AND (`tabKOT`.owner = '{user}' OR `tabKOT`.waiter = '{user}')"
        
    if any(role in frappe.get_roles(user) for role in ["Cashier", "Outlet Manager"]):
        # Cashier dan Outlet Manager bisa lihat semua KOT di branch yang diizinkan
        return branch_condition
        
    return "1=0"

def get_kds_permission_query(user):
    """
    Permission query untuk Kitchen Display System
    """
    if "System Manager" in frappe.get_roles(user):
        return ""
        
    branches = get_user_permitted_branches(user)
    if not branches:
        return "1=0"
        
    branch_condition = """`tabKitchen Display Order`.branch in ({branches})""".format(
        branches=",".join(["'{}'".format(branch) for branch in branches])
    )
    
    if "Kitchen Staff" in frappe.get_roles(user):
        # Kitchen staff punya akses penuh ke KDS di branch-nya
        return branch_condition
        
    if any(role in frappe.get_roles(user) for role in ["Waiter", "Cashier"]):
        # Waiter dan Cashier hanya bisa lihat KDS yang sudah disubmit
        return f"{branch_condition} AND `tabKitchen Display Order`.docstatus = 1"
        
    if "Outlet Manager" in frappe.get_roles(user):
        # Outlet Manager bisa lihat semua KDS di branch yang diizinkan
        return branch_condition
        
    return "1=0"

def get_pos_invoice_permission_query(user):
    """
    Permission query untuk POS Invoice
    """
    if "System Manager" in frappe.get_roles(user):
        return ""
        
    branches = get_user_permitted_branches(user)
    if not branches:
        return "1=0"
        
    branch_condition = """`tabPOS Invoice`.branch in ({branches})""".format(
        branches=",".join(["'{}'".format(branch) for branch in branches])
    )
    
    if "Cashier" in frappe.get_roles(user):
        # Cashier bisa buat dan lihat invoice di branch-nya
        return branch_condition
        
    if "Waiter" in frappe.get_roles(user):
        # Waiter hanya bisa lihat invoice yang sudah disubmit
        return f"{branch_condition} AND `tabPOS Invoice`.docstatus = 1"
        
    if "Kitchen Staff" in frappe.get_roles(user):
        # Kitchen staff tidak bisa akses invoice
        return "1=0"
        
    if "Outlet Manager" in frappe.get_roles(user):
        # Outlet Manager bisa lihat semua invoice di branch yang diizinkan
        return branch_condition
        
    return "1=0"

def has_permission(doc, user=None, permission_type=None):
    """
    Permission handler untuk custom doctype
    """
    if not user:
        user = frappe.session.user
        
    if "System Manager" in frappe.get_roles(user):
        return True
        
    # Untuk document baru
    if doc.get('__islocal'):
        return True
        
    # Cek permission berdasarkan role dan branch
    if doc.doctype in ["POS Order", "KOT", "Kitchen Display Order", "POS Invoice"]:
        branches = get_user_permitted_branches(user)
        
        if not branches:
            return False
            
        if doc.branch not in branches:
            return False
            
        # Permission type specific checks
        if permission_type == "write":
            if doc.doctype == "POS Order" and "Waiter" in frappe.get_roles(user):
                return doc.owner == user or doc.waiter == user
                
            if doc.doctype == "KOT" and "Kitchen Staff" in frappe.get_roles(user):
                return True
                
            if doc.doctype == "POS Invoice" and "Cashier" in frappe.get_roles(user):
                return True
                
            if "Outlet Manager" in frappe.get_roles(user):
                return True
                
        return True
        
    return False