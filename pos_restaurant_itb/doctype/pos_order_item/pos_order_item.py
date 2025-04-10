import frappe
import json
from frappe import _
from frappe.model.document import Document
from pos_restaurant_itb.utils.kot_helpers import get_attribute_summary

class POSOrderItem(Document):
    def validate(self):
        """
        Validate POS Order Item data
        """
        # Calculate amount if not set
        if not self.amount:
            self.amount = self.qty * self.rate
            
        # Ensure item has proper variant attributes if it's a variant
        if self.template_item and not self.variant_attributes:
            frappe.throw(_("Variant attributes are required for variant items."))
    
    @property
    def attribute_summary(self):
        """
        Returns a human-readable summary of variant attributes
        """
        return get_attribute_summary(self.variant_attributes)
        
    @staticmethod
    def resolve_item_variant(template_item, dynamic_attributes):
        """
        Resolve the item variant based on the template and attributes
        
        Args:
            template_item: Template item code
            dynamic_attributes: List of attribute name-value pairs
            
        Returns:
            Item code of the variant, or None if no match found
        """
        if not template_item or not dynamic_attributes:
            return None
            
        # Convert dynamic_attributes to the format expected by Item Variant
        # Dynamic attributes format: [{"attribute_name": "Color", "attribute_value": "Red"}, ...]
        # Item Variant expects: {"Color": "Red", ...}
        
        if isinstance(dynamic_attributes, str):
            attrs_list = json.loads(dynamic_attributes)
        else:
            attrs_list = dynamic_attributes
            
        attrs_dict = {
            attr.get("attribute_name"): attr.get("attribute_value")
            for attr in attrs_list
            if attr.get("attribute_name") and attr.get("attribute_value")
        }
        
        if not attrs_dict:
            return None
            
        # Get all variants of the template
        variants = frappe.get_all(
            "Item",
            filters={"variant_of": template_item},
            fields=["name"]
        )
        
        # For each variant, check if it matches all the attributes
        for variant in variants:
            variant_attributes = frappe.get_all(
                "Item Variant Attribute",
                filters={"parent": variant.name},
                fields=["attribute", "attribute_value"]
            )
            
            # Create a dictionary of attribute:value for this variant
            variant_attrs_dict = {
                attr.attribute: attr.attribute_value
                for attr in variant_attributes
            }
            
            # Check if this variant matches all the requested attributes
            match = True
            for attr_name, attr_value in attrs_dict.items():
                if attr_name not in variant_attrs_dict or variant_attrs_dict[attr_name] != attr_value:
                    match = False
                    break
                    
            if match:
                return variant.name
                
        # If no matching variant found, return None
        return None