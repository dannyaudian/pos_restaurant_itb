# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 08:45:57'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class POSDynamicAttribute(Document):
    @handle_pos_errors()
    def validate(self):
        """Validate POS Dynamic Attribute"""
        self.validate_attribute()
        self.validate_mapped_item()
        self.validate_extra_price()
    
    def validate_attribute(self):
        """Validate attribute and its value"""
        if not self.attribute_name or not self.attribute_value:
            return

        if not frappe.db.exists("Item Attribute", self.attribute_name):
            frappe.throw(_(
                "Attribute '{0}' does not exist"
            ).format(self.attribute_name))

        valid_values = frappe.get_all(
            "Item Attribute Value",
            filters={"parent": self.attribute_name},
            pluck="attribute_value"
        )

        if self.attribute_value not in valid_values:
            frappe.throw(_(
                "Value '{0}' is not valid for Attribute '{1}'. "
                "Valid values are: {2}"
            ).format(
                self.attribute_value,
                self.attribute_name,
                ", ".join(valid_values)
            ))
            
        frappe.msgprint(_(
            "✅ Validated: {0} = {1}"
        ).format(self.attribute_name, self.attribute_value))

    def validate_mapped_item(self):
        """Validate mapped item if specified"""
        if not self.item_code:
            return

        if not frappe.db.exists("Item", self.item_code):
            frappe.throw(_(
                "Item {0} does not exist"
            ).format(self.item_code))

        item = frappe.get_doc("Item", self.item_code)

        if not item.is_active:
            frappe.throw(_(
                "Item {0} is not active"
            ).format(self.item_code))

        if item.variant_of:
            template_attributes = frappe.get_all(
                "Item Variant Attribute",
                filters={
                    "parent": item.variant_of,
                    "attribute": self.attribute_name
                },
                pluck="attribute"
            )
            
            if not template_attributes:
                frappe.throw(_(
                    "Item {0} does not have attribute {1}"
                ).format(self.item_code, self.attribute_name))

        frappe.msgprint(_(
            "✅ Mapped to Item: {0} - {1}"
        ).format(self.item_code, item.item_name))

    def validate_extra_price(self):
        """Validate extra price"""
        self.extra_price = flt(self.extra_price)
        
        if self.extra_price < 0:
            frappe.throw(_("Extra price cannot be negative"))
            
        if self.extra_price > 0:
            frappe.msgprint(_(
                "💰 Extra price added: {0}"
            ).format(self.extra_price))

    def before_save(self):
        """Update parent order item if needed"""
        if self.extra_price and self.parent_pos_order_item:
            try:
                parent_item = frappe.get_doc(
                    "POS Order Item",
                    self.parent_pos_order_item
                )
                parent_item.run_method("calculate_amount")
                parent_item.save()
                
                frappe.msgprint(_(
                    "💰 Parent item amount updated with attribute price"
                ))
            except Exception as e:
                frappe.log_error(
                    message=f"Failed to update parent item: {str(e)}",
                    title="Dynamic Attribute Error"
                )