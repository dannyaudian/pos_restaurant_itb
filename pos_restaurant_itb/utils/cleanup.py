import frappe
from frappe.utils import now_datetime, add_days

def clear_old_kitchen_sessions():
    """Clear kitchen sessions older than 24 hours"""
    cutoff_time = add_days(now_datetime(), -1)
    
    # Example: Clear old KDS sessions
    old_kds = frappe.get_all(
        "Kitchen Display Order",
        filters={
            "creation": ["<", cutoff_time],
            "status": ["in", ["Served", "Cancelled"]]
        },
        pluck="name"
    )
    
    for kds in old_kds:
        frappe.db.set_value("Kitchen Display Order", kds, "archived", 1)
    
    frappe.db.commit()
    frappe.log_error(f"Cleared {len(old_kds)} old kitchen sessions", "Cleanup Job")