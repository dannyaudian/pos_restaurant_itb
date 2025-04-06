# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 08:18:16'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from pos_restaurant_itb.api.kot_status_update import update_kds_status_from_kot
from typing import Dict, Optional, Union

@frappe.whitelist()
def send_to_kitchen(pos_order: str) -> str:
    """
    Send order items to kitchen by creating KOT.
    
    Args:
        pos_order (str): POS Order ID to send to kitchen
        
    Returns:
        str: HTML rendered KOT template if successful
        
    Raises:
        frappe.ValidationError: If no items to send or error occurs
    """
    from pos_restaurant_itb.api.create_kot import create_kot_from_pos_order

    kot_name = create_kot_from_pos_order(pos_order_id=pos_order)

    if not kot_name:
        frappe.throw(_("❌ No additional items to send to kitchen."))

    kot_doc = frappe.get_doc("KOT", kot_name)

    # Render KOT HTML template
    return frappe.render_template(
        "templates/kot_print.html",
        {"kot": kot_doc}
    )

@frappe.whitelist()
def cancel_pos_order_item(item_name: str, reason: Optional[str] = None) -> Dict:
    """
    Cancel specific item in POS Order. Only allowed for Outlet Manager.
    
    Args:
        item_name (str): POS Order Item name to cancel
        reason (str, optional): Cancellation reason
        
    Returns:
        Dict: Response with status and message
        
    Raises:
        frappe.ValidationError: If user doesn't have permission or error occurs
    """
    if not frappe.has_role("Outlet Manager"):
        frappe.throw(_("Only Outlet Manager can cancel items."))

    doc = frappe.get_doc("POS Order Item", item_name)

    doc.cancelled = 1
    doc.cancellation_note = reason or "Cancelled manually"
    doc.rate = 0
    doc.amount = 0
    doc.save()

    # Recalculate parent total
    parent = frappe.get_doc("POS Order", doc.parent)
    total = sum(i.amount for i in parent.pos_order_items if not i.cancelled)
    parent.total_amount = total
    parent.save()

    frappe.db.commit()

    return {
        "status": "success",
        "message": _(f"Item {doc.item_code} cancelled.")
    }

@frappe.whitelist()
def mark_all_served(pos_order_id: str) -> Union[str, None]:
    """
    Mark all items in POS Order as Served.
    Usually used when all food has been delivered.
    
    Args:
        pos_order_id (str): POS Order ID to mark items as served
        
    Returns:
        str: Success message if items were updated
        None: If no items needed update
        
    Raises:
        frappe.ValidationError: If error occurs during update
    """
    doc = frappe.get_doc("POS Order", pos_order_id)
    updated = False
    kot_id = None

    for item in doc.pos_order_items:
        if item.kot_status not in ("Served", "Cancelled"):
            item.kot_status = "Served"
            item.kot_last_update = frappe.utils.now_datetime()
            kot_id = item.kot_id
            updated = True

    if updated:
        doc.save()
        frappe.db.commit()

        if kot_id:
            kds_name = frappe.db.get_value(
                "Kitchen Display Order",
                {"kot_id": kot_id}
            )
            if kds_name:
                update_kds_status_from_kot(kds_name)

        return _("✅ All items marked as 'Served'.")

    return _("No items needed update.")