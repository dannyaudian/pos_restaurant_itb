# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 08:18:16'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
import json
from frappe import _
from typing import Dict, Union, List

@frappe.whitelist()
def resolve_variant(template: str, attributes: Union[str, List[Dict]]) -> Dict:
    """
    Find item variant based on template item and selected attribute combination.
    
    Args:
        template (str): Template item code
        attributes (Union[str, List[Dict]]): List of selected attributes, can be JSON string
            [
                {
                    "attribute_name": "Size",
                    "attribute_value": "Large"
                },
                ...
            ]
    
    Returns:
        Dict: Variant details
            {
                "item_code": "ITEM-VAR-001",
                "item_name": "Item Variant 001",
                "rate": 100.00
            }
            
    Raises:
        frappe.ValidationError: If inputs are invalid or no matching variant found
    """
    # Parse if JSON string (from JavaScript client)
    if isinstance(attributes, str):
        try:
            attributes = json.loads(attributes)
        except Exception:
            frappe.throw(_("Invalid attribute format (not valid JSON)."))

    if not attributes or not isinstance(attributes, list):
        frappe.throw(_("Attributes are required and must be a list."))

    # Check if template has variants
    if not frappe.db.get_value("Item", template, "has_variants"):
        frappe.throw(_(
            "Item <b>{0}</b> is not a Template (has no variants)."
        ).format(template))

    # Create attribute map from input
    attr_map = {
        a.get("attribute_name"): a.get("attribute_value")
        for a in attributes
        if a.get("attribute_name") and a.get("attribute_value")
    }

    if not attr_map:
        frappe.throw(_("Attribute data is incomplete or empty."))

    # Get all variants of template
    variants = frappe.get_all(
        "Item",
        filters={"variant_of": template},
        pluck="name"
    )

    # Find matching variant
    for variant in variants:
        match = True
        for attr_name, attr_value in attr_map.items():
            actual = frappe.db.get_value(
                "Item Variant Attribute",
                {
                    "parent": variant,
                    "attribute": attr_name
                },
                "attribute_value"
            )

            if actual != attr_value:
                match = False
                break

        if match:
            item_doc = frappe.get_doc("Item", variant)

            # Get price from Price List or fallback to standard_rate
            price_list = frappe.db.get_single_value(
                "Selling Settings",
                "selling_price_list"
            ) or "Standard Selling"
            
            rate = frappe.db.get_value(
                "Item Price",
                {
                    "item_code": variant,
                    "price_list": price_list
                },
                "price_list_rate"
            ) or item_doc.get("standard_rate") or 0

            return {
                "item_code": variant,
                "item_name": item_doc.item_name,
                "rate": rate
            }

    # No matching variant found
    frappe.throw(_("❌ No variant matches the selected attribute combination."))