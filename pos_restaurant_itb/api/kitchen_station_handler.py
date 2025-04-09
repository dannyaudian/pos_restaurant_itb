# pos_restaurant_itb/api/kitchen_station_handler.py
import frappe
from frappe import _
from frappe.utils import now_datetime
# Import fungsi get_attribute_summary di awal file
from pos_restaurant_itb.api.kitchen_station import get_attribute_summary

@frappe.whitelist()
def get_kitchen_items_by_station(branch, item_group):
    """
    Ambil semua item dari KOT yang sesuai dengan branch dan item_group,
    hanya status: Queued atau Cooking (belum Ready/Cancelled),
    disusun berdasarkan urutan waktu.
    """
    if not branch or not item_group:
        frappe.throw(_("Branch dan Item Group wajib diisi."))

    kot_items = frappe.db.sql("""
        SELECT 
            ki.name AS kot_item_id,
            k.name AS kot_id,
            k.table,
            k.branch,
            k.pos_order,
            ki.item_code,
            ki.item_name,
            ki.dynamic_attributes,  -- Ambil dynamic_attributes juga
            ki.attribute_summary,
            ki.note,
            ki.kot_status,
            ki.kot_last_update,
            ki.cancelled,
            ki.cancellation_note,
            ki.waiter,
            ki.order_id
        FROM `tabKOT Item` ki
        INNER JOIN `tabKOT` k ON ki.parent = k.name
        INNER JOIN `tabItem` i ON ki.item_code = i.name
        WHERE k.branch = %s
        AND i.item_group = %s
        AND ki.kot_status IN ('Queued', 'Cooking')
        AND ki.cancelled = 0
        ORDER BY k.kot_time ASC, ki.creation ASC
    """, (branch, item_group), as_dict=True)

    # Proses attribute_summary untuk hasil dari SQL query
    for item in kot_items:
        # Lebih baik mengecek jika ada dynamic_attributes dulu 
        # untuk mengurangi overhead jika attribute_summary sudah ada
        if not item.get("attribute_summary") and item.get("dynamic_attributes"):
            try:
                item["attribute_summary"] = get_attribute_summary(item["dynamic_attributes"])
            except Exception as e:
                frappe.log_error(f"Error generating attribute_summary: {str(e)}")
                item["attribute_summary"] = ""
        elif not item.get("attribute_summary"):
            # Pastikan attribute_summary selalu ada, meski kosong
            item["attribute_summary"] = ""

    return kot_items

@frappe.whitelist()
def update_kitchen_item_status(kot_item_id, new_status):
    """
    Ubah status KOT Item menjadi Cooking atau Ready.
    Update waktu terakhir, dan trigger update ke KDS.
    """
    if new_status not in ["Cooking", "Ready"]:
        frappe.throw(_("Status tidak valid. Pilih antara 'Cooking' atau 'Ready'."))

    kot_item = frappe.get_doc("KOT Item", kot_item_id)
    kot_item.kot_status = new_status
    kot_item.kot_last_update = now_datetime()
    kot_item.save(ignore_permissions=True)

    # Update KDS jika ada
    kot_id = kot_item.parent
    kds_name = frappe.db.get_value("Kitchen Display Order", {"kot_id": kot_id})
    if kds_name:
        from pos_restaurant_itb.api.kot_status_update import update_kds_status_from_kot
        update_kds_status_from_kot(kds_name)

    frappe.db.commit()
    return {
        "status": "success",
        "message": f"Item {kot_item.item_code} diubah menjadi {new_status}"
    }

@frappe.whitelist()
def cancel_kitchen_item(kot_item_id, reason):
    """
    Cancel item dari dapur. Set cancelled flag, isi alasan, dan update waktu.
    """
    if not reason or len(reason.strip()) < 3:
        frappe.throw(_("Alasan pembatalan harus diisi dengan benar."))

    kot_item = frappe.get_doc("KOT Item", kot_item_id)

    if kot_item.kot_status == "Ready":
        frappe.throw(_("Item yang sudah Ready tidak dapat dibatalkan."))

    kot_item.kot_status = "Cancelled"
    kot_item.cancelled = 1
    kot_item.cancellation_note = reason.strip()
    kot_item.kot_last_update = now_datetime()
    kot_item.save(ignore_permissions=True)

    # Update KDS jika ada
    kot_id = kot_item.parent
    kds_name = frappe.db.get_value("Kitchen Display Order", {"kot_id": kot_id})
    if kds_name:
        from pos_restaurant_itb.api.kot_status_update import update_kds_status_from_kot
        update_kds_status_from_kot(kds_name)

    frappe.db.commit()
    return {
        "status": "success",
        "message": f"Item {kot_item.item_code} telah dibatalkan."
    }