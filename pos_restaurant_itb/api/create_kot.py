import frappe
from frappe import _
from frappe.utils import now
from pos_restaurant_itb.api.kitchen_station import create_kitchen_station_items_from_kot

@frappe.whitelist()
def create_kot_from_pos_order(pos_order_id: str) -> str:
    try:
        if not pos_order_id:
            frappe.throw(_("POS Order tidak boleh kosong."))

        frappe.logger().debug(f"📝 Memulai pembuatan KOT untuk POS Order: {pos_order_id}")

        try:
            pos_order = frappe.get_doc("POS Order", pos_order_id)
        except frappe.DoesNotExistError:
            frappe.throw(_("POS Order {0} tidak ditemukan.").format(pos_order_id))

        if pos_order.docstatus != 1:
            frappe.throw(_("POS Order harus disubmit sebelum dikirim ke dapur."))

        items_to_send = [
            item for item in pos_order.pos_order_items
            if not item.sent_to_kitchen and not item.cancelled
        ]

        if not items_to_send:
            frappe.throw(_("Semua item sudah dikirim ke dapur atau dibatalkan."))

        kot = frappe.new_doc("KOT")
        kot.update({
            "pos_order": pos_order.name,
            "table": pos_order.table,
            "branch": pos_order.branch,
            "kot_time": now(),
            "status": "New",
            "waiter": get_waiter_from_user(frappe.session.user)
        })

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
                "waiter": kot.waiter
            })

        try:
            kot.insert(ignore_permissions=True)
        except frappe.MandatoryError as e:
            frappe.throw(_("KOT creation failed due to missing mandatory fields."))

        for item in pos_order.pos_order_items:
            if item in items_to_send:
                item.sent_to_kitchen = 1
                item.kot_id = kot.name

        pos_order.save(ignore_permissions=True)
        frappe.db.commit()

        try:
            create_kitchen_station_items_from_kot(kot.name)
        except Exception as e:
            frappe.log_error(str(e), "❌ Warning: Kitchen Station")
            frappe.msgprint(_("KOT berhasil dibuat, namun gagal menambahkan item ke Kitchen Station."))

        frappe.logger().info(f"✅ KOT berhasil dibuat: {kot.name}")
        return kot.name

    except Exception as e:
        frappe.db.rollback()
        log_error(e, pos_order_id)
        raise

@frappe.whitelist()
def cancel_pos_order_item(item_name: str = None, reason: str = None) -> dict:
    if not item_name:
        frappe.throw(_("Item name is required."))

    if not any(role in ["System Manager", "Outlet Manager"] for role in frappe.get_roles(frappe.session.user)):
        frappe.throw(_("Hanya System Manager atau Outlet Manager yang boleh membatalkan item."))

    doc = frappe.get_doc("POS Order Item", item_name)
    doc.cancelled = 1
    doc.cancellation_note = reason or _("Cancelled manually")
    doc.rate = 0
    doc.amount = 0
    doc.save()

    parent = frappe.get_doc("POS Order", doc.parent)
    parent.total_amount = sum(i.amount for i in parent.pos_order_items if not i.cancelled)
    parent.save()
    frappe.db.commit()

    return {
        "status": "success",
        "message": _(f"Item {doc.item_code} dibatalkan.")
    }

@frappe.whitelist()
def mark_all_served(pos_order_id: str) -> str:
    doc = frappe.get_doc("POS Order", pos_order_id)
    updated = False
    kot_id = None

    for item in doc.pos_order_items:
        if item.kot_status not in ("Served", "Cancelled"):
            item.kot_status = "Served"
            item.kot_last_update = frappe.utils.now_datetime()
            kot_id = item.kot_id
            updated = True

    if updated:
        doc.save()
        frappe.db.commit()

        if kot_id:
            kds_name = frappe.db.get_value("Kitchen Display Order", {"kot_id": kot_id})
            if kds_name:
                from pos_restaurant_itb.api.kot_status_update import update_kds_status_from_kot
                update_kds_status_from_kot(kds_name)

        return "✅ Semua item telah ditandai sebagai 'Served'."

    return "Tidak ada item yang perlu diubah."

def get_waiter_from_user(user_id: str) -> str:
    emp = frappe.db.get_value("Employee", {"user_id": user_id}, "name", cache=True)
    return emp or user_id

def log_error(error: Exception, pos_order_id: str) -> None:
    error_msg = f"""
    Error during KOT creation
    --------------------------
    POS Order: {pos_order_id}
    User: {frappe.session.user}
    Time: {now()}
    Error: {str(error)}
    Traceback: {frappe.get_traceback()}
    """
    frappe.log_error(message=error_msg, title="❌ KOT Creation Error")
