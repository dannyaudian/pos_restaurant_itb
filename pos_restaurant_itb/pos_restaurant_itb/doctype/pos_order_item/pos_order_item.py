# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 08:45:57'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, flt

class POSOrderItem(Document):
    @handle_pos_errors()
    def validate(self):
        """Validate POS Order Item"""
        self.validate_item()
        self.validate_quantity()
        self.validate_rate()
        self.calculate_amount()
        self.validate_dynamic_attributes()
        
    def validate_item(self):
        """Validate item details"""
        if not self.item_code:
            frappe.throw(_("Item Code is required."))
            
        if not self.item_name:
            self.item_name = frappe.db.get_value("Item", self.item_code, "item_name")
            if not self.item_name:
                frappe.throw(_("Item name is required."))

    def validate_quantity(self):
        """Validate quantity"""
        self.qty = flt(self.qty)
        if self.qty <= 0:
            frappe.throw(_("Quantity must be greater than 0"))

    def validate_rate(self):
        """Get and validate item rate"""
        if not self.rate and self.item_code:
            price_list = (
                self.get_price_list() or 
                frappe.db.get_single_value("Selling Settings", "selling_price_list") or 
                "Standard Selling"
            )

            rate = frappe.db.get_value(
                "Item Price",
                {
                    "item_code": self.item_code,
                    "price_list": price_list
                },
                "price_list_rate"
            )

            if rate is None:
                rate = frappe.db.get_value("Item", self.item_code, "standard_rate") or 0
                frappe.msgprint(_(
                    "📌 Using fallback price from Item: {0}"
                ).format(rate))
            else:
                frappe.msgprint(_(
                    "📌 Price from {0}: {1}"
                ).format(price_list, rate))

            self.rate = flt(rate)

    def get_price_list(self):
        """Get price list from parent POS Order"""
        if self.parent:
            return frappe.db.get_value("POS Order", self.parent, "selling_price_list")
        return None

    def calculate_amount(self):
        """Calculate total amount"""
        self.rate = flt(self.rate)
        self.amount = flt(self.rate * self.qty)
        
        attribute_price = sum(
            flt(d.extra_price) 
            for d in self.dynamic_attributes if d.extra_price
        )
        
        if attribute_price:
            self.amount += (attribute_price * self.qty)
            frappe.msgprint(_(
                "💰 Total Amount = ({0} + {1}) × {2} = {3}"
            ).format(self.rate, attribute_price, self.qty, self.amount))
        else:
            frappe.msgprint(_(
                "💰 Total Amount = {0} × {1} = {2}"
            ).format(self.rate, self.qty, self.amount))

    def validate_dynamic_attributes(self):
        """Validate and resolve dynamic attributes"""
        if not self.dynamic_attributes:
            return
            
        attr_summary = []
        total_extra = 0
        
        for attr in self.dynamic_attributes:
            if attr.attribute_value:
                attr_summary.append(f"{attr.attribute_name}: {attr.attribute_value}")
                if attr.extra_price:
                    total_extra += flt(attr.extra_price)
                
        self.attribute_summary = ", ".join(attr_summary) if attr_summary else None
        
        if total_extra:
            frappe.msgprint(_(
                "💰 Extra price from attributes: {0}"
            ).format(total_extra))
        
        variant = self.resolve_item_variant(
            self.item_code,
            self.dynamic_attributes
        )
        
        if variant:
            self.resolved_dynamic_items = [{"item_code": variant}]
            frappe.msgprint(_("✅ Resolved variant: {0}").format(variant))

    def resolve_item_variant(self, template_item, dynamic_attributes):
        """
        Resolve item variant based on selected attributes
        Returns variant item code if found, None otherwise
        """
        attr_dict = {
            attr.attribute_name: attr.attribute_value 
            for attr in dynamic_attributes
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

    def on_update(self):
        """Handle status changes"""
        if self.has_value_changed("kot_status"):
            self.kot_last_update = now_datetime()
            
            if self.parent:
                parent = frappe.get_doc("POS Order", self.parent)
                parent.run_method("update_status")
            
        if self.has_value_changed("cancelled"):
            if self.cancelled and not self.cancellation_note:
                frappe.throw(_("Cancellation Note is required when cancelling an item"))