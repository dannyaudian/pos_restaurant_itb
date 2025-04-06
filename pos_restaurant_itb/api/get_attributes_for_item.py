# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 08:18:16'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import List, Dict

@frappe.whitelist()
def get_attributes_for_item(item_code: str) -> List[Dict]:
    """
    Get list of attributes and their possible values for a template item.
    
    Args:
        item_code (str): Item Code to get attributes for
        
    Returns:
        List[Dict]: List of attributes with their possible values
            [
                {
                    "attribute": "Size",
                    "values": ["Small", "Medium", "Large"]
                },
                ...
            ]
            
    Raises:
        frappe.ValidationError: If item_code is empty or invalid
    """
    if not item_code:
        frappe.throw(_("Item Code is required."))

    # Get item document
    item = frappe.get_doc("Item", item_code)
    if not item.has_variants:
        return []

    attributes = []
    for attr in item.attributes:
        # Get attribute values from Item Attribute doctype
        values = frappe.get_all(
            "Item Attribute Value",
            filters={"parent": attr.attribute},
            pluck="attribute_value"
        )
        
        attributes.append({
            "attribute": attr.attribute,
            "values": values
        })

    return attributes