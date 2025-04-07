# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 10:00:41'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, cint
from typing import List, Dict, Optional, Any, Union

from pos_restaurant_itb.utils.constants import (
    POS_ORDER_STATUSES,
    TableStatus,
    ErrorMessages,
    NamingSeries,
    CacheKeys,
    CacheExpiration
)
from pos_restaurant_itb.utils.status_manager import StatusManager
from pos_restaurant_itb.utils.common import get_waiter_name
from pos_restaurant_itb.utils.error_handlers import handle_pos_errors, ValidationError
from pos_restaurant_itb.api.kitchen.create_kot import create_kot_from_pos_order

class POSOrder(Document):
    """
    POS Order Document Class
    
    Handles restaurant orders with:
    - Order creation and naming
    - Waiter assignment and validation
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
            
            self.order_id = NamingSeries.POS_ORDER.format(
                branch_code=branch_code.strip().upper(),
                date=date,
                seq=seq
            )
            
        self.name = self.order_id

    def validate(self) -> None:
        """Validate order before save"""
        self._validate_waiter()
        self._validate_order_type()
        self._validate_items()
        self._update_status()
        self._validate_table()
        self._validate_status_change()

    def before_save(self) -> None:
        """Set defaults before saving"""
        if not self.order_datetime:
            self.order_datetime = now_datetime()
            
        if not self.waiter_user:
            self.waiter_user = frappe.session.user

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
    def _validate_waiter(self) -> None:
        """Validate waiter assignment and permissions"""
        if not self.waiter_user:
            self.waiter_user = frappe.session.user
            
        self.waiter_name = get_waiter_name(self.waiter_user)
        self._validate_waiter_permissions()

    def _validate_waiter_permissions(self) -> None:
        """Validate waiter roles and permissions"""
        if "System Manager" in frappe.get_roles(self.waiter_user):
            self.waiter = self.waiter_user
            return

        employee = frappe.db.get_value(
            "Employee",
            {"user_id": self.waiter_user},
            ["name", "employee_name", "status"],
            as_dict=True,
            cache=True
        )

        if not employee:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.NO_EMPLOYEE_RECORD,
                    user=self.waiter_user
                )
            )

        if employee.status != "Active":
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INACTIVE_EMPLOYEE,
                    name=employee.employee_name
                )
            )

        if "Waiter" not in frappe.get_roles(self.waiter_user):
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.MISSING_ROLE,
                    role="Waiter",
                    user=employee.employee_name
                )
            )

        self.waiter = employee.name

    def _validate_order_type(self) -> None:
        """
        Validate order type requirements
        - Dine In: Requires table
        - Takeaway/Delivery: No table allowed
        """
        if self.order_type == "Dine In" and not self.table:
            raise ValidationError(ErrorMessages.TABLE_REQUIRED)
        
        if self.order_type in ["Takeaway", "Delivery"]:
            self.table = None
            
    def _validate_items(self) -> List[str]:
        """
        Validate items and calculate totals
        
        Returns:
            List[str]: List of item statuses
        """
        if not self.pos_order_items:
            self.status = "Draft"
            self.total_amount = 0
            return []

        # Calculate totals excluding cancelled items
        active_items = [
            item for item in self.pos_order_items 
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
        if not self.table or self.order_type != "Dine In":
            return

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
        return bool(frappe.db.exists(
            "POS Order",
            {
                "table": self.table,
                "name": ["!=", self.name],
                "docstatus": ["<", 2],
                "status": ["in", ["Draft", "In Progress", "Ready for Billing"]]
            }
        ))

    def _notify_status_change(self, old_status: str, new_status: str) -> None:
        """
        Notify status changes to relevant parties
        
        Args:
            old_status (str): Previous status
            new_status (str): New status
        """
        frappe.publish_realtime(
            "pos_order_status_update",
            {
                "order": self.name,
                "old_status": old_status,
                "new_status": new_status,
                "user": frappe.session.user,
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
        if not self.get("pos_order_items"):
            return
            
        unsent_items = [
            item for item in self.pos_order_items
            if not item.sent_to_kitchen and not item.cancelled
        ]
        
        if not unsent_items:
            return
            
        try:
            kot_name = create_kot_from_pos_order(self.name)
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
                "pos_order": self.name,
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
                    for item in self.pos_order_items
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

    def _cancel_related_documents(self) -> None:
        """Cancel related KOTs and Invoice"""
        self._cancel_kots()
        self._cancel_invoice()

    def _cancel_kots(self) -> None:
        """Cancel related KOTs"""
        for item in self.pos_order_items:
            if item.kot_id:
                try:
                    kot = frappe.get_doc("KOT", item.kot_id)
                    if kot.docstatus != 2:
                        kot.cancel()
                        frappe.msgprint(
                            _(f"🗑️ KOT {kot.name} cancelled"),
                            alert=True
                        )
                except Exception as e:
                    frappe.log_error(
                        f"Failed to cancel KOT {item.kot_id}: {str(e)}",
                        "KOT Cancellation Error"
                    )

    def _cancel_invoice(self) -> None:
        """Cancel related Sales Invoice"""
        if not self.sales_invoice:
            return
            
        try:
            invoice = frappe.get_doc("Sales Invoice", self.sales_invoice)
            if invoice.docstatus != 2:
                invoice.cancel()
                frappe.msgprint(
                    _(f"🗑️ Sales Invoice {invoice.name} cancelled"),
                    alert=True
                )
        except Exception as e:
            frappe.log_error(
                f"Failed to cancel invoice {self.sales_invoice}: {str(e)}",
                "Invoice Cancellation Error"
            )

    def _update_statistics(self) -> None:
        """Update order statistics"""
        try:
            self._update_branch_stats()
            self._update_table_stats()
        except Exception as e:
            frappe.log_error(
                f"Failed to update statistics for order {self.name}: {str(e)}",
                "Statistics Update Error"
            )

    def _update_branch_stats(self) -> None:
        """Update branch statistics"""
        stats_key = f"branch_stats:{self.branch}:{self.creation.date()}"
        stats = frappe.cache().get_value(stats_key) or {
            "total_orders": 0,
            "total_amount": 0
        }
        
        stats["total_orders"] += 1
        stats["total_amount"] += self.total_amount
        
        frappe.cache().set_value(
            stats_key,
            stats,
            expires_in_sec=CacheExpiration.LONG
        )

    def _update_table_stats(self) -> None:
        """Update table statistics"""
        if not self.table:
            return
            
        table_key = f"table_stats:{self.table}"
        table_stats = frappe.cache().get_value(table_key) or {
            "total_orders": 0,
            "total_amount": 0,
            "last_order": None
        }
        
        table_stats["total_orders"] += 1
        table_stats["total_amount"] += self.total_amount
        table_stats["last_order"] = self.name
        
        frappe.cache().set_value(
            table_key,
            table_stats,
            expires_in_sec=CacheExpiration.LONG
        )

    def _get_next_sequence(self) -> int:
        """Get next sequence number for order ID"""
        key = CacheKeys.get_key(
            CacheKeys.ORDER_SEQUENCE,
            branch=self.branch,
            date=now_datetime().date()
        )
        seq = frappe.cache().get_value(key) or 0
        seq += 1
        frappe.cache().set_value(
            key,
            seq,
            expires_in_sec=CacheExpiration.LONG
        )
        return seq

# Permission Handlers
def get_permission_query_conditions(user: Optional[str] = None) -> str:
    """Get permission query conditions for POS Order"""
    from pos_restaurant_itb.utils.permissions import (
        get_pos_order_conditions
    )
    return get_pos_order_conditions(user)

def has_permission(
    doc: Dict,
    user: Optional[str] = None,
    permission_type: Optional[str] = None
) -> bool:
    """Check permission for POS Order"""
    from pos_restaurant_itb.utils.permissions import (
        check_pos_order_permission
    )
    return check_pos_order_permission(doc, user, permission_type)