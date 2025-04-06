# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 10:33:43'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe.model.document import Document
from frappe import _
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pos_restaurant_itb.utils.error_handlers import ValidationError
from pos_restaurant_itb.utils.constants import ErrorMessages

@dataclass
class PrinterConfig:
    """Printer configuration data class"""
    name: str
    type: str
    address: Optional[str] = None
    bluetooth_id: Optional[str] = None
    print_format: Optional[str] = None

class PrinterMappingPOSRestaurant(Document):
    """
    Printer Mapping for POS Restaurant
    
    Maps printers to specific branches and validates their configurations
    """

    def autoname(self) -> None:
        """
        Generate unique name for printer mapping
        Format: {BRANCH_CODE}-{PRINTER_TYPE}-{PRINTER_NAME}
        Example: JKT-R1-THERMAL-KITCHEN1
        """
        if not self.branch:
            raise ValidationError(ErrorMessages.BRANCH_REQUIRED)

        branch_code = frappe.db.get_value(
            "Branch",
            self.branch,
            "branch_code",
            cache=True
        )
        
        if not branch_code:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.MISSING_CONFIG,
                    config_name="Branch Code",
                    branch=self.branch
                )
            )

        # Format components
        branch_code = branch_code.strip().upper()
        printer_type = (self.printer_type or "Thermal").upper()
        printer_name = re.sub(r'\s+', '', self.printer_name or "Printer")

        self.name = f"{branch_code}-{printer_type}-{printer_name}"

    def validate(self) -> None:
        """
        Validate printer configuration
        
        Validates:
        - Required fields based on printer type
        - IP/Hostname format for Thermal printers
        - Bluetooth identifier format
        - Print format existence
        """
        self._validate_printer_config()
        self._validate_print_format()

    def _validate_printer_config(self) -> None:
        """Validate printer specific configuration"""
        config = PrinterConfig(
            name=self.printer_name,
            type=self.printer_type,
            address=self.printer_ip,
            bluetooth_id=self.bluetooth_identifier,
            print_format=self.print_format
        )

        if config.type == "Thermal":
            self._validate_thermal_printer(config)
        elif config.type == "Bluetooth":
            self._validate_bluetooth_printer(config)

    def _validate_thermal_printer(self, config: PrinterConfig) -> None:
        """
        Validate thermal printer configuration
        
        Args:
            config: PrinterConfig instance
        """
        if not config.address:
            raise ValidationError(
                message=ErrorMessages.PRINTER_IP_REQUIRED,
                title="Validation Error"
            )
            
        if not self._is_valid_ip(config.address):
            raise ValidationError(
                message=ErrorMessages.format(
                    ErrorMessages.INVALID_IP_FORMAT,
                    ip=config.address
                ),
                title="Validation Error"
            )

    def _validate_bluetooth_printer(self, config: PrinterConfig) -> None:
        """
        Validate bluetooth printer configuration
        
        Args:
            config: PrinterConfig instance
        """
        if not config.bluetooth_id:
            raise ValidationError(
                message=ErrorMessages.BLUETOOTH_ID_REQUIRED,
                title="Validation Error"
            )
            
        if not self._is_valid_bluetooth_id(config.bluetooth_id):
            raise ValidationError(
                message=ErrorMessages.format(
                    ErrorMessages.INVALID_BLUETOOTH_FORMAT,
                    id=config.bluetooth_id
                ),
                title="Validation Error"
            )

    def _validate_print_format(self) -> None:
        """Validate print format existence"""
        if self.print_format:
            exists = frappe.db.exists(
                "Print Format",
                self.print_format
            )
            if not exists:
                raise ValidationError(
                    message=ErrorMessages.format(
                        ErrorMessages.PRINT_FORMAT_NOT_FOUND,
                        format=self.print_format
                    ),
                    title="Validation Error"
                )

    def _is_valid_ip(self, ip: str) -> bool:
        """
        Validate IP address or hostname format
        
        Args:
            ip: IP address or hostname to validate
            
        Returns:
            bool: True if valid
        """
        if not ip:
            return False
            
        # IPv4 pattern
        ip_pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
        
        # Hostname pattern
        hostname_pattern = r"^[a-zA-Z0-9\-\.]+$"
        
        # Check if matches either pattern
        return bool(
            re.match(ip_pattern, ip) or 
            re.match(hostname_pattern, ip)
        )

    def _is_valid_bluetooth_id(self, identifier: str) -> bool:
        """
        Validate bluetooth identifier format
        
        Args:
            identifier: MAC address or device name
            
        Returns:
            bool: True if valid
        """
        if not identifier:
            return False
            
        # MAC address pattern
        mac_pattern = r"^([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})$"
        
        # Device name pattern
        name_pattern = r"^[\w\s\-]+$"
        
        # Check if matches either pattern
        return bool(
            re.match(mac_pattern, identifier) or 
            re.match(name_pattern, identifier)
        )

    def get_printer_config(self) -> Dict[str, Any]:
        """
        Get formatted printer configuration
        
        Returns:
            Dict: Printer configuration
        """
        return {
            "name": self.name,
            "printer_name": self.printer_name,
            "printer_type": self.printer_type,
            "address": self.printer_ip if self.printer_type == "Thermal" else self.bluetooth_identifier,
            "print_format": self.print_format,
            "branch": self.branch
        }
