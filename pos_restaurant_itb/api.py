import frappe
from restaurant_pos_core.utils.print_templates import render_kot_template, render_thermal_receipt

@frappe.whitelist()
def print_kot(name):
    doc = frappe.get_doc("POS Order", name)
    return render_kot_template(doc)

@frappe.whitelist()
def print_receipt(name):
    doc = frappe.get_doc("POS Order", name)
    return render_thermal_receipt(doc)

@frappe.whitelist()
def update_kot_item_status(order, item_code, status):
    doc = frappe.get_doc("POS Order", order)
    updated = False
    for item in doc.pos_order_items:
        if item.item_code == item_code:
            item.kot_status = status
            item.kot_last_update = frappe.utils.now_datetime()
            updated = True
            break
    if updated:
        doc.save()
        frappe.db.commit()
        from restaurant_pos_core.hooks.sla_log_hook import log_kitchen_sla
        log_kitchen_sla(item)
        from restaurant_pos_core.event.update_kot_status import update_pos_order_status
        update_pos_order_status(doc)
        doc.save()
        return {"status": "success", "message": f"{item_code} updated to {status}"}
    else:
        frappe.throw("Item tidak ditemukan dalam order.")
