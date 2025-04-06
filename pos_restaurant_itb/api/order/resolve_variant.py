# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 15:10:45'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
import json
from typing import Dict, Union, List, Optional

from pos_restaurant_itb.utils.error_handlers import (
    handle_api_error,
    ValidationError,
    VariantError
)
from pos_restaurant_itb.utils.constants import (
    CacheKeys,
    ErrorMessages
)

@frappe.whitelist()
@handle_api_error
def resolve_variant(
    template: str,
    attributes: Union[str, List[Dict]],
    price_list: Optional[str] = None
) -> Dict:
    """
    Find item variant based on template item and selected attributes
    
    Args:
        template: Template item code
        attributes: List of selected attributes
            [
                {
                    "attribute": str,
                    "value": str
                }
            ]
        price_list: Specific price list to use (optional)
    
    Returns:
        Dict: Variant details
            {
                "item_code": str,
                "item_name": str,
                "rate": float,
                "currency": str,
                "tax_rate": float,
                "stock_qty": float,
                "uom": str,
                "attributes": [
                    {
                        "attribute": str,
                        "value": str,
                        "abbr": str
                    }
                ],
                "thumbnail": str
            }
            
    Raises:
        ValidationError: If inputs are invalid
        VariantError: If no matching variant found
    """
    # Validate and parse attributes
    attr_map = parse_attributes(attributes)
    
    # Validate template
    validate_template(template)
    
    # Check cache
    cache_key = f"{CacheKeys.VARIANT_MATCH}:{template}:{hash(frozenset(attr_map.items()))}"
    variant_data = frappe.cache().get_value(cache_key)
    
    if not variant_data:
        # Find matching variant
        variant = find_matching_variant(template, attr_map)
        if not variant:
            raise VariantError(
                "No variant matches the selected attributes",
                attr_map
            )
        
        # Get variant details
        variant_data = get_variant_details(
            variant,
            price_list
        )
        
        # Cache for 5 minutes
        frappe.cache().set_value(
            cache_key,
            variant_data,
            expires_in_sec=300
        )
        
        # Log resolution
        log_variant_resolution(
            template,
            variant,
            attr_map
        )
    
    return variant_data

def parse_attributes(attributes: Union[str, List[Dict]]) -> Dict[str, str]:
    """
    Parse and validate attribute input
    
    Args:
        attributes: Raw attributes input
        
    Returns:
        Dict[str, str]: Parsed attribute map
        
    Raises:
        ValidationError: If attributes are invalid
    """
    # Parse JSON if string
    if isinstance(attributes, str):
        try:
            attributes = json.loads(attributes)
        except json.JSONDecodeError:
            raise ValidationError(
                "Invalid attributes format (not valid JSON)",
                "Parse Error"
            )
    
    if not attributes or not isinstance(attributes, list):
        raise ValidationError(
            "Attributes must be a non-empty list",
            "Invalid Format"
        )
    
    # Create attribute map
    attr_map = {}
    for attr in attributes:
        name = attr.get("attribute")
        value = attr.get("value")
        
        if not name or not value:
            raise ValidationError(
                "Each attribute must have 'attribute' and 'value'",
                "Missing Data"
            )
        
        attr_map[name] = value
    
    return attr_map

def validate_template(template: str) -> None:
    """
    Validate template item
    
    Args:
        template: Template item code
        
    Raises:
        ValidationError: If template is invalid
    """
    if not template:
        raise ValidationError(
            "Template item code is required",
            "Missing Data"
        )
    
    has_variants = frappe.db.get_value(
        "Item",
        template,
        "has_variants"
    )
    
    if not has_variants:
        raise ValidationError(
            f"Item {template} is not a template item",
            "Invalid Template"
        )

def find_matching_variant(
    template: str,
    attr_map: Dict[str, str]
) -> Optional[str]:
    """
    Find variant matching attribute combination
    
    Args:
        template: Template item code
        attr_map: Attribute map to match
        
    Returns:
        Optional[str]: Matching variant code
    """
    variants = frappe.get_all(
        "Item",
        filters={"variant_of": template},
        pluck="name"
    )
    
    for variant in variants:
        if matches_attributes(variant, attr_map):
            return variant
    
    return None

def matches_attributes(
    variant: str,
    attr_map: Dict[str, str]
) -> bool:
    """
    Check if variant matches attribute combination
    
    Args:
        variant: Variant item code
        attr_map: Attribute map to match
        
    Returns:
        bool: True if matches
    """
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
            return False
    
    return True

def get_variant_details(
    variant: str,
    price_list: Optional[str] = None
) -> Dict:
    """
    Get comprehensive variant details
    
    Args:
        variant: Variant item code
        price_list: Price list to use
        
    Returns:
        Dict: Variant details
    """
    item = frappe.get_doc("Item", variant)
    
    # Get price
    if not price_list:
        price_list = frappe.db.get_single_value(
            "Selling Settings",
            "selling_price_list"
        ) or "Standard Selling"
    
    price_data = frappe.db.get_value(
        "Item Price",
        {
            "item_code": variant,
            "price_list": price_list
        },
        ["price_list_rate", "currency"],
        as_dict=True
    ) or {}
    
    # Get stock
    stock_qty = frappe.db.get_value(
        "Bin",
        {
            "item_code": variant,
            "warehouse": item.default_warehouse
        },
        "actual_qty"
    ) or 0
    
    # Get attributes
    attributes = []
    for attr in item.attributes:
        attributes.append({
            "attribute": attr.attribute,
            "value": attr.attribute_value,
            "abbr": get_attribute_abbr(
                attr.attribute,
                attr.attribute_value
            )
        })
    
    return {
        "item_code": variant,
        "item_name": item.item_name,
        "rate": price_data.get("price_list_rate") or item.standard_rate or 0,
        "currency": price_data.get("currency") or "INR",
        "tax_rate": get_tax_rate(item),
        "stock_qty": stock_qty,
        "uom": item.stock_uom,
        "attributes": attributes,
        "thumbnail": item.thumbnail or item.image
    }

def get_attribute_abbr(
    attribute: str,
    value: str
) -> str:
    """Get attribute value abbreviation"""
    return frappe.db.get_value(
        "Item Attribute Value",
        {
            "parent": attribute,
            "attribute_value": value
        },
        "abbr"
    ) or value[:3].upper()

def get_tax_rate(item) -> float:
    """Get item's tax rate"""
    tax_rate = 0
    if item.taxes:
        for tax in item.taxes:
            tax_rate += tax.tax_rate
    return tax_rate

def log_variant_resolution(
    template: str,
    variant: str,
    attr_map: Dict
) -> None:
    """
    Log variant resolution event
    
    Args:
        template: Template item code
        variant: Resolved variant code
        attr_map: Attribute combination used
    """
    frappe.logger().debug(
        f"Variant Resolution\n"
        f"Template: {template}\n"
        f"Variant: {variant}\n"
        f"Attributes: {attr_map}\n"
        f"User: {frappe.session.user}\n"
        f"Time: {frappe.utils.now()}"
    )