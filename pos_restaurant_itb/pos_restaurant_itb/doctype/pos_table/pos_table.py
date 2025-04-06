# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 13:46:05'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_url, now_datetime, get_datetime
from pathlib import Path
import qrcode
import io
import base64
import os
from typing import Dict, Optional

from pos_restaurant_itb.utils.constants import (
    TableStatus,
    ErrorMessages,
    CacheKeys,
    CacheExpiration
)
from pos_restaurant_itb.utils.security import SecurityManager
from pos_restaurant_itb.utils.error_handlers import ValidationError

class POSTable(Document):
    """
    POS Table Document Class
    
    Features:
    - Table management with unique IDs
    - QR code generation (static/dynamic)
    - Status tracking
    - Branch-based access control
    - Table statistics
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize with security manager"""
        super().__init__(*args, **kwargs)
        self.security = SecurityManager()

    def autoname(self) -> None:
        """
        Generate table name using format: table_id-branch_code
        Example: T01-JKT-R1
        
        Raises:
            ValidationError: If required fields missing
        """
        if not self.table_id:
            raise ValidationError(ErrorMessages.TABLE_ID_REQUIRED)

        if not self.branch:
            raise ValidationError(ErrorMessages.BRANCH_REQUIRED)

        # Get branch code with caching
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

        self.name = f"{self.table_id}-{branch_code}"

    def validate(self) -> None:
        """
        Run all validations
        
        Order:
        1. Branch access
        2. Table ID
        3. Branch config
        4. QR code
        5. Statistics
        """
        self._validate_branch_access()
        self._validate_table_id()
        self._validate_branch()
        self._generate_qr_code()
        self._update_statistics()

    def _validate_branch_access(self) -> None:
        """
        Check if current user has access to branch
        Uses SecurityManager for centralized access control
        """
        self.security.validate_branch_operation(
            self.branch,
            "manage_tables"
        )

    def _validate_table_id(self) -> None:
        """
        Validate table_id:
        - Must exist
        - Must be alphanumeric
        - Must be unique within branch
        """
        if not self.table_id:
            raise ValidationError(ErrorMessages.TABLE_ID_REQUIRED)
            
        if not self.table_id.isalnum():
            raise ValidationError(ErrorMessages.INVALID_TABLE_ID)
            
        # Check uniqueness in branch
        existing = frappe.db.exists(
            "POS Table",
            {
                "table_id": self.table_id,
                "branch": self.branch,
                "name": ["!=", self.name]
            }
        )
        
        if existing:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.DUPLICATE_TABLE_ID,
                    table_id=self.table_id,
                    branch=self.branch
                )
            )

    def _validate_branch(self) -> None:
        """
        Validate branch configuration:
        - Must exist
        - Must have branch code
        - Must be active
        """
        if not self.branch:
            raise ValidationError(ErrorMessages.BRANCH_REQUIRED)
            
        branch = frappe.get_cached_doc("Branch", self.branch)
        
        if not branch.branch_code:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.MISSING_CONFIG,
                    config_name="Branch Code",
                    branch=self.branch
                )
            )
        
        if not branch.is_active:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INACTIVE_BRANCH,
                    branch=self.branch
                )
            )

    def _generate_qr_code(self) -> None:
        """
        Generate QR code based on settings
        
        Features:
        - Static/Dynamic QR
        - Customizable appearance
        - File/Base64 storage
        - Error handling
        """
        try:
            # Get settings
            settings = frappe.get_cached_doc("POS Settings")
            
            # Check if QR enabled
            if not settings.enable_table_qr:
                self.qr_code = None
                return
                
            # Get QR data based on type
            qr_data = self._get_qr_data(settings.qr_type)
            
            # Configure QR
            qr = qrcode.QRCode(
                version=1,  # Auto-size
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=settings.qr_box_size or 10,
                border=settings.qr_border or 4
            )
            qr.add_data(str(qr_data))
            qr.make(fit=True)
            
            # Generate image
            img = qr.make_image(
                fill_color=settings.qr_fill_color or "black",
                back_color=settings.qr_back_color or "white"
            )
            
            # Save based on settings
            if settings.qr_storage_type == "File":
                self._save_qr_to_file(img, settings)
            else:  # Base64
                self._save_qr_to_base64(img)
                
        except Exception as e:
            frappe.log_error(
                f"QR Code generation failed for table {self.name}: {str(e)}",
                "QR Code Error"
            )

    def _get_qr_data(self, qr_type: str) -> Dict:
        """
        Get QR code data based on type
        
        Args:
            qr_type: "Static" or "Dynamic"
            
        Returns:
            Dict: QR code data
        """
        base_data = {
            "table_id": self.table_id,
            "branch": self.branch,
            "name": self.name
        }
        
        if qr_type == "Dynamic":
            # Add URL and timestamp for dynamic QR
            base_url = get_url()
            base_data.update({
                "url": f"{base_url}/pos/table/{self.name}",
                "timestamp": str(now_datetime())
            })
        
        return base_data

    def _save_qr_to_file(self, img, settings) -> None:
        """
        Save QR as file
        
        Structure:
        /public/files/table_qr/table_qr_T01-JKT-R1.png
        """
        site_path = frappe.get_site_path()
        qr_folder = os.path.join(
            site_path,
            'public',
            'files',
            'table_qr'
        )
        
        # Create folder if not exists
        Path(qr_folder).mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_name = f"table_qr_{self.name}.png"
        file_path = os.path.join(qr_folder, file_name)
        img.save(file_path)
        
        # Update document
        self.qr_code = f"/files/table_qr/{file_name}"

    def _save_qr_to_base64(self, img) -> None:
        """
        Save QR as base64 in document
        Format: data:image/png;base64,...
        """
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        self.qr_code = f"data:image/png;base64,{qr_base64}"

    def on_update(self) -> None:
        """
        Handle table update events:
        1. Update linked docs if status changes
        2. Clear cache
        3. Update statistics
        """
        if self.has_value_changed("is_active"):
            self._update_linked_docs()
            self._clear_cache()
        
        self._update_statistics()

    def _update_linked_docs(self) -> None:
        """
        Update status of linked documents
        - Cancel active orders if table deactivated
        - Update table status
        """
        if not self.is_active:
            # Get active orders
            active_orders = frappe.get_all(
                "POS Order",
                filters={
                    "table": self.name,
                    "docstatus": 0
                },
                pluck="name"
            )
            
            # Cancel each order
            for order in active_orders:
                try:
                    doc = frappe.get_doc("POS Order", order)
                    doc.status = "Cancelled"
                    doc.save()
                except Exception as e:
                    frappe.log_error(
                        f"Failed to cancel order {order}: {str(e)}",
                        "Table Deactivation Error"
                    )
            
            self.current_status = TableStatus.MAINTENANCE
        else:
            self.current_status = TableStatus.AVAILABLE
            
        frappe.db.commit()

    def _update_statistics(self) -> None:
        """
        Update table statistics:
        - Total orders
        - Total amount
        - Average order value
        - Last order time
        """
        stats_key = CacheKeys.get_key(
            CacheKeys.TABLE_STATS,
            table=self.name
        )
        
        # Get or initialize stats
        stats = frappe.cache().get_value(stats_key) or {
            "total_orders": 0,
            "total_amount": 0,
            "avg_order_value": 0,
            "last_order_time": None
        }
        
        # Update last order time if changed
        if self.last_order_time:
            stats["last_order_time"] = self.last_order_time
            
        # Cache stats
        frappe.cache().set_value(
            stats_key,
            stats,
            expires_in_sec=CacheExpiration.LONG
        )

    def _clear_cache(self) -> None:
        """Clear table related cache"""
        frappe.cache().delete_value(
            CacheKeys.get_key(
                CacheKeys.TABLE_STATS,
                table=self.name
            )
        )

    @frappe.whitelist()
    def print_qr(self, print_format: Optional[str] = None) -> None:
        """
        Print table QR code
        
        Args:
            print_format: Custom print format name
            
        Raises:
            frappe.ValidationError: If QR not generated
        """
        if not self.qr_code:
            frappe.throw(_("No QR code generated for this table"))
            
        # Get settings
        settings = frappe.get_cached_doc("POS Settings")
        print_format = print_format or settings.default_table_qr_format
        
        if not print_format:
            frappe.throw(_("No print format specified for Table QR"))
            
        # Return print
        return frappe.get_print(
            "POS Table",
            self.name,
            print_format,
            doc=self
        )

def get_table_status(table: str) -> Optional[str]:
    """
    Get current table status
    
    Args:
        table: Table name
        
    Returns:
        Optional[str]: Current status or None
    """
    if not table:
        return None
        
    return frappe.db.get_value(
        "POS Table",
        table,
        "current_status",
        cache=True
    ) or TableStatus.AVAILABLE

def get_table_stats(table: str) -> Dict:
    """
    Get table statistics
    
    Args:
        table: Table name
        
    Returns:
        Dict: Statistics dictionary
    """
    stats_key = CacheKeys.get_key(
        CacheKeys.TABLE_STATS,
        table=table
    )
    
    return frappe.cache().get_value(stats_key) or {
        "total_orders": 0,
        "total_amount": 0,
        "avg_order_value": 0,
        "last_order_time": None
    }

      @frappe.whitelist()
    def print_qr(self, print_format: Optional[str] = None) -> Dict:
        """
        Print table QR code
        
        Args:
            print_format: Custom print format name
            
        Returns:
            Dict: Print data and settings
        """
        if not self.qr_code:
            frappe.throw(_("No QR code generated for this table"))
            
        settings = frappe.get_cached_doc("POS Settings")
        
        # Get print format
        print_format = (
            print_format or 
            settings.default_table_qr_format or 
            "Table QR Card"
        )
        
        # Get printer settings
        printer_settings = frappe.get_doc("Network Printer Settings", 
            settings.default_table_printer
        ) if settings.default_table_printer else None
        
        html = frappe.get_print(
            "POS Table",
            self.name,
            print_format,
            doc=self,
            no_letterhead=True
        )
        
        return {
            "print_format": print_format,
            "html": html,
            "printer": printer_settings.name if printer_settings else None,
            "print_type": settings.table_qr_print_type or "Direct",
            "preview_only": not bool(printer_settings)
        }


    @frappe.whitelist()
    def print_multiple(self, copies: int = 1) -> None:
        """
        Print multiple copies of QR
        
        Args:
            copies: Number of copies to print
        """
        if copies < 1:
            copies = 1
            
        settings = frappe.get_cached_doc("POS Settings")
        if not settings.default_table_printer:
            frappe.throw(_("No default printer set for table QR"))
            
        print_data = self.print_qr()
        
        for _ in range(copies):
            frappe.enqueue(
                'pos_restaurant_itb.utils.printing.print_to_network_printer',
                html=print_data["html"],
                printer=print_data["printer"],
                doctype="POS Table",
                docname=self.name,
                is_background=True
            )