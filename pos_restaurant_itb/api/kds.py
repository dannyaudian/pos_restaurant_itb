# pos_restaurant_itb/api/kds.py

import frappe
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist()
def create_kds_from_kot(kot_id):
    """
    Create Kitchen Display Order (KDS) from a given KOT ID.
    Manual backup version, only used if automatic creation fails.
    """
    if not kot_id:
        frappe.throw(_("KOT ID wajib diisi."))

    # Cek apakah KDS sudah dibuat sebelumnya
    existing = frappe.db.exists("Kitchen Display Order", {"kot_id": kot_id})
    if existing:
        return existing

    kot = frappe.get_doc("KOT", kot_id)

    kds = frappe.new_doc("Kitchen Display Order")
    kds.kot_id = kot.name
    kds.table_number = kot.table
    kds.branch = kot.branch
    kds.status = "New"
    kds.last_updated = now_datetime()

    for item in kot.kot_items:
        kds.append("item_list", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "note": item.note,
            "kot_status": item.kot_status,
            "kot_last_update": item.kot_last_update,
            "attribute_summary": item.attribute_summary or "",
            "cancelled": item.cancelled,
            "cancellation_note": item.cancellation_note
        })

    kds.insert(ignore_permissions=True)
    frappe.db.commit()

    return kds.name
