# pos_restaurant_itb/api/kitchen_station.py
import frappe
import json
from frappe import _
from frappe.utils import now_datetime

def get_attribute_summary(dynamic_attributes_json):
    """
    Mengkonversi dynamic_attributes dalam format JSON ke string yang mudah dibaca
    """
    try:
        if not dynamic_attributes_json:
            return ""
            
        if isinstance(dynamic_attributes_json, str):
            attrs = json.loads(dynamic_attributes_json or "[]")
        else:
            attrs = dynamic_attributes_json or []
            
        attr_pairs = [
            f"{attr.get('attribute_name')}: {attr.get('attribute_value')}" 
            for attr in attrs 
            if attr.get('attribute_name') and attr.get('attribute_value')
        ]
        return ", ".join(attr_pairs)
    except Exception:
        return str(dynamic_attributes_json) if dynamic_attributes_json else ""

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

        # Tangani kasus ketika attribute_summary tidak ada
        try:
            # Pertama coba menggunakan property attribute_summary jika tersedia
            if hasattr(item, "attribute_summary") and callable(getattr(item, "attribute_summary", None)):
                attribute_summary = item.attribute_summary()
            elif hasattr(item, "attribute_summary") and item.attribute_summary:
                attribute_summary = item.attribute_summary
            else:
                # Fallback ke dynamic_attributes
                attribute_summary = get_attribute_summary(item.dynamic_attributes)
        except Exception:
            # Fallback jika terjadi error
            attribute_summary = get_attribute_summary(item.dynamic_attributes)

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