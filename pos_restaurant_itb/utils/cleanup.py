import frappe
from frappe.utils import now_datetime, add_days

def clear_old_kitchen_sessions():
    """Clear kitchen sessions older than 24 hours"""
    cutoff_time = add_days(now_datetime(), -1)
    
    # Clear old KDS sessions
    old_kds = frappe.get_all(
        "Kitchen Display Order",
        filters={
            "creation": ["<", cutoff_time],
            "status": ["in", ["Served", "Cancelled"]]
        },
        pluck="name"
    )
    
    count = 0
    for kds in old_kds:
        try:
            # Either archive or delete
            frappe.db.set_value("Kitchen Display Order", kds, "archived", 1)
            count += 1
        except Exception as e:
            frappe.log_error(f"Failed to archive KDS {kds}: {str(e)}", "Cleanup Error")
    
    frappe.db.commit()
    
    if count > 0:
        frappe.log_error(f"Cleared {count} old kitchen sessions", "Kitchen Cleanup")