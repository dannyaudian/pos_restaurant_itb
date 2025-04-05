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

    # Parsing jika input JSON string
    if isinstance(attributes, str):
        attributes = json.loads(attributes)

    # Ubah dari dict flat (dari dialog) → array of {attribute_name, attribute_value}
    if isinstance(attributes, dict):
        attributes = [
            {"attribute_name": key, "attribute_value": val}
            for key, val in attributes.items()
            if key and val
        ]

    if not attributes:
        frappe.throw(_("Tidak ada atribut yang valid untuk disimpan."))

    # Ambil dokumen POS Order Item
    doc = frappe.get_doc("POS Order Item", parent_pos_order_item)

    # Bersihkan sebelumnya
    doc.set("dynamic_attributes", [])

    # Tambahkan semua atribut baru
    for attr in attributes:
        doc.append("dynamic_attributes", {
            "attribute_name": attr["attribute_name"],
            "attribute_value": attr["attribute_value"]
        })

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"{len(doc.dynamic_attributes)} atribut disimpan.",
        "dynamic_attributes": doc.dynamic_attributes
    }
