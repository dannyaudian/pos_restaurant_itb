import frappe
from frappe import _
from frappe.utils import now_datetime
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
            item.kot_last_update = now_datetime().isoformat()
            kot_id = item.kot_id
            updated = True
            break

    if not updated:
        frappe.throw(_("Item tidak ditemukan atau sudah dibatalkan."))

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Update status di Kitchen Display Order (jika ada)
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

@frappe.whitelist()
def create_kds_from_kot(kot_id):
    """
    Membuat Kitchen Display Order berdasarkan KOT ID.
    Mengisi otomatis semua informasi dan item_list dari KOT Item.
    """
    if not kot_id:
        frappe.throw(_("KOT ID wajib diisi."))

    # Cek apakah sudah ada KDS sebelumnya
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
