import frappe
from frappe import _

@frappe.whitelist()
def get_attributes_for_item(item_code):
    """
    Mengambil daftar atribut dari item template untuk ditampilkan ke user
    """
    if not item_code:
        frappe.throw(_("Item tidak boleh kosong."))

    item = frappe.get_doc("Item", item_code)
    if not item.has_variants:
        return []

    return frappe.get_all(
        "Item Variant Attribute",
        filters={"parent": item_code},
        fields=["attribute", "attribute_value"]
    )
