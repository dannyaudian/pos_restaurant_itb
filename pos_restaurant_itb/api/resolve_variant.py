# File: pos_restaurant_itb/api/resolve_variant.py

import frappe
import json
from frappe import _

@frappe.whitelist()
def resolve_variant(template, attributes):
    """
    Resolve an item variant based on template and attributes
    
    Args:
        template: Template item code
        attributes: JSON string of attributes in format [{"attribute_name": "Color", "attribute_value": "Red"}, ...]
        
    Returns:
        Item code of the matching variant, or None if no match found
    """
    from pos_restaurant_itb.pos_restaurant_itb.doctype.pos_order_item.pos_order_item import POSOrderItem
    
    try:
        if isinstance(attributes, str):
            attributes = json.loads(attributes)
            
        variant_item = POSOrderItem.resolve_item_variant(template, attributes)
        
        if variant_item:
            # Get additional details for the variant
            item_details = frappe.get_value(
                "Item", 
                variant_item, 
                ["item_name", "standard_rate", "stock_uom"], 
                as_dict=True
            )
            
            return {
                "status": "success",
                "item_code": variant_item,
                "item_name": item_details.item_name,
                "rate": item_details.standard_rate,
                "uom": item_details.stock_uom
            }
        else:
            return {
                "status": "error",
                "message": _("No matching variant found for the selected attributes.")
            }
    except Exception as e:
        frappe.log_error(f"Error resolving variant: {str(e)}")
        return {
            "status": "error",
            "message": _("Error resolving variant: {0}").format(str(e))
        }