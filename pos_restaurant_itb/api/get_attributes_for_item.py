# File: pos_restaurant_itb/api/get_attributes_for_item.py

import frappe
from frappe import _

@frappe.whitelist()
def get_attributes_for_item(item_code):
    """
    Get all possible attributes for an item template
    
    Args:
        item_code: The template item code
        
    Returns:
        List of attributes with their possible values
    """
    if not item_code:
        return []
        
    # Check if this is a template item
    is_template = frappe.db.get_value("Item", item_code, "has_variants")
    if not is_template:
        return []
        
    # Get attributes for this template
    attributes = frappe.get_all(
        "Item Variant Attribute",
        filters={"parent": item_code},
        fields=["attribute", "attribute_values"]
    )
    
    result = []
    for attr in attributes:
        # Get attribute values (either from the field or from Attribute doctype)
        values = []
        if attr.attribute_values:
            values = attr.attribute_values.split("\n")
        else:
            # Get from Attribute doctype
            attr_values = frappe.get_all(
                "Item Attribute Value",
                filters={"parent": attr.attribute},
                fields=["attribute_value"],
                order_by="idx"
            )
            values = [av.attribute_value for av in attr_values]
            
        result.append({
            "attribute": attr.attribute,
            "values": values
        })
        
    return result