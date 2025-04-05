import frappe
import json
from frappe import _

@frappe.whitelist()
def resolve_variant(template, attributes):
    """
    Mencari item variant berdasarkan item template dan kombinasi atribut yang dipilih.
    """
    # Parse jika dari JSON string (dari JavaScript client)
    if isinstance(attributes, str):
        try:
            attributes = json.loads(attributes)
        except Exception:
            frappe.throw(_("Format atribut tidak valid (bukan JSON)."))

    if not attributes or not isinstance(attributes, list):
        frappe.throw(_("Atribut belum dipilih atau format tidak valid."))

    # Pastikan ini template yang punya varian
    if not frappe.db.get_value("Item", template, "has_variants"):
        frappe.throw(_("Item <b>{0}</b> bukan Template (tidak punya varian).").format(template))

    # Buat map dari input attributes
    attr_map = {
        a.get("attribute_name"): a.get("attribute_value")
        for a in attributes
        if a.get("attribute_name") and a.get("attribute_value")
    }

    if not attr_map:
        frappe.throw(_("Data atribut tidak lengkap atau kosong."))

    # Ambil semua varian dari template
    variants = frappe.get_all("Item", filters={"variant_of": template}, pluck="name")

    for variant in variants:
        match = True
        for attr_name, attr_value in attr_map.items():
            actual = frappe.db.get_value("Item Variant Attribute", {
                "parent": variant,
                "attribute": attr_name
            }, "attribute_value")

            if actual != attr_value:
                match = False
                break

        if match:
            item_doc = frappe.get_doc("Item", variant)

            # Ambil harga dari Price List atau fallback ke standard_rate
            price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
            rate = frappe.db.get_value("Item Price", {
                "item_code": variant,
                "price_list": price_list
            }, "price_list_rate") or item_doc.get("standard_rate") or 0

            return {
                "item_code": variant,
                "item_name": item_doc.item_name,
                "rate": rate
            }

    # Tidak ditemukan varian yang cocok
    frappe.throw(_("❌ Tidak ada varian yang cocok dengan kombinasi atribut tersebut."))
