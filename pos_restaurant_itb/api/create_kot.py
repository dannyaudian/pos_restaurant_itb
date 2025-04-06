import frappe
from frappe import _
from frappe.utils import now
from pos_restaurant_itb.api.kitchen_station import create_kitchen_station_items_from_kot

@frappe.whitelist()
def create_kot_from_pos_order(pos_order_id):
    if not pos_order_id:
        frappe.throw(_("POS Order tidak boleh kosong."))

    pos_order = frappe.get_doc("POS Order", pos_order_id)

    if pos_order.docstatus != 0:
        frappe.throw(_("POS Order sudah final dan tidak dapat dikirim ke dapur."))

    # Ambil item yang belum dikirim ke dapur
    items_to_send = [
        item for item in pos_order.pos_order_items
        if not item.sent_to_kitchen and not item.cancelled
    ]

    if not items_to_send:
        frappe.throw(_("Semua item dalam order ini sudah dikirim ke dapur atau dibatalkan."))

    kot = frappe.new_doc("KOT")
    kot.pos_order = pos_order.name
    kot.table = pos_order.table
    kot.branch = pos_order.branch
    kot.kot_time = now()
    kot.status = "New"
    kot.waiter = get_waiter_from_user(frappe.session.user)

    for item in items_to_send:
        kot.append("kot_items", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "note": item.note,
            "kot_status": "Queued",
            "kot_last_update": now(),
            "dynamic_attributes": frappe.as_json(item.dynamic_attributes or []),
            "order_id": pos_order.order_id,
            "branch": pos_order.branch,
            "waiter": kot.waiter  # as Data, bukan Link
        })

    try:
        kot.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "❌ Gagal insert KOT")
        frappe.throw(_("Terjadi kesalahan saat membuat KOT."))

    # Update POS Order item: sent_to_kitchen dan kot_id
    for item in pos_order.pos_order_items:
        if not item.sent_to_kitchen and not item.cancelled:
            item.sent_to_kitchen = 1
            item.kot_id = kot.name

    pos_order.save()
    frappe.db.commit()

    # 🔁 Tambahkan ke Kitchen Station secara otomatis
    try:
        create_kitchen_station_items_from_kot(kot.name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "❌ Gagal insert Kitchen Station")
        frappe.msgprint(_("KOT berhasil dibuat, namun gagal menambahkan item ke Kitchen Station."))

    return kot.name

def get_waiter_from_user(user_id):
    """
    Ambil nama Employee berdasarkan user_id.
    Jika tidak ditemukan, kembalikan user_id langsung (misal System Manager non-employee).
    """
    emp = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
    return emp or user_id
