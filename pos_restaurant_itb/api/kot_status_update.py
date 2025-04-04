import frappe

def update_kds_status_from_kot(kds_name):
    """
    Cek semua item di Kitchen Display Order.
    Jika semua item Ready → update status jadi "Ready"
    Jika semua item Served → update status jadi "Served"
    """
    kds = frappe.get_doc("Kitchen Display Order", kds_name)
    statuses = [i.kot_status for i in kds.item_list]

    if all(s == "Served" for s in statuses):
        kds.status = "Served"
    elif all(s in ("Ready", "Served") for s in statuses):
        kds.status = "Ready"
    elif any(s == "Cooking" for s in statuses):
        kds.status = "In Progress"
    else:
        kds.status = "New"

    kds.save(ignore_permissions=True)
    frappe.db.commit()
