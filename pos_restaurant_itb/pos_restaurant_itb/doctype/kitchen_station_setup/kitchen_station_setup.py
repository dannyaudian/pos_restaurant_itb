# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:16:09'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import re
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime_str
from typing import Dict, List, Optional, Tuple

from pos_restaurant_itb.utils.error_handlers import handle_pos_errors, ValidationError
from pos_restaurant_itb.utils.constants import (
    ErrorMessages,
    CacheKeys,
    CacheExpiration,
    NamingSeries,
    PrinterTypes
)
from pos_restaurant_itb.utils.network import is_valid_ip_address
from pos_restaurant_itb.utils.device import is_valid_bluetooth_id

class KitchenStationSetup(Document):
    """
    Kitchen Station Setup Document Class
    
    Features:
    - Automated naming sequence
    - Printer configuration validation
    - Network device validation
    - Branch-specific settings
    - Caching optimization
    
    Naming Pattern:
    KITCHEN-{branch_code}-{sequence}
    Example: KITCHEN-JKT01-0001
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._setup_defaults()
        
    def _setup_defaults(self) -> None:
        """Setup initial document defaults"""
        if not self.modified_by:
            self.modified_by = frappe.session.user
        if not self.owner:
            self.owner = frappe.session.user
        if not self.creation:
            self.creation = get_datetime_str()

    @handle_pos_errors()
    def autoname(self) -> None:
        """
        Generate unique kitchen station ID
        
        Format: KITCHEN-{branch_code}-{sequence}
        Example: KITCHEN-JKT01-0001
        
        Raises:
            ValidationError: If branch or branch code is missing
        """
        if not self.branch:
            raise ValidationError(ErrorMessages.BRANCH_REQUIRED)

        # Get branch code with cache
        branch_code = frappe.db.get_value(
            "Branch",
            self.branch,
            "branch_code",
            cache=True
        )
        
        if not branch_code:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.MISSING_BRANCH_CODE,
                    branch=self.branch
                )
            )

        branch_code = branch_code.strip().upper()
        prefix = NamingSeries.KITCHEN_PREFIX.format(branch_code=branch_code)
        
        last_number = self._get_last_sequence(prefix)
        self.name = NamingSeries.KITCHEN_FULL.format(
            prefix=prefix,
            seq=str(last_number + 1).zfill(4)
        )

    def _get_last_sequence(self, prefix: str) -> int:
        """
        Get last used sequence number
        
        Args:
            prefix: Station ID prefix
            
        Returns:
            int: Last sequence number used
        """
        cache_key = CacheKeys.get_key(
            CacheKeys.KITCHEN_SEQUENCE,
            prefix=prefix
        )
        
        last_number = frappe.cache().get_value(cache_key)
        if last_number is None:
            # Get last number from DB
            last = frappe.db.sql("""
                SELECT name 
                FROM `tabKitchen Station Setup`
                WHERE name LIKE %s 
                ORDER BY name DESC 
                LIMIT 1
            """, (f"{prefix}-%",))
            
            last_number = int(last[0][0].split("-")[-1]) if last else 0
            frappe.cache().set_value(
                cache_key,
                last_number,
                expires_in_sec=CacheExpiration.LONG
            )
            
        return last_number

    @handle_pos_errors()
    def validate(self) -> None:
        """
        Validate kitchen station setup
        
        Validates:
        1. Basic configuration
        2. Printer mappings
        3. Device connections
        """
        self._validate_basics()
        self._validate_printer_mappings()

    def _validate_basics(self) -> None:
        """
        Validate basic configuration
        
        Checks:
        - Required fields
        - Branch status
        - Station status
        """
        if not self.station_name:
            raise ValidationError(ErrorMessages.STATION_NAME_REQUIRED)
            
        if not self.branch:
            raise ValidationError(ErrorMessages.BRANCH_REQUIRED)
            
        # Check branch status
        branch = frappe.get_cached_doc("Branch", self.branch)
        if not branch.is_active:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INACTIVE_BRANCH,
                    branch=self.branch
                )
            )

    def _validate_printer_mappings(self) -> None:
        """
        Validate printer configuration
        
        Validates:
        - Printer existence
        - Connection settings
        - Network configuration
        """
        if not self.printer_list:
            return

        seen_printers = set()
        for printer in self.printer_list:
            self._validate_single_printer(printer, seen_printers)
            seen_printers.add(printer.printer)

    def _validate_single_printer(
        self,
        printer: Dict,
        seen_printers: set
    ) -> None:
        """
        Validate single printer configuration
        
        Args:
            printer: Printer configuration
            seen_printers: Set of already seen printers
            
        Raises:
            ValidationError: If validation fails
        """
        if printer.printer in seen_printers:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.DUPLICATE_PRINTER,
                    printer=printer.printer_name
                )
            )

        if printer.printer_type == PrinterTypes.THERMAL:
            self._validate_thermal_printer(printer)
        elif printer.printer_type == PrinterTypes.BLUETOOTH:
            self._validate_bluetooth_printer(printer)

    def _validate_thermal_printer(self, printer: Dict) -> None:
        """
        Validate thermal printer settings
        
        Args:
            printer: Printer configuration
        """
        if not printer.printer_ip:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.MISSING_PRINTER_IP,
                    printer=printer.printer_name
                )
            )
            
        if not is_valid_ip_address(printer.printer_ip):
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INVALID_PRINTER_IP,
                    printer=printer.printer_name,
                    ip=printer.printer_ip
                )
            )

    def _validate_bluetooth_printer(self, printer: Dict) -> None:
        """
        Validate bluetooth printer settings
        
        Args:
            printer: Printer configuration
        """
        if not printer.bluetooth_identifier:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.MISSING_BLUETOOTH_ID,
                    printer=printer.printer_name
                )
            )
            
        if not is_valid_bluetooth_id(printer.bluetooth_identifier):
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INVALID_BLUETOOTH_ID,
                    printer=printer.printer_name,
                    id=printer.bluetooth_identifier
                )
            )

    def after_save(self) -> None:
        """Update cache after saving"""
        self._update_cache()
        
    def on_trash(self) -> None:
        """Clean up cache on deletion"""
        self._clear_cache()

    def _update_cache(self) -> None:
        """Update configuration cache"""
        cache_key = CacheKeys.get_key(
            CacheKeys.KITCHEN_CONFIG,
            station=self.name
        )
        
        config = {
            "name": self.name,
            "station_name": self.station_name,
            "branch": self.branch,
            "printers": [
                {
                    "name": p.printer,
                    "type": p.printer_type,
                    "ip": p.printer_ip if p.printer_type == PrinterTypes.THERMAL else None,
                    "bluetooth_id": p.bluetooth_identifier if p.printer_type == PrinterTypes.BLUETOOTH else None
                }
                for p in (self.printer_list or [])
            ]
        }
        
        frappe.cache().set_value(
            cache_key,
            config,
            expires_in_sec=CacheExpiration.LONG
        )

    def _clear_cache(self) -> None:
        """Clear configuration cache"""
        cache_key = CacheKeys.get_key(
            CacheKeys.KITCHEN_CONFIG,
            station=self.name
        )
        frappe.cache().delete_value(cache_key)