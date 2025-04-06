# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 09:31:46'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.utils import now
from pos_restaurant_itb.utils import error_handlers
from pos_restaurant_itb.utils.constants import KOT_STATUSES

@error_handlers.handle_pos_errors()
def update_kds_status_from_kot(kds_name: str) -> None:
    """
    Update Kitchen Display Order (KDS) status based on KOT items status
    
    Status Logic:
    - All "Served"            → status = "Served"
    - All "Ready" / "Served"  → status = "Ready"
    - Any "Cooking"           → status = "In Progress"
    - Others                  → status = "New"
    
    Args:
        kds_name (str): Kitchen Display Order name
        
    Raises:
        ValidationError: If validation fails
    """
    if not kds_name:
        raise error_handlers.ValidationError(
            "KDS name is required",
            "Validation Error"
        )

    try:
        kds = frappe.get_doc("Kitchen Display Order", kds_name)
        statuses = [
            item.kot_status 
            for item in kds.item_list 
            if not item.cancelled
        ]

        if not statuses:
            new_status = "New"
        elif all(s == "Served" for s in statuses):
            new_status = "Served"
        elif all(s in ("Ready", "Served") for s in statuses):
            new_status = "Ready"
        elif any(s == "Cooking" for s in statuses):
            new_status = "In Progress"
        else:
            new_status = "New"

        if kds.status != new_status:
            kds.status = new_status
            kds.last_updated = now()
            kds.save(ignore_permissions=True)
            frappe.db.commit()
            
            frappe.publish_realtime(
                'kds_status_update',
                {
                    'kds_name': kds_name,
                    'status': new_status,
                    'timestamp': now()
                }
            )

    except Exception as e:
        frappe.log_error(
            message=f"""
            Failed to update KDS status
            -------------------------
            KDS: {kds_name}
            Error: {str(e)}
            Traceback: {frappe.get_traceback()}
            """,
            title="❌ KDS Update Error"
        )
        raise

@frappe.whitelist()
@error_handlers.handle_pos_errors()
def bulk_update_kot_status(updates: list) -> dict:
    """
    Batch update KOT items status
    
    Args:
        updates (list): List of dicts with kot_id, item_code, and new_status
        
    Returns:
        dict: Update results summary
    """
    if not updates:
        raise error_handlers.ValidationError(
            "No updates provided",
            "Validation Error"
        )
        
    results = {
        "success": [],
        "failed": []
    }
    
    for update in updates:
        try:
            kot = frappe.get_doc("KOT", update.get("kot_id"))
            item_code = update.get("item_code")
            new_status = update.get("new_status")
            
            if new_status not in KOT_STATUSES:
                raise error_handlers.ValidationError(
                    f"Invalid status: {new_status}",
                    "Status Error"
                )
                
            updated = False
            for item in kot.kot_items:
                if item.item_code == item_code:
                    item.kot_status = new_status
                    item.kot_last_update = now()
                    updated = True
                    break
                    
            if updated:
                kot.save(ignore_permissions=True)
                results["success"].append(update)
            else:
                results["failed"].append({
                    **update,
                    "reason": "Item not found"
                })
                
        except Exception as e:
            results["failed"].append({
                **update,
                "reason": str(e)
            })
            
    frappe.db.commit()
    return results