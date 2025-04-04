import frappe
from pos_restaurant_itb.utils.print_templates import render_kot_template, render_thermal_receipt
from pos_restaurant_itb.api.kot_status_update import update_kds_status_from_kot  

@frappe.whitelist()
def print_kot(name):
    """Render KOT Print Template"""
    doc = frappe.get_doc("POS Order", name)
    return render_kot_template(doc)

@frappe.whitelist()
def print_receipt(name):
    """Render Thermal Receipt Template"""
    doc = frappe.get_doc("POS Order", name)
    return render_thermal_receipt(doc)

@frappe.whitelist()
def update_kot_item_status(order, item_code, status):
    doc = frappe.get_doc("POS Order", order)
    updated = False
    kot_id = None

    for item in doc.pos_order_items:
        if item.item_code == item_code:
            item.kot_status = status
            item.kot_last_update = frappe.utils.now_datetime()
            updated = True
            kot_id = getattr(item, "kot_id", None) 
            break

    if updated:
        doc.save()
        frappe.db.commit()

        if kot_id:
            kds_name = frappe.db.get_value("Kitchen Display Order", {"kot_id": kot_id})
            if kds_name:
                update_kds_status_from_kot(kds_name)

        return {"status": "success", "message": f"{item_code} updated to {status}"}
    else:
        frappe.throw("Item tidak ditemukan dalam order.")

@frappe.whitelist()
def get_new_order_id(branch):
    if not branch:
        frappe.throw("Branch is required")

    branch_code = frappe.db.get_value("Branch", branch, "branch_code")
    if not branch_code:
        frappe.throw("Branch code not found")

    branch_code = branch_code.strip().upper()
    count = frappe.db.count("POS Order", {"branch": branch}) + 1
    return f"POS-{branch_code}-{count:05d}"
