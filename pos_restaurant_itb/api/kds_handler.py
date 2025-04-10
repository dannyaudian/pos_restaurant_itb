# File: pos_restaurant_itb/api/kds_handler.py

import frappe
from frappe import _
from frappe.utils import now_datetime

@frappe.whitelist()
def create_kds_from_kot(kot_id):
    """
    Create Kitchen Display Order (KDS) automatically from KOT.
    Will take all items from KOT and copy to KDS.
    """
    if not kot_id:
        frappe.throw(_("KOT ID is required."))
    
    kot = frappe.get_doc("Kitchen Order Ticket", kot_id)
    
    # Validate branch isolation - only process for active branches
    branch_is_active = frappe.db.get_value("Branch", kot.branch, "is_active")
    if not branch_is_active:
        frappe.throw(_("Cannot create kitchen display for inactive branch."))
    
    # Prevent duplication
    if frappe.db.exists("Kitchen Display Order", {"kot_id": kot.name}):
        return {
            "status": "warning",
            "message": _(f"KDS for {kot.name} already exists."),
            "kds_name": frappe.db.get_value("Kitchen Display Order", {"kot_id": kot.name})
        }
    
    kds = frappe.new_doc("Kitchen Display Order")
    kds.kot_id = kot.name
    kds.table_number = kot.table
    kds.branch = kot.branch  # Ensure branch isolation
    kds.status = "New"
    kds.last_updated = now_datetime()
    
    for item in kot.kot_items:
        # Copy all fields including dynamic attributes
        kds.append("item_list", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "note": item.note,
            "kot_status": item.kot_status,
            "kot_last_update": item.kot_last_update,
            "dynamic_attributes": item.dynamic_attributes,  # Using dynamic_attributes as per your schema
            "cancelled": item.cancelled,
            "cancellation_note": item.cancellation_note
        })
    
    # Set flag to prevent circular updates
    frappe.flags.in_kot_update = True
    kds.insert(ignore_permissions=True)
    frappe.flags.in_kot_update = False
    
    frappe.db.commit()
    
    return {
        "status": "success",
        "message": _(f"✅ KDS successfully created from KOT {kot.name}"),
        "kds_name": kds.name
    }