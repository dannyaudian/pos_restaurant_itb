# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 13:54:25'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, flt
from typing import Optional, Dict, List

from pos_restaurant_itb.utils.error_handlers import handle_pos_errors
from pos_restaurant_itb.utils.constants import KOTStatus

class POSOrderItem(Document):
    """
    POS Order Item Document Class
    
    Features:
    - Item validation and pricing
    - Dynamic attributes handling
    - Kitchen order status tracking
    - Amount calculations
    - Variant resolution
    """
    
    @handle_pos_errors()
    def validate(self) -> None:
        """Validate POS Order Item"""
        self.validate_item()
        self.validate_quantity()
        self.validate_rate()
        self.calculate_amount()
        self.validate_dynamic_attributes()
        
    def validate_item(self) -> None:
        """Validate item details"""
        if not self.item_code:
            frappe.throw(_("Item Code is required."))
            
        if not self.item_name:
            self.item_name = frappe.db.get_value(
                "Item", 
                self.item_code, 
                "item_name",
                cache=True
            )
            if not self.item_name:
                frappe.throw(_("Item name is required."))

    def validate_quantity(self) -> None:
        """Validate quantity"""
        self.qty = flt(self.qty)
        if self.qty <= 0:
            frappe.throw(_("Quantity must be greater than 0"))

    def validate_rate(self) -> None:
        """Get and validate item rate"""
        if not self.rate and self.item_code:
            price_list = (
                self.get_price_list() or 
                frappe.db.get_single_value(
                    "Selling Settings",
                    "selling_price_list",
                    cache=True
                ) or 
                "Standard Selling"
            )

            rate = frappe.db.get_value(
                "Item Price",
                {
                    "item_code": self.item_code,
                    "price_list": price_list
                },
                "price_list_rate",
                cache=True
            )

            if rate is None:
                rate = frappe.db.get_value(
                    "Item",
                    self.item_code,
                    "standard_rate",
                    cache=True
                ) or 0
                frappe.msgprint(
                    _("📌 Using fallback price from Item: {0}").format(rate)
                )
            else:
                frappe.msgprint(
                    _("📌 Price from {0}: {1}").format(price_list, rate)
                )

            self.rate = flt(rate)

    def get_price_list(self) -> Optional[str]:
        """Get price list from parent POS Order"""
        if self.parent:
            return frappe.db.get_value(
                "POS Order",
                self.parent,
                "selling_price_list",
                cache=True
            )
        return None

    def calculate_amount(self) -> None:
        """Calculate total amount including attributes"""
        self.rate = flt(self.rate)
        self.amount = flt(self.rate * self.qty)
        
        attribute_price = sum(
            flt(d.extra_price) 
            for d in self.dynamic_attributes if d.extra_price
        )
        
        if attribute_price:
            self.amount += (attribute_price * self.qty)
            frappe.msgprint(
                _("💰 Total Amount = ({0} + {1}) × {2} = {3}").format(
                    self.rate, attribute_price, self.qty, self.amount
                )
            )
        else:
            frappe.msgprint(
                _("💰 Total Amount = {0} × {1} = {2}").format(
                    self.rate, self.qty, self.amount
                )
            )

    def validate_dynamic_attributes(self) -> None:
        """Validate and resolve dynamic attributes"""
        if not self.dynamic_attributes:
            return
            
        attr_summary = []
        total_extra = 0
        
        for attr in self.dynamic_attributes:
            if attr.attribute_value:
                attr_summary.append(
                    f"{attr.attribute_name}: {attr.attribute_value}"
                )
                if attr.extra_price:
                    total_extra += flt(attr.extra_price)
                
        self.attribute_summary = ", ".join(attr_summary) if attr_summary else None
        
        if total_extra:
            frappe.msgprint(
                _("💰 Extra price from attributes: {0}").format(total_extra)
            )
        
        variant = self.resolve_item_variant(
            self.item_code,
            self.dynamic_attributes
        )
        
        if variant:
            self.resolved_dynamic_items = [{"item_code": variant}]
            frappe.msgprint(_("✅ Resolved variant: {0}").format(variant))

    def resolve_item_variant(
        self,
        template_item: str,
        dynamic_attributes: List[Dict]
    ) -> Optional[str]:
        """
        Resolve item variant based on selected attributes
        
        Args:
            template_item: Template item code
            dynamic_attributes: List of dynamic attributes
            
        Returns:
            Optional[str]: Variant item code if found
        """
        attr_dict = {
            attr.attribute_name: attr.attribute_value 
            for attr in dynamic_attributes
        }

        variants = frappe.get_all(
            "Item",
            filters={"variant_of": template_item},
            fields=["name"],
            cache=True
        )
        
        for variant in variants:
            match = True
            variant_attrs = frappe.get_all(
                "Item Variant Attribute",
                filters={"parent": variant.name},
                fields=["attribute", "attribute_value"],
                cache=True
            )
            
            for attr in variant_attrs:
                if attr_dict.get(attr.attribute) != attr.attribute_value:
                    match = False
                    break
                    
            if match:
                return variant.name
                
        return None

    def on_update(self) -> None:
        """Handle status changes"""
        if self.has_value_changed("kot_status"):
            self.kot_last_update = now_datetime()
            
            if self.kot_status == KOTStatus.CANCELLED:
                self.cancelled = 1
                if not self.cancellation_note:
                    self.cancellation_note = "Cancelled from kitchen"
            
            if self.parent:
                parent = frappe.get_doc("POS Order", self.parent)
                parent.run_method("update_status")
            
        if self.has_value_changed("cancelled"):
            if self.cancelled and not self.cancellation_note:
                frappe.throw(_("Cancellation Note is required when cancelling an item"))