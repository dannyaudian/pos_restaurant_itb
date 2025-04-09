import frappe

def update_kds_status_from_kot(kds_name):
    if not kds_name:
        return

    kds = frappe.get_doc("Kitchen Display Order", kds_name)
    statuses = [item.kot_status for item in kds.item_list if not item.cancelled]

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
    kds.save(ignore_permissions=True)
    frappe.db.commit()
        new_status = "New"

    kds.save(ignore_permissions=True)
    frappe.db.commit()

