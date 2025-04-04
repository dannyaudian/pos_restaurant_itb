import frappe
from frappe import _

@frappe.whitelist()
def resolve_variant(template, attributes):
    """Mencari item variant berdasarkan template dan kombinasi atribut"""
    if not frappe.db.get_value("Item", template, "has_variants"):
        frappe.throw(_("Item '{0}' bukan Template (tidak punya varian).").format(template))

    if not attributes:
        frappe.throw(_("Atribut belum dipilih."))

    # Buat dict: {attribute_name: attribute_value}
    attr_map = {a.get('attribute_name'): a.get('attribute_value') for a in attributes if a.get('attribute_name') and a.get('attribute_value')}

    # Ambil semua variant dari template
    variants = frappe.get_all("Item", filters={"variant_of": template}, pluck="name")

    # Cek satu per satu variant
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
            item_name = frappe.db.get_value("Item", variant, "item_name")
            rate = frappe.db.get_value("Item Price", {
                "item_code": variant,
                "price_list": frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
            }, "price_list_rate") or 0

            return {
                "item_code": variant,
                "item_name": item_name,
                "rate": rate
            }

    # Tidak ditemukan
    frappe.throw(_("❌ Tidak ada item variant yang cocok dengan atribut yang dipilih."))
