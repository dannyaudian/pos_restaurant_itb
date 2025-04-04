# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now

class KitchenDisplayOrder(Document):

    def before_insert(self):
        self.last_updated = now()
        self.status = "New"

    def on_update(self):
        self.last_updated = now()
