# pos_restaurant_itb/pos_restaurant_itb/doctype/kot_item/kot_item.py

import frappe
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
