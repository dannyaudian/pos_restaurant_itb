import frappe
from frappe import _
from pos_restaurant_itb.api.kot_status_update import update_kds_status_from_kot

@frappe.whitelist()
def update_kot_item_status(order, item_code, status):
    """
    Update status item pada POS Order dan update status KDS jika semua item berubah status.
    """
    if not order or not item_code or not status:
        frappe.throw(_("Parameter tidak lengkap."))

    doc = frappe.get_doc("POS Order", order)
    updated = False
    kot_id = None

    for item in doc.pos_order_items:
        if item.item_code == item_code and not item.cancelled:
            item.kot_status = status
            item.kot_last_update = frappe.utils.now_datetime()
            kot_id = item.kot_id
            updated = True
            break

    if not updated:
        frappe.throw(_("Item tidak ditemukan atau sudah dibatalkan."))

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Update KDS status jika ada kot_id
    if kot_id:
        kds_name = frappe.db.get_value("Kitchen Display Order", {"kot_id": kot_id})
        if kds_name:
            update_kds_status_from_kot(kds_name)

    return {
        "status": "success",
        "message": _(f"{item_code} berhasil diupdate ke status {status}")
    }


@frappe.whitelist()
def get_new_order_id(branch):
    """
    Generate new POS Order ID berdasarkan kode cabang.
    Format: POS-{BRANCHCODE}-{DDMMYY}-{SEQUENCE}
    """
    if not branch:
        frappe.throw(_("Cabang harus diisi."))

    branch_code = frappe.db.get_value("Branch", branch, "branch_code")
    if not branch_code:
        frappe.throw(_("Kode cabang tidak ditemukan untuk: {0}").format(branch))

    today = frappe.utils.now_datetime().strftime("%d%m%y")
    prefix = f"POS-{branch_code.upper()}-{today}"

    last = frappe.db.sql(
        """SELECT name FROM `tabPOS Order`
           WHERE name LIKE %s
           ORDER BY name DESC LIMIT 1""",
        (prefix + "%",)
    )

    last_number = int(last[0][0].split("-")[-1]) if last else 0
    new_order_id = f"{prefix}-{str(last_number + 1).zfill(4)}"

    return new_order_id
