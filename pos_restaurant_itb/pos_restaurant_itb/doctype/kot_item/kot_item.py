# pos_restaurant_itb/pos_restaurant_itb/doctype/kot_item/kot_item.py

import frappe
import json
from frappe.model.document import Document
from frappe.utils import now_datetime

class KOTItem(Document):
    def validate(self):
        # Default status jika belum diisi
        if not self.kot_status:
            self.kot_status = "Queued"

        # Timestamp jika status diubah
        if self.kot_status and not self.kot_last_update:
            self.kot_last_update = now_datetime()

        # Isi waiter jika kosong (diambil dari parent KOT)
        if not self.waiter and self.parent:
            parent_doc = frappe.get_doc("KOT", self.parent)
            if parent_doc.waiter:
                self.waiter = parent_doc.waiter
            else:
                # fallback: pakai user id jika tidak ada employee
                self.waiter = frappe.session.user

    def get_attribute_summary(self):
        """Generate a readable summary from dynamic_attributes JSON"""
        if not hasattr(self, "_attribute_summary"):
            try:
                if not self.dynamic_attributes:
                    self._attribute_summary = ""
                    return self._attribute_summary
                    
                if isinstance(self.dynamic_attributes, str):
                    attrs = json.loads(self.dynamic_attributes or "[]")
                else:
                    attrs = self.dynamic_attributes or []
                    
                attr_pairs = [
                    f"{attr.get('attribute_name')}: {attr.get('attribute_value')}" 
                    for attr in attrs 
                    if attr.get('attribute_name') and attr.get('attribute_value')
                ]
                self._attribute_summary = ", ".join(attr_pairs)
            except Exception as e:
                frappe.log_error(f"Error in get_attribute_summary for KOTItem {self.name}: {str(e)}")
                self._attribute_summary = ""
        return self._attribute_summary

    @property
    def attribute_summary(self):
        """Property to access attribute summary"""
        return self.get_attribute_summary()