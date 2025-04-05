import frappe
from frappe import _

@frappe.whitelist()
def get_available_tables(branch):
    """
    Mengembalikan daftar meja aktif yang belum digunakan oleh POS Order yang sedang berlangsung.
    Meja dianggap *sedang dipakai* jika ada POS Order dengan status:
    - Draft
    - In Progress
    - Ready for Billing
    """

    if not branch:
        frappe.throw(_("Cabang harus diisi."))

    # Ambil semua meja yang sedang digunakan di cabang ini
    used_tables = frappe.get_all(
        "POS Order",
        filters={
            "docstatus": ["<", 2],
            "status": ["in", ["Draft", "In Progress", "Ready for Billing"]],
            "branch": branch
        },
        pluck="table"
    )

    # Ambil semua meja aktif di cabang yang belum dipakai
    available_tables = frappe.get_all(
        "POS Table",
        filters={
            "branch": branch,
            "is_active": 1,
            "name": ["not in", used_tables or [""]]
        },
        fields=["name", "table_id"]
    )

    return available_tables
