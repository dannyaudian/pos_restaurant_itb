import frappe
from frappe import _

@frappe.whitelist()
def resolve_variant(template, attributes):
    """
    Mencari item variant berdasarkan template dan kombinasi atribut
    """
    if not frappe.db.get_value("Item", template, "has_variants"):
        frappe.throw(_("Item <b>{0}</b> bukan Template (tidak punya varian).").format(template))

    if not attributes:
        frappe.throw(_("Atribut belum dipilih."))

    # Buat mapping atribut → value
    attr_map = {
        attr.get("attribute_name"): attr.get("attribute_value")
        for attr in attributes
        if attr.get("attribute_name") and attr.get("attribute_value")
    }

    if not attr_map:
        frappe.throw(_("Data atribut tidak lengkap."))

    # Ambil semua item varian dari template
    variants = frappe.get_all("Item", filters={"variant_of": template}, pluck="name")

    for variant in variants:
        matched = True

        for attr_name, attr_value in attr_map.items():
            actual_value = frappe.db.get_value("Item Variant Attribute", {
                "parent": variant,
                "attribute": attr_name
            }, "attribute_value")

            if actual_value != attr_value:
                matched = False
                break

        if matched:
            item_doc = frappe.get_doc("Item", variant)
            price = frappe.db.get_value("Item Price", {
                "item_code": variant,
                "price_list": frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
            }, "price_list_rate") or 0

            return {
                "item_code": item_doc.name,
                "item_name": item_doc.item_name,
                "rate": price
            }

    # Tidak ditemukan yang cocok
    frappe.throw(_("❌ Tidak ada varian yang cocok dengan kombinasi atribut tersebut."))
