import frappe
from frappe.model.document import Document
from frappe import _

class KitchenStationSetup(Document):
    def autoname(self):
        if not self.branch:
            frappe.throw(_("Branch harus diisi untuk membuat ID Kitchen Station."))

        branch_code = frappe.get_value("Branch", self.branch, "branch_code")
        if not branch_code:
            frappe.throw(_("Branch Code tidak ditemukan untuk cabang {0}").format(self.branch))

        # Format autoname: KITCHEN-<BRANCHCODE>-####
        branch_code = branch_code.strip().upper()
        prefix = f"KITCHEN-{branch_code}"

        last = frappe.db.sql(
            """SELECT name FROM `tabKitchen Station Setup`
               WHERE name LIKE %s ORDER BY name DESC LIMIT 1""",
            (prefix + "-%",)
        )

        last_number = int(last[0][0].split("-")[-1]) if last else 0
        self.name = f"{prefix}-{str(last_number + 1).zfill(4)}"

    def validate(self):
        self.validate_printer_mappings()

    def validate_printer_mappings(self):
        if not self.printer_list:
            return

        for printer in self.printer_list:
            if printer.printer_type == "Thermal":
                if not printer.printer_ip or not self.is_valid_ip(printer.printer_ip):
                    frappe.throw(_(f"IP Address tidak valid untuk printer '{printer.printer_name}'."))

            if printer.printer_type == "Bluetooth":
                if not printer.bluetooth_identifier:
                    frappe.throw(_(f"Bluetooth Identifier wajib diisi untuk printer '{printer.printer_name}'."))

    def is_valid_ip(self, ip):
        import re
        pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if re.match(pattern, ip):
            parts = ip.split(".")
            return all(0 <= int(part) <= 255 for part in parts)
        return False
