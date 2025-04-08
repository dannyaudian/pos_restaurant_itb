import frappe
from frappe import _
from pos_restaurant_itb.api.kot_status_update import update_kds_status_from_kot


@frappe.whitelist()
def send_to_kitchen(pos_order):
    """
    Alias backward compatibility:
    Tetap panggil create_kot_from_pos_order dari API resmi (bukan dari doctype langsung).
    """

    from pos_restaurant_itb.api.create_kot import create_kot_from_pos_order

    kot_name = create_kot_from_pos_order(pos_order_id=pos_order)

    if not kot_name:
        frappe.throw(_("❌ Tidak ada item tambahan yang perlu dikirim ke dapur."))

    kot_doc = frappe.get_doc("KOT", kot_name)

    # Render HTML template KOT
    return frappe.render_template("templates/kot_print.html", {"kot": kot_doc})


@frappe.whitelist()
def cancel_pos_order_item(item_name, reason=None):
    """
    Batalkan satu item di POS Order. Hanya bisa dilakukan oleh Outlet Manager.
    """

    if not frappe.has_role("Outlet Manager"):
        frappe.throw(_("Hanya Outlet Manager yang boleh membatalkan item."))

    doc = frappe.get_doc("POS Order Item", item_name)

    doc.cancelled = 1
    doc.cancellation_note = reason or "Cancelled manually"
    doc.rate = 0
    doc.amount = 0
    doc.save()

    # Rehitung total di parent
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
    """
    Tandai semua item dalam POS Order sebagai Served.
    Biasanya dipakai saat makanan sudah selesai dan diantar semua.
    """

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

        return f"✅ Semua item telah ditandai sebagai 'Served'."

    return "Tidak ada item yang perlu diubah."
