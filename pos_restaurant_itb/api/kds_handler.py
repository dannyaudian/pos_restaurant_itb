import frappe
from frappe import _
from frappe.utils import now_datetime

@frappe.whitelist()
def create_kds_from_kot(kot_id):
    """
    Buat Kitchen Display Order (KDS) otomatis dari KOT.
    Akan mengambil semua item dari KOT dan copy ke KDS.
    """
    if not kot_id:
        frappe.throw(_("KOT ID wajib diisi."))

    kot = frappe.get_doc("KOT", kot_id)

    # Cegah duplikasi
    if frappe.db.exists("Kitchen Display Order", {"kot_id": kot.name}):
        return {
            "status": "warning",
            "message": _(f"KDS untuk {kot.name} sudah ada."),
            "kds_name": frappe.db.get_value("Kitchen Display Order", {"kot_id": kot.name})
        }

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

    return {
        "status": "success",
        "message": _(f"✅ KDS berhasil dibuat dari KOT {kot.name}"),
        "kds_name": kds.name
    }
