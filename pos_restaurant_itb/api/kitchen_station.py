import frappe
import json
from frappe import _
from frappe.utils import now_datetime


def get_attribute_summary(dynamic_attributes_json):
    try:
        attrs = json.loads(dynamic_attributes_json or "[]")
        return ", ".join(f"{d.get('attribute_name')}: {d.get('attribute_value')}" for d in attrs)
    except Exception:
        return ""


@frappe.whitelist()
def create_kitchen_station_items_from_kot(kot_id):
    """
    Membaca semua item dari KOT dan membuat entri ke Kitchen Station berdasarkan qty.
    Setiap item dengan qty > 1 akan menghasilkan multiple line di Kitchen Station.
    Hindari duplikasi jika entri sudah pernah dibuat.
    """
    if not kot_id:
        frappe.throw(_("KOT ID tidak boleh kosong."))

    kot_doc = frappe.get_doc("KOT", kot_id)

    for item in kot_doc.kot_items:
        if item.cancelled:
            continue

        attribute_summary = item.attribute_summary or get_attribute_summary(item.dynamic_attributes)

        existing_count = frappe.db.count("Kitchen Station", {
            "kot_id": kot_doc.name,
            "item_code": item.item_code,
            "attribute_summary": attribute_summary,
            "note": item.note,
            "branch": kot_doc.branch,
            "table": kot_doc.table
        })

        remaining_qty = int(item.qty) - existing_count
        if remaining_qty <= 0:
            continue

        for _ in range(remaining_qty):
            doc = frappe.new_doc("Kitchen Station")
            doc.kot_id = kot_doc.name
            doc.table = kot_doc.table
            doc.branch = kot_doc.branch
            doc.item_code = item.item_code
            doc.item_name = item.item_name
            doc.attribute_summary = attribute_summary
            doc.note = item.note
            doc.kot_status = "Queued"
            doc.kot_last_update = now_datetime().isoformat()
            doc.cancelled = 0
            doc.cancellation_note = ""
            doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"status": "success", "message": f"Kitchen Station items created from {kot_id}"}
