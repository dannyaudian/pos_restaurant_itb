import frappe

def kds_permissions(doc, user=None, permission_type=None):
    """Custom permission handler for Kitchen Display Order"""
    if not user:
        user = frappe.session.user
    
    # System Manager can do anything
    if "System Manager" in frappe.get_roles(user):
        return True
        
    # Kitchen User can only see KDS for their branch
    if "Kitchen User" in frappe.get_roles(user):
        user_branch = frappe.db.get_value("Employee", {"user_id": user}, "branch")
        if user_branch and doc.branch == user_branch:
            return True
    
    return False