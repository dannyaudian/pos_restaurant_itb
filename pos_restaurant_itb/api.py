import frappe
from pos_restaurant_itb.api.kot_status_update import update_kds_status_from_kot


@frappe.whitelist()
def update_kot_item_status(order, item_code, status):
    """
    Update status item pada POS Order dan update status KDS jika semua item berubah.
    """
    doc = frappe.get_doc("POS Order", order)
    updated = False
    kot_id = None

    for item in doc.pos_order_items:
        if item.item_code == item_code:
            item.kot_status = status
            item.kot_last_update = frappe.utils.now_datetime()
            updated = True
            kot_id = getattr(item, "kot_id", None)
            break

    if not updated:
        frappe.throw("Item tidak ditemukan dalam order.")

    doc.save()
    frappe.db.commit()

    if kot_id:
        kds_name = frappe.db.get_value("Kitchen Display Order", {"kot_id": kot_id})
        if kds_name:
            update_kds_status_from_kot(kds_name)

    return {
        "status": "success",
        "message": f"{item_code} updated to {status}"
    }


@frappe.whitelist()
def get_new_order_id(branch):
    """
    Generate new POS Order ID berdasarkan branch code.
    Format: POS-{BRANCH_CODE}-{SEQ}
    """
