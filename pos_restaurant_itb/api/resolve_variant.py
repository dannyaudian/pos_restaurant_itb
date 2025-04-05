import frappe
import json
from frappe import _

@frappe.whitelist()
def resolve_variant(template, attributes):
    """
    Mencari item variant berdasarkan template dan kombinasi atribut
    """
    # Jika dari client JS, bisa jadi string JSON
    if isinstance(attributes, str):
        attributes = json.loads(attributes)

    # Validasi: harus item template
    if not frappe.db.get_value("Item", template, "has_variants"):
        frappe.throw(_("Item <b>{0}</b> bukan Template (tidak punya varian).").format(template))

    if not attributes:
        frappe.throw(_("Atribut belum dipilih."))

    # Buat dict {attribute_name: attribute_value}
    attr_map = {
        a.get("attribute_name"): a.get("attribute_value")
        for a in attributes
        if a.get("attribute_name") and a.get("attribute_value")
    }

    if not attr_map:
        frappe.throw(_("Data atribut tidak lengkap."))

    # Ambil semua varian dari template
    variants = frappe.get_all("Item", filters={"variant_of": template}, pluck="name")

    for variant in variants:
        is_match = True
        for attr_name, attr_value in attr_map.items():
            actual = frappe.db.get_value("Item Variant Attribute", {
                "parent": variant,
                "attribute": attr_name
            }, "attribute_value")

            if actual != attr_value:
                is_match = False
                break

        if is_match:
            # Ambil rate dari Price List → fallback ke standard_rate jika tidak ada
            price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
            rate = frappe.db.get_value("Item Price", {
                "item_code": variant,
                "price_list": price_list
            }, "price_list_rate")

            if rate is None:
                rate = frappe.db.get_value("Item", variant, "standard_rate") or 0

            return {
                "item_code": variant,
                "item_name": frappe.db.get_value("Item", variant, "item_name"),
                "rate": rate
            }

    # Jika tidak ada yang cocok
    frappe.throw(_("❌ Tidak ada varian yang cocok dengan kombinasi atribut tersebut."))
