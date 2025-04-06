import frappe
from frappe.model.document import Document
import re

class PrinterMappingPOSRestaurant(Document):
    def autoname(self):
        if not self.branch:
            frappe.throw("Branch wajib diisi sebelum menyimpan Printer Mapping.")

        branch_code = frappe.db.get_value("Branch", self.branch, "branch_code")
        if not branch_code:
            frappe.throw("Branch Code tidak ditemukan untuk cabang ini.")

        branch_code = branch_code.strip().upper()
        printer_type = self.printer_type or "Thermal"
        printer_name = (self.printer_name or "Printer").replace(" ", "")

        self.name = f"{branch_code}-{printer_type}-{printer_name}"

    def validate(self):
        if self.printer_type == "Thermal":
            if not self.printer_ip:
                frappe.throw("Untuk printer Thermal, IP / Address wajib diisi.")
            if not self.is_valid_ip(self.printer_ip):
                frappe.throw("Alamat IP tidak valid. Harap masukkan format IP (contoh: 192.168.1.100) atau hostname.")

        elif self.printer_type == "Bluetooth":
            if not self.bluetooth_identifier:
                frappe.throw("Untuk printer Bluetooth, Bluetooth Identifier wajib diisi.")
            if not self.is_valid_bluetooth_id(self.bluetooth_identifier):
                frappe.throw("Bluetooth Identifier tidak valid. Gunakan MAC Address (contoh: 00:1A:7D:DA:71:13) atau nama device.")

    def is_valid_ip(self, ip):
        # Validasi IPv4 atau hostname
        ip_pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
        hostname_pattern = r"^[a-zA-Z0-9\-\.]+$"
        return re.match(ip_pattern, ip) or re.match(hostname_pattern, ip)

    def is_valid_bluetooth_id(self, identifier):
        # Validasi MAC Address atau nama device
        mac_pattern = r"^([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})$"
        name_pattern = r"^[\w\s\-]+$"
        return re.match(mac_pattern, identifier) or re.match(name_pattern, identifier)
