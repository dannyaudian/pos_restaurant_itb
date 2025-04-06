# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 08:48:49'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _

def validate_item_attributes(item_code, attributes):
    """
    Validate item attributes
    
    Args:
        item_code (str): Item code
        attributes (list): List of attribute dicts with attribute_name and attribute_value
        
    Returns:
        bool: True if valid
    """
    if not attributes:
        return True
        
    item = frappe.get_doc("Item", item_code)
    
    # If not template, no validation needed
    if not item.has_variants:
        return True
        
    # Get valid attributes for item
    valid_attributes = frappe.get_all(
        "Item Variant Attribute",
        filters={"parent": item_code},
        fields=["attribute"]
    )
    
    valid_attr_names = [d.attribute for d in valid_attributes]
    
    # Validate each attribute
    for attr in attributes:
        if attr.attribute_name not in valid_attr_names:
            frappe.throw(_(
                "Attribute {0} is not valid for item {1}"
            ).format(attr.attribute_name, item_code))
            
        # Validate attribute value
        valid_values = frappe.get_all(
            "Item Attribute Value",
            filters={"parent": attr.attribute_name},
            pluck="attribute_value"
        )
        
        if attr.attribute_value not in valid_values:
            frappe.throw(_(
                "Value {0} is not valid for attribute {1}"
            ).format(attr.attribute_value, attr.attribute_name))
            
    return True

def get_variant_attributes(item_code):
    """
    Get variant attributes for item
    
    Args:
        item_code (str): Item code
        
    Returns:
        list: List of attribute dicts
    """
    if not frappe.db.get_value("Item", item_code, "has_variants"):
        return []
        
    attributes = frappe.get_all(
        "Item Variant Attribute",
        filters={"parent": item_code},
        fields=["attribute", "attribute_value"]
    )
    
    for attr in attributes:
        attr.values = frappe.get_all(
            "Item Attribute Value",
            filters={"parent": attr.attribute},
            pluck="attribute_value"
        )
        
    return attributes

def find_variant(template_item, attributes):
    """
    Find matching variant for given attributes
    
    Args:
        template_item (str): Template item code
        attributes (list): List of attribute dicts
        
    Returns:
        str: Variant item code if found, else None
    """
    if not template_item or not attributes:
        return None
        
    attr_dict = {
        attr.attribute_name: attr.attribute_value 
        for attr in attributes
    }
    
    variants = frappe.get_all(
        "Item",
        filters={"variant_of": template_item},
        fields=["name"]
    )
    
    for variant in variants:
        match = True
        variant_attrs = frappe.get_all(
            "Item Variant Attribute",
            filters={"parent": variant.name},
            fields=["attribute", "attribute_value"]
        )
        
        for attr in variant_attrs:
            if attr_dict.get(attr.attribute) != attr.attribute_value:
                match = False
                break
                
        if match:
            return variant.name
            
    return None