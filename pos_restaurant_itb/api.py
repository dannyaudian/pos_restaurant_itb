# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 09:31:46'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

"""
POS Restaurant ITB API
---------------------
Main API endpoints for POS Restaurant ITB.

Note: Most functions have been moved to their respective modules.
This file now serves as a central point for common API functions
and re-exports of frequently used functions.
"""

import frappe
from frappe import _
from frappe.utils import now
from pos_restaurant_itb.utils import (
    error_handlers,
    common,
    security
)

# Re-export commonly used functions
from pos_restaurant_itb.api.create_kot import create_kot_from_pos_order
from pos_restaurant_itb.api.kot_status_update import (
    update_kds_status_from_kot,
    bulk_update_kot_status
)
from pos_restaurant_itb.utils.common import (
    get_new_order_id,
    update_kot_item_status,
    get_branch_from_user
)

@frappe.whitelist()
@error_handlers.handle_pos_errors()
def create_kds_from_kot(kot_id: str) -> str:
    """
    Create Kitchen Display Order from KOT ID
    
    Args:
        kot_id (str): KOT ID to create KDS from
        
    Returns:
        str: Created KDS name
        
    Raises:
        ValidationError: If validation fails
    """
    if not kot_id:
        raise error_handlers.ValidationError(
            "KOT ID is required",
            "Validation Error"
        )

    # Check for existing KDS
    existing = frappe.db.exists(
        "Kitchen Display Order",
        {"kot_id": kot_id}
    )
    if existing:
        return existing

    try:
        kot = frappe.get_doc("KOT", kot_id)
        
        # Validate branch access
        security.validate_branch_operation(
            kot.branch,
            "create_kds",
            frappe.session.user
        )
        
        kds = frappe.new_doc("Kitchen Display Order")
        kds.update({
            "kot_id": kot.name,
            "table_number": kot.table,
            "branch": kot.branch,
            "status": "New",
            "last_updated": now()
        })

        for item in kot.kot_items:
            if item.cancelled:
                continue
                
            kds.append("item_list", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "kot_status": item.kot_status,
                "kot_last_update": item.kot_last_update,
                "attribute_summary": item.dynamic_attributes,
                "note": item.note,
                "cancelled": item.cancelled,
                "cancellation_note": item.cancellation_note
            })

        kds.insert(ignore_permissions=True)
        frappe.db.commit()

        return kds.name

    except Exception as e:
        frappe.log_error(
            message=f"""
            Failed to create KDS
            -------------------
            KOT: {kot_id}
            Error: {str(e)}
            Traceback: {frappe.get_traceback()}
            """,
            title="❌ KDS Creation Error"
        )
        raise

# Version and metadata
__version__ = "1.0.0"