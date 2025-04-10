# File: pos_restaurant_itb/utils/kot_helpers.py

import frappe
import json

def get_attribute_summary(dynamic_attributes):
    """
    Converts dynamic_attributes in JSON format to a readable string
    This utility function can be used across multiple doctypes
    """
    try:
        if not dynamic_attributes:
            return ""
            
        if isinstance(dynamic_attributes, str):
            attrs = json.loads(dynamic_attributes or "[]")
        else:
            attrs = dynamic_attributes or []
            
        attr_pairs = [
            f"{attr.get('attribute_name')}: {attr.get('attribute_value')}" 
            for attr in attrs 
            if attr.get('attribute_name') and attr.get('attribute_value')
        ]
        return ", ".join(attr_pairs)
    except Exception as e:
        frappe.log_error(f"Error in get_attribute_summary: {str(e)}")
        return ""