# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 17:42:00'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, cint
from typing import List, Dict, Optional, Any, Union

from pos_restaurant_itb.utils.constants import (
    QR_ORDER_STATUSES,
    TableStatus,
    ErrorMessages,
    NamingSeries,
    CacheKeys,
    CacheExpiration
)
from pos_restaurant_itb.utils.status_manager import StatusManager
from pos_restaurant_itb.utils.error_handlers import handle_pos_errors, ValidationError
from pos_restaurant_itb.api.create_kot import create_kot_from_qr_order

class QROrder(Document):
    """
    QR Order Document Class
    
    Handles QR-based restaurant orders with:
    - Order creation and naming
    - QR code validation
    - Item management
    - Status transitions
    - Table management
    - Kitchen communication
    - Invoice creation
    - Statistics tracking
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_manager = StatusManager(self.doctype, self)
        
    def autoname(self) -> None:
        """Generate unique order ID using branch code and sequence"""
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
                    config_name="Branch Code"
                )
            )

        if not self.order_id:
            date = now_datetime().strftime("%Y%m%d")
            seq = self._get_next_sequence()
            
            self.order_id = NamingSeries.QR_ORDER.format(
                branch_code=branch_code.strip().upper(),
                date=date,
                seq=seq
            )
            
        self.name = self.order_id

    def validate(self) -> None:
        """Validate order before save"""
        self._validate_qr_code()
        self._validate_items()
        self._update_status()
        self._validate_table()
        self._validate_status_change()

    def before_save(self) -> None:
        """Set defaults before saving"""
        if not self.order_datetime:
            self.order_datetime = now_datetime()

    def on_update(self) -> None:
        """Handle order update events"""
        self._update_table_status(self.status)
        self._notify_kitchen()
        self._update_statistics()

    def on_submit(self) -> None:
        """Handle order submission"""
        self._create_invoice()
        self._update_table_status("Completed")

    def on_cancel(self) -> None:
        """Handle order cancellation"""
        self._cancel_related_documents()
        self._update_table_status("Cancelled")

    def on_trash(self) -> None:
        """Cleanup on deletion"""
        if self.table:
            self._update_table_status("Available")

    # Private Methods
    def _validate_qr_code(self) -> None:
        """Validate QR code uniqueness and format"""
        if not self.qr_code:
            raise ValidationError(ErrorMessages.QR_CODE_REQUIRED)
            
        if frappe.db.exists("QR Order", {
            "qr_code": self.qr_code,
            "name": ["!=", self.name]
        }):
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.DUPLICATE_QR_CODE,
                    qr_code=self.qr_code
                )
            )
            
    def _validate_items(self) -> List[str]:
        """
        Validate items and calculate totals
        
        Returns:
            List[str]: List of item statuses
        """
        if not self.qr_order_items:
            self.status = "Draft"
            self.total_amount = 0
            return []

        # Calculate totals excluding cancelled items
        active_items = [
            item for item in self.qr_order_items 
            if not item.cancelled
        ]
        
        self.total_amount = sum(item.amount or 0 for item in active_items)
        self.total_quantity = sum(item.qty or 0 for item in active_items)
        
        return [item.kot_status or "Draft" for item in active_items]

    def _update_status(self) -> None:
        """Update order status based on item statuses"""
        item_statuses = self._validate_items()
        
        if not item_statuses:
            return
            
        new_status = self._determine_status(item_statuses)
        
        if self.status != new_status:
            old_status = self.status
            self.status = new_status
            self._notify_status_change(old_status, new_status)

    def _determine_status(self, item_statuses: List[str]) -> str:
        """
        Determine order status based on item statuses
        
        Args:
            item_statuses (List[str]): List of item statuses
            
        Returns:
            str: Determined order status
        """
        if all(s == "Ready" for s in item_statuses):
            return "Ready for Billing"
        elif any(s in ["Cooking", "Queued"] for s in item_statuses):
            return "In Progress"
        return "Draft"

    def _validate_table(self) -> None:
        """Validate table availability and status"""
        if not self.table:
            raise ValidationError(ErrorMessages.TABLE_REQUIRED)

        table = frappe.get_cached_doc("POS Table", self.table)
        
        if not table.is_active:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INACTIVE_TABLE,
                    table=self.table
                )
            )

        if self._is_table_occupied():
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.TABLE_OCCUPIED,
                    table=self.table
                )
            )

    def _is_table_occupied(self) -> bool:
        """
        Check if table is occupied by another order
        
        Returns:
            bool: True if table is occupied
        """
        return bool(frappe.db.exists({
            "doctype": ["in", ["POS Order", "QR Order"]],
            "table": self.table,
            "name": ["!=", self.name],
            "docstatus": ["<", 2],
            "status": ["in", ["Draft", "In Progress", "Ready for Billing"]]
        }))

    def _notify_status_change(self, old_status: str, new_status: str) -> None:
        """
        Notify status changes to relevant parties
        
        Args:
            old_status (str): Previous status
            new_status (str): New status
        """
        frappe.publish_realtime(
            "qr_order_status_update",
            {
                "order": self.name,
                "old_status": old_status,
                "new_status": new_status,
                "table": self.table,
                "timestamp": str(now_datetime())
            }
        )

    def _update_table_status(self, order_status: str) -> None:
        """
        Update table status based on order status
        
        Args:
            order_status (str): Current order status
        """
        if not self.table:
            return

        table = frappe.get_cached_doc("POS Table", self.table)
        
        if order_status in ["Completed", "Cancelled"]:
            table.current_status = TableStatus.AVAILABLE
        elif order_status in ["Draft", "In Progress"]:
            table.current_status = TableStatus.OCCUPIED
            
        table.save(ignore_permissions=True)

    def _notify_kitchen(self) -> None:
        """Create and send KOT for new items"""
        if not self.get("qr_order_items"):
            return
            
        unsent_items = [
            item for item in self.qr_order_items
            if not item.sent_to_kitchen and not item.cancelled
        ]
        
        if not unsent_items:
            return
            
        try:
            kot_name = create_kot_from_qr_order(self.name)
            if kot_name:
                frappe.msgprint(
                    _(f"👨‍🍳 KOT {kot_name} created and sent to kitchen"),
                    alert=True
                )
        except Exception as e:
            frappe.log_error(
                f"Failed to create KOT for order {self.name}: {str(e)}",
                "KOT Creation Error"
            )
            frappe.msgprint(
                _("⚠️ Failed to send order to kitchen"),
                indicator="red"
            )

    def _create_invoice(self) -> None:
        """Create Sales Invoice from order"""
        if self.total_amount <= 0 or self.sales_invoice:
            return
            
        try:
            invoice = frappe.get_doc({
                "doctype": "Sales Invoice",
                "customer": self.customer,
                "qr_order": self.name,
                "is_pos": 1,
                "branch": self.branch,
                "posting_date": self.order_datetime.date(),
                "items": [
                    {
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "qty": item.qty,
                        "rate": item.rate,
                        "amount": item.amount
                    }
                    for item in self.qr_order_items
                    if not item.cancelled
                ]
            })
            
            invoice.insert()
            self.db_set('sales_invoice', invoice.name)
            
            frappe.msgprint(
                _(f"✅ Sales Invoice {invoice.name} created"),
                indicator="green"
            )
            
        except Exception as e:
            frappe.log_error(
                f"Failed to create invoice for order {self.name}: {str(e)}",
                "Invoice Creation Error"
            )
            raise