# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class KOT(Document):
    def autoname(self):
        if not self.branch:
            frappe.throw(_("Branch is required to generate KOT ID."))

        # Ambil 3 karakter branch code
        branch_code = frappe.db.get_value("Branch", self.branch, "branch_code")
        if not branch_code or len(branch_code) < 3:
            frappe.throw(_("Branch must have a valid 3-character code."))

        branch_code = branch_code.upper().strip()
        count = frappe.db.count("KOT", {"branch": self.branch}) + 1
        self.kot_id = f"KOT-{branch_code}-{count:04d}"
        self.name = self.kot_id

    def validate(self):
        self.update_status_from_items()

    def update_status_from_items(self):
        """
        Update status KOT berdasarkan status KOT Item:
        - Semua Served → 'Served'
        - Semua Ready → 'Ready'
        - Ada Cooking → 'In Progress'
        - Selain itu → 'New'
        """
        statuses = [d.kot_status for d in self.kot_items if d.kot_status]

        if not statuses:
            self.status = "New"
            return

        if all(s == "Served" for s in statuses):
            self.status = "Served"
        elif all(s == "Ready" for s in statuses):
            self.status = "Ready"
        elif any(s == "Cooking" for s in statuses):
            self.status = "In Progress"
        else:
            self.status = "New"

    def on_submit(self):
        self.create_kds_entry()

    def create_kds_entry(self):
        """
        Membuat Kitchen Display Order berdasarkan isi KOT ini.
        """
        kds = frappe.new_doc("Kitchen Display Order")
        kds.kot_id = self.name
        kds.table_number = frappe.db.get_value("POS Table", self.table, "table_id")
        kds.branch = self.branch
        kds.status = self.status or "New"

        for item in self.kot_items:
            kds.append("item_list", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "note": item.note,
                "kot_status": item.kot_status,
                "kot_last_update": item.kot_last_update,
                "dynamic_attributes": item.dynamic_attributes,
                "order_id": self.pos_order,
                "branch": self.branch
            })

        kds.insert(ignore_permissions=True)


@frappe.whitelist()
def create_kot_from_pos_order(pos_order_id):
    """
    Membuat dokumen KOT berdasarkan POS Order (hanya untuk item yang belum dikirim ke dapur).
    """
    if not pos_order_id:
        frappe.throw(_("POS Order ID is required."))

    pos_order = frappe.get_doc("POS Order", pos_order_id)

    if not pos_order.pos_order_items:
        frappe.throw(_("POS Order tidak memiliki item."))

    kot = frappe.new_doc("KOT")
    kot.pos_order = pos_order.name
    kot.branch = pos_order.branch
    kot.table = pos_order.table
    kot.waiter = pos_order.modified_by  # atau gunakan field waiter jika ada
    kot.status = "New"

    found_item = False

    for item in pos_order.pos_order_items:
        if not item.sent_to_kitchen:
            kot.append("kot_items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "note": item.note,
                "kot_status": "Queued",
                "dynamic_attributes": item.dynamic_attributes,
                "kot_last_update": now()
            })
            item.sent_to_kitchen = 1
            found_item = True

    if not found_item:
        frappe.throw(_("Semua item sudah dikirim ke dapur."))

    kot.insert(ignore_permissions=True)
    kot.submit()

    # Simpan update flag item
    pos_order.save(ignore_permissions=True)

    return kot.name
