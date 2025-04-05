import frappe
from frappe import _

@frappe.whitelist()
def get_attributes_for_item(item_code):
    """
    Mengembalikan daftar atribut & nilai-nilai pilihan dari item template
    """
    if not item_code:
        frappe.throw(_("Item tidak boleh kosong."))

    item = frappe.get_doc("Item", item_code)
    if not item.has_variants:
        return []

    attributes = []
    for attr in item.attributes:
        # ambil nilai attribute value dari Doctype Item Attribute
        values = frappe.get_all("Item Attribute Value", filters={"parent": attr.attribute}, pluck="attribute_value")
        attributes.append({
            "attribute": attr.attribute,
            "values": values
        })

    return attributes
