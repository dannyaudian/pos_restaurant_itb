import frappe
from frappe import _
from frappe.utils import now, cstr
from pos_restaurant_itb.api.kitchen_station import create_kitchen_station_items_from_kot
from pos_restaurant_itb.api.kot_status_update import update_kds_status_from_kot

@frappe.whitelist()
def send_to_kitchen(pos_order):
    from pos_restaurant_itb.api.create_kot import create_kot_from_pos_order

    kot_name = create_kot_from_pos_order(pos_order_id=pos_order)

    if not kot_name:
        frappe.throw(_("❌ Tidak ada item tambahan yang perlu dikirim ke dapur."))

    kot_doc = frappe.get_doc("KOT", kot_name)

    return frappe.render_template("templates/kot_print.html", {"kot": kot_doc})

@frappe.whitelist()
def cancel_pos_order_item(item_name=None, reason=None):
    if not item_name:
        frappe.throw(_("Item name is required."))

    if not frappe.has_role("Outlet Manager"):
        frappe.throw(_("Hanya Outlet Manager yang boleh membatalkan item."))

    doc = frappe.get_doc("POS Order Item", item_name)
    doc.cancelled = 1
    doc.cancellation_note = reason or "Cancelled manually"
    doc.rate = 0
    doc.amount = 0
    doc.save()

    parent = frappe.get_doc("POS Order", doc.parent)
    total = sum(i.amount for i in parent.pos_order_items if not i.cancelled)
    parent.total_amount = total
    parent.save()

    frappe.db.commit()

    return {
        "status": "success",
        "message": _(f"Item {doc.item_code} dibatalkan.")
    }

@frappe.whitelist()
def mark_all_served(pos_order_id):
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
                update_kds_status_from_kot(kds_name)

        return "✅ Semua item telah ditandai sebagai 'Served'."

    return "Tidak ada item yang perlu diubah."

@frappe.whitelist()
def create_kot_from_pos_order(pos_order_id):
    try:
        if not pos_order_id:
            frappe.throw(_("POS Order tidak boleh kosong."))

        frappe.logger().debug(f"📝 Memulai pembuatan KOT untuk POS Order: {pos_order_id}")

        try:
            pos_order = frappe.get_doc("POS Order", pos_order_id)
        except frappe.DoesNotExistError:
            frappe.throw(_("POS Order {0} tidak ditemukan.").format(pos_order_id))

        if pos_order.docstatus == 0:
            frappe.throw(_("POS Order belum disave. Silakan save terlebih dahulu sebelum mengirim item ke dapur."))

        validate_pos_order(pos_order)

        items_to_send = get_items_to_send(pos_order)
        if not items_to_send:
            frappe.throw(_("Semua item dalam order ini sudah dikirim ke dapur atau dibatalkan."))

        frappe.logger().debug(f"📝 Item yang akan dikirim: {items_to_send}")

        kot = create_kot_document(pos_order, items_to_send)
        update_pos_order_items(pos_order, kot.name, items_to_send)
        frappe.db.commit()
        process_kitchen_station(kot.name)

        frappe.logger().info(f"✅ KOT berhasil dibuat: {kot.name}")
        return kot.name

    except Exception as e:
        frappe.db.rollback()
        log_error(e, pos_order_id)
        raise

def validate_pos_order(pos_order):
    if pos_order.docstatus != 1:
        frappe.throw(_("POS Order harus disubmit untuk dikirim ke dapur."))

def get_items_to_send(pos_order):
    return [
        item for item in pos_order.pos_order_items
        if not item.sent_to_kitchen and not item.cancelled
    ]

def create_kot_document(pos_order, items_to_send):
    try:
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

        kot.insert(ignore_permissions=True)
        frappe.logger().info(f"✅ KOT document created: {kot.name}")
        return kot

    except Exception as e:
        frappe.log_error(
            message=f"Gagal membuat KOT untuk POS Order {pos_order.name}: {str(e)}",
            title="❌ Gagal Create KOT"
        )
        raise

def update_pos_order_items(pos_order, kot_name, items_to_send):
    try:
        for item in pos_order.pos_order_items:
            if item in items_to_send:
                item.sent_to_kitchen = 1
                item.kot_id = kot_name

        pos_order.save(ignore_permissions=True)
        frappe.logger().info(f"✅ POS Order items updated for KOT: {kot_name}")

    except Exception as e:
        frappe.log_error(
            message=f"Gagal update POS Order {pos_order.name}: {str(e)}",
            title="❌ Gagal Update POS Order"
        )
        raise

def process_kitchen_station(kot_name):
    try:
        create_kitchen_station_items_from_kot(kot_name)
    except Exception as e:
        frappe.log_error(
            message=f"Gagal membuat Kitchen Station Items untuk KOT {kot_name}: {str(e)}",
            title="❌ Warning: Kitchen Station"
        )
        frappe.msgprint(
            _("KOT berhasil dibuat, namun gagal menambahkan item ke Kitchen Station.")
        )

def get_waiter_from_user(user_id):
    emp = frappe.db.get_value("Employee", {"user_id": user_id}, "name", cache=True)
    return emp or user_id

def log_error(error, pos_order_id):
    error_msg = f"""
    Error saat membuat KOT
    ----------------------
    POS Order: {pos_order_id}
    User: {frappe.session.user}
    Time: {now()}
    Error: {str(error)}
    Traceback: {frappe.get_traceback()}
    """

    frappe.log_error(
        message=error_msg,
        title="❌ KOT Creation Error"
    )