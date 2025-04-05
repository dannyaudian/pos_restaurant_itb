import frappe

def update_kds_status_from_kot(kds_name):
    """
    Update status Kitchen Display Order (KDS) berdasarkan status semua item KOT.
    - Semua "Served"            → status = "Served"
    - Semua "Ready" / "Served"  → status = "Ready"
    - Ada yang "Cooking"        → status = "In Progress"
    - Lainnya                   → status = "New"
    """
    if not kds_name:
        return

    kds = frappe.get_doc("Kitchen Display Order", kds_name)
    statuses = [item.kot_status for item in kds.item_list if not item.cancelled]

    if not statuses:
        kds.status = "New"
    elif all(s == "Served" for s in statuses):
        kds.status = "Served"
    elif all(s in ("Ready", "Served") for s in statuses):
        kds.status = "Ready"
    elif any(s == "Cooking" for s in statuses):
        kds.status = "In Progress"
    else:
        kds.status = "New"

    kds.save(ignore_permissions=True)
    frappe.db.commit()
