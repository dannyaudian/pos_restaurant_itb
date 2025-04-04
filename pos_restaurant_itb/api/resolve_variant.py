import frappe
from frappe import _

@frappe.whitelist()
def resolve_item_variant(template, attributes):
    if not frappe.db.get_value("Item", template, "has_variants"):
        return

    attr_map = {a['attribute_name']: a['attribute_value'] for a in attributes}

    variants = frappe.get_all("Item", filters={"variant_of": template}, pluck="name")

    for variant in variants:
        matched = True
        for attr_name, attr_value in attr_map.items():
            value = frappe.db.get_value("Item Variant Attribute", {
                "parent": variant,
                "attribute": attr_name
            }, "attribute_value")

            if value != attr_value:
                matched = False
                break

        if matched:
            return variant

    frappe.throw(_("Tidak ada item variant yang cocok dengan atribut yang dipilih."))