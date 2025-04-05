import frappe
from frappe import _
import json

@frappe.whitelist()
def save_dynamic_attributes(parent_pos_order_item, attributes):
    """
    Simpan kombinasi atribut ke child table `dynamic_attributes` dari POS Order Item
    """

    if not parent_pos_order_item or not attributes:
        frappe.throw(_("Parameter tidak lengkap."))

    # Jika dikirim dari client JS, bisa jadi string → parsing
    if isinstance(attributes, str):
        attributes = json.loads(attributes)

    # Ambil dokumen POS Order Item
    doc = frappe.get_doc("POS Order Item", parent_pos_order_item)
    doc.flags.ignore_permissions = True  # 🔥 penting: bypass permission check

    # Bersihkan dulu
    doc.set("dynamic_attributes", [])

    # Tambahkan setiap atribut
    for attr_name, attr_value in attributes.items():
        if not attr_name or not attr_value:
            continue

        doc.append("dynamic_attributes", {
            "attribute_name": attr_name,
            "attribute_value": attr_value
        })

    doc.save()
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"{len(doc.dynamic_attributes)} atribut disimpan.",
        "dynamic_attributes": doc.dynamic_attributes
    }
