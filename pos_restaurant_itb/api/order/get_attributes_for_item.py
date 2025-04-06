# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:53:34'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import List, Dict, Optional

from pos_restaurant_itb.utils.error_handlers import (
    handle_api_error,
    ValidationError
)
from pos_restaurant_itb.utils.constants import CacheKeys

@frappe.whitelist()
@handle_api_error
def get_attributes_for_item(item_code: str) -> Dict:
    """
    Get list of attributes and their possible values for a template item
    
    Args:
        item_code: Item Code to get attributes for
        
    Returns:
        Dict: Item attributes with metadata
            {
                "item_code": str,
                "item_name": str,
                "has_variants": bool,
                "attributes": [
                    {
                        "attribute": str,
                        "label": str,
                        "values": List[str],
                        "default": str,
                        "required": bool,
                        "allow_custom": bool
                    },
                    ...
                ],
                "dynamic_attributes": [
                    {
                        "name": str,
                        "label": str,
                        "type": str,
                        "options": List[str],
                        "required": bool
                    },
                    ...
                ]
            }
            
    Raises:
        ValidationError: If item_code is empty or invalid
    """
    if not item_code:
        raise ValidationError(
            "Item Code is required",
            "Missing Data"
        )

    # Check cache first
    cache_key = f"{CacheKeys.ITEM_ATTRIBUTES}:{item_code}"
    attributes_data = frappe.cache().get_value(cache_key)
    
    if not attributes_data:
        # Get item document
        try:
            item = frappe.get_doc("Item", item_code)
        except frappe.DoesNotExistError:
            raise ValidationError(
                f"Item {item_code} not found",
                "Invalid Item"
            )
        
        attributes_data = {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "has_variants": item.has_variants,
            "attributes": [],
            "dynamic_attributes": []
        }
        
        if item.has_variants:
            # Get variant attributes
            for attr in item.attributes:
                attribute_doc = frappe.get_cached_doc(
                    "Item Attribute",
                    attr.attribute
                )
                
                # Get attribute values
                values = get_attribute_values(attribute_doc)
                
                attributes_data["attributes"].append({
                    "attribute": attr.attribute,
                    "label": attribute_doc.attribute_label or attr.attribute,
                    "values": values,
                    "default": attr.default_value or values[0] if values else None,
                    "required": attr.required,
                    "allow_custom": attribute_doc.allow_custom_values
                })
        
        # Get dynamic attributes if any
        if item.dynamic_attributes:
            attributes_data["dynamic_attributes"] = get_dynamic_attributes(item)
        
        # Cache for 1 hour
        frappe.cache().set_value(
            cache_key,
            attributes_data,
            expires_in_sec=3600
        )
    
    return attributes_data

def get_attribute_values(attribute_doc) -> List[str]:
    """
    Get possible values for an attribute
    
    Args:
        attribute_doc: Item Attribute document
        
    Returns:
        List[str]: List of possible values
    """
    # Get from cache
    cache_key = f"{CacheKeys.ATTRIBUTE_VALUES}:{attribute_doc.name}"
    values = frappe.cache().get_value(cache_key)
    
    if not values:
        values = frappe.get_all(
            "Item Attribute Value",
            filters={"parent": attribute_doc.name},
            fields=["attribute_value", "abbr"],
            order_by="idx"
        )
        
        # Format values
        values = [
            {
                "value": v.attribute_value,
                "abbr": v.abbr
            }
            for v in values
        ]
        
        # Cache for 1 hour
        frappe.cache().set_value(
            cache_key,
            values,
            expires_in_sec=3600
        )
    
    return values

def get_dynamic_attributes(item) -> List[Dict]:
    """
    Get dynamic attributes for an item
    
    Args:
        item: Item document
        
    Returns:
        List[Dict]: List of dynamic attributes
    """
    dynamic_attrs = []
    
    for attr in item.dynamic_attributes:
        attr_data = {
            "name": attr.attribute_name,
            "label": attr.attribute_label or attr.attribute_name,
            "type": attr.attribute_type,
            "required": attr.required,
            "options": []
        }
        
        # Get options if any
        if attr.attribute_type in ["Select", "MultiSelect"]:
            attr_data["options"] = [
                opt.strip()
                for opt in (attr.options or "").split("\n")
                if opt.strip()
            ]
        elif attr.attribute_type == "Numeric":
            attr_data.update({
                "min_value": attr.min_value,
                "max_value": attr.max_value,
                "increment": attr.increment or 1
            })
        
        dynamic_attrs.append(attr_data)
    
    return dynamic_attrs