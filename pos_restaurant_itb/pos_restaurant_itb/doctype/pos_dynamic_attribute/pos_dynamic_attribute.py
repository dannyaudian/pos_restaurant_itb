# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:04:02'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from typing import List, Dict, Optional, Any

from pos_restaurant_itb.utils.error_handlers import handle_pos_errors, ValidationError
from pos_restaurant_itb.utils.constants import ErrorMessages, CacheKeys, CacheExpiration

class POSDynamicAttribute(Document):
    """
    POS Dynamic Attribute Document Class
    
    Features:
    - Dynamic item attribute handling
    - Value validation with caching
    - Item variant mapping
    - Price adjustment management
    - Parent order synchronization
    
    Use Cases:
    1. Add attributes to POS Order Items (size, color, etc.)
    2. Map attributes to specific items
    3. Add extra charges for attributes
    4. Validate attribute values
    5. Update parent order pricing
    """
    
    @handle_pos_errors()
    def validate(self) -> None:
        """
        Validate POS Dynamic Attribute
        
        Validates:
        1. Attribute and value combination
        2. Mapped item if specified
        3. Extra price if set
        """
        self.validate_attribute()
        self.validate_mapped_item()
        self.validate_extra_price()
    
    def validate_attribute(self) -> None:
        """
        Validate attribute and its value
        
        Checks:
        - Attribute existence
        - Value validity
        - Cache management
        """
        if not self.attribute_name or not self.attribute_value:
            return

        # Check attribute existence with cache
        attr_cache_key = f"item_attribute:{self.attribute_name}"
        attr_exists = frappe.cache().get_value(attr_cache_key)
        
        if attr_exists is None:
            attr_exists = frappe.db.exists("Item Attribute", self.attribute_name)
            frappe.cache().set_value(
                attr_cache_key,
                attr_exists,
                expires_in_sec=CacheExpiration.MEDIUM
            )

        if not attr_exists:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INVALID_ATTRIBUTE,
                    attribute=self.attribute_name
                )
            )

        # Get valid values with cache
        values_cache_key = f"attribute_values:{self.attribute_name}"
        valid_values = frappe.cache().get_value(values_cache_key)
        
        if valid_values is None:
            valid_values = frappe.get_all(
                "Item Attribute Value",
                filters={"parent": self.attribute_name},
                pluck="attribute_value",
                cache=True
            )
            frappe.cache().set_value(
                values_cache_key,
                valid_values,
                expires_in_sec=CacheExpiration.MEDIUM
            )

        if self.attribute_value not in valid_values:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INVALID_ATTRIBUTE_VALUE,
                    value=self.attribute_value,
                    attribute=self.attribute_name,
                    valid_values=", ".join(valid_values)
                )
            )
            
        frappe.msgprint(
            _("✅ Validated: {0} = {1}").format(
                self.attribute_name,
                self.attribute_value
            )
        )

    def validate_mapped_item(self) -> None:
        """
        Validate mapped item if specified
        
        Checks:
        - Item existence
        - Item status
        - Attribute compatibility
        - Variant validation
        """
        if not self.item_code:
            return

        # Get item with cache
        item = frappe.get_cached_doc("Item", self.item_code)
        
        if not item:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.ITEM_NOT_FOUND,
                    item=self.item_code
                )
            )

        if not item.is_active:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INACTIVE_ITEM,
                    item=self.item_code
                )
            )

        if item.variant_of:
            template_attributes = frappe.get_all(
                "Item Variant Attribute",
                filters={
                    "parent": item.variant_of,
                    "attribute": self.attribute_name
                },
                pluck="attribute",
                cache=True
            )
            
            if not template_attributes:
                raise ValidationError(
                    ErrorMessages.format(
                        ErrorMessages.INVALID_ITEM_ATTRIBUTE,
                        item=self.item_code,
                        attribute=self.attribute_name
                    )
                )

        frappe.msgprint(
            _("✅ Mapped to Item: {0} - {1}").format(
                self.item_code,
                item.item_name
            )
        )

    def validate_extra_price(self) -> None:
        """
        Validate extra price
        
        Checks:
        - Price validity
        - Price limits
        - Notifications
        """
        self.extra_price = flt(self.extra_price)
        
        if self.extra_price < 0:
            raise ValidationError(ErrorMessages.NEGATIVE_PRICE)
            
        if self.extra_price > 0:
            # Get price limits from settings
            settings = frappe.get_cached_doc("POS Settings")
            max_extra_price = settings.get("max_attribute_price", 0)
            
            if max_extra_price and self.extra_price > max_extra_price:
                raise ValidationError(
                    ErrorMessages.format(
                        ErrorMessages.PRICE_LIMIT_EXCEEDED,
                        price=self.extra_price,
                        limit=max_extra_price
                    )
                )
            
            frappe.msgprint(
                _("💰 Extra price added: {0}").format(self.extra_price)
            )

    def before_save(self) -> None:
        """Update parent order item if needed"""
        if self.extra_price and self.parent_pos_order_item:
            try:
                # Get parent with cache
                parent_item = frappe.get_cached_doc(
                    "POS Order Item",
                    self.parent_pos_order_item
                )
                
                # Update amount
                parent_item.run_method("calculate_amount")
                parent_item.save(ignore_permissions=True)
                
                frappe.msgprint(
                    _("💰 Parent item amount updated with attribute price")
                )
                
            except Exception as e:
                frappe.log_error(
                    message=f"Failed to update parent item: {str(e)}",
                    title="Dynamic Attribute Error"
                )
                raise ValidationError(ErrorMessages.UPDATE_FAILED)