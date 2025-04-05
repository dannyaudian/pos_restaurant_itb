import frappe
from frappe import _
import json

@frappe.whitelist()
def save_dynamic_attributes(pos_order_item, attributes):
    """
    Simpan kombinasi atribut ke child table `dynamic_attributes` dari POS Order Item
    """

    if not pos_order_item or not attributes:
        frappe.throw(_("Parameter tidak lengkap."))

    # Jika dikirim dari client JS, bisa jadi string → parsing
    if isinstance(attributes, str):
        attributes = json.loads(attributes)

    # Ambil dokumen POS Order Item
    doc = frappe.get_doc("POS Order Item", pos_order_item)

    # Bersihkan dulu
    doc.set("dynamic_attributes", [])

    # Tambahkan setiap atribut
    for attr in attributes:
        if not attr.get("attribute_name") or not attr.get("attribute_value"):
            continue

        doc.append("dynamic_attributes", {
            "attribute_name": attr["attribute_name"],
            "attribute_value": attr["attribute_value"]
        })

    doc.save()
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"{len(doc.dynamic_attributes)} atribut disimpan.",
        "dynamic_attributes": doc.dynamic_attributes
    }
