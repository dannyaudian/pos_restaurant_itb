# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 10:03:41'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now
from typing import Optional, Dict, Any, List

from pos_restaurant_itb.utils.constants import (
    KOT_STATUSES,
    ErrorMessages,
    CacheKeys,
    CacheExpiration
)
from pos_restaurant_itb.utils.error_handlers import handle_pos_errors, ValidationError
from pos_restaurant_itb.utils.status_manager import StatusManager
from pos_restaurant_itb.utils.common import get_branch_from_user, get_waiter_name

class KOT(Document):
    """
    Kitchen Order Ticket (KOT) Document Class
    
    Handles:
    - Kitchen orders
    - POS Order item tracking
    - Kitchen status management
    - Waiter assignments
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_manager = StatusManager(self.doctype, self)

    @handle_pos_errors()
    def validate(self) -> None:
        """Validate KOT document"""
        self._validate_basics()
        self._validate_branch()
        self._validate_status()
        self._validate_items()
        
        if self.pos_order:
            self._validate_pos_order()

    def _validate_basics(self) -> None:
        """Validate basic KOT requirements"""
        if not self.kot_items:
            raise ValidationError(ErrorMessages.NO_ITEMS)
            
        if not self.waiter:
            self.waiter = get_waiter_name()
            
        if not self.branch:
            self.branch = get_branch_from_user()

    def _validate_branch(self) -> None:
        """Validate branch access"""
        if not frappe.flags.in_test:
            allowed_branches = frappe.cache().get_value(
                CacheKeys.get_key(
                    CacheKeys.USER_BRANCHES,
                    user=frappe.session.user
                )
            )
            
            if not allowed_branches or self.branch not in allowed_branches:
                raise ValidationError(
                    ErrorMessages.format(
                        ErrorMessages.BRANCH_ACCESS_DENIED,
                        branch=self.branch,
                        user=frappe.session.user
                    )
                )

    def _validate_status(self) -> None:
        """Validate status transitions"""
        if self.has_value_changed("status"):
            self.status_manager.validate_status(self.status)
            if self.get_doc_before_save():
                self.status_manager.validate_transition(
                    self.get_doc_before_save().status,
                    self.status
                )

    def _validate_items(self) -> None:
        """Validate KOT items"""
        seen_items = set()
        for item in self.kot_items:
            if not item.item_code:
                raise ValidationError(ErrorMessages.MISSING_ITEM_CODE)
                
            key = f"{item.item_code}_{item.note or ''}"
            if key in seen_items:
                raise ValidationError(
                    ErrorMessages.format(
                        ErrorMessages.DUPLICATE_ITEM,
                        item=item.item_name
                    )
                )
            seen_items.add(key)

    def _validate_pos_order(self) -> None:
        """Validate linked POS Order"""
        pos_order = frappe.get_cached_doc("POS Order", self.pos_order)
        
        if pos_order.docstatus == 2:  # Cancelled
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.ORDER_CANCELLED,
                    order=self.pos_order
                )
            )
            
        if pos_order.status not in ["Draft", "In Progress"]:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INVALID_ORDER_STATUS,
                    status=pos_order.status
                )
            )

    def _populate_kot_items(self, pos_order: Document) -> None:
        """
        Populate KOT items from POS Order
        
        Args:
            pos_order: POS Order document
        """
        waiter_name = get_waiter_name()
        
        for item in pos_order.pos_order_items:
            if not item.cancelled and not item.sent_to_kitchen:
                self._add_kot_item(item, pos_order, waiter_name)

    def _add_kot_item(
        self,
        pos_item: Dict[str, Any],
        pos_order: Document,
        waiter_name: str
    ) -> None:
        """
        Add single KOT item
        
        Args:
            pos_item: POS Order item
            pos_order: Parent POS Order
            waiter_name: Waiter name
        """
        self.append(
            "kot_items",
            {
                "item_code": pos_item.item_code,
                "item_name": pos_item.item_name,
                "qty": pos_item.qty,
                "note": pos_item.note,
                "kot_status": "Queued",
                "kot_last_update": now(),
                "dynamic_attributes": frappe.as_json(
                    pos_item.get("dynamic_attributes") or []
                ),
                "order_id": pos_order.order_id,
                "branch": pos_order.branch,
                "waiter": waiter_name
            }
        )

    def _update_pos_order_items(self) -> None:
        """Update POS Order items with KOT reference"""
        pos_order = frappe.get_cached_doc("POS Order", self.pos_order)
        
        updated = False
        for kot_item in self.kot_items:
            for pos_item in pos_order.pos_order_items:
                if self._should_update_pos_item(pos_item, kot_item):
                    self._update_pos_item(pos_item)
                    updated = True
                    
        if updated:
            pos_order.save(ignore_permissions=True)

    def _should_update_pos_item(
        self,
        pos_item: Dict[str, Any],
        kot_item: Dict[str, Any]
    ) -> bool:
        """
        Check if POS item should be updated
        
        Args:
            pos_item: POS Order item
            kot_item: KOT item
            
        Returns:
            bool: True if should update
        """
        return (
            pos_item.item_code == kot_item.item_code and
            not pos_item.sent_to_kitchen
        )

    def _update_pos_item(self, pos_item: Dict[str, Any]) -> None:
        """
        Update POS item with KOT details
        
        Args:
            pos_item: POS Order item to update
        """
        pos_item.update({
            "sent_to_kitchen": 1,
            "kot_id": self.name,
            "kot_status": "Queued",
            "kot_last_update": now()
        })

    def before_save(self) -> None:
        """Set defaults before saving"""
        if not self.creation:
            self.creation = now()
            
        if not self.owner:
            self.owner = frappe.session.user

    def on_update(self) -> None:
        """Handle KOT update"""
        self._notify_status_change()
        self._update_statistics()

    def on_cancel(self) -> None:
        """Handle KOT cancellation"""
        self._validate_cancellation()
        self._revert_pos_order_items()

    def _validate_cancellation(self) -> None:
        """Validate if KOT can be cancelled"""
        if self.status in ["Ready", "Served"]:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INVALID_CANCELLATION,
                    status=self.status
                )
            )

    def _revert_pos_order_items(self) -> None:
        """Revert POS Order items on KOT cancellation"""
        if not self.pos_order:
            return
            
        pos_order = frappe.get_cached_doc("POS Order", self.pos_order)
        
        updated = False
        for pos_item in pos_order.pos_order_items:
            if pos_item.kot_id == self.name:
                pos_item.update({
                    "sent_to_kitchen": 0,
                    "kot_id": None,
                    "kot_status": None,
                    "kot_last_update": None
                })
                updated = True
                
        if updated:
            pos_order.save(ignore_permissions=True)

    def _notify_status_change(self) -> None:
        """Notify relevant parties about status change"""
        if self.has_value_changed("status"):
            frappe.publish_realtime(
                "kot_status_update",
                {
                    "kot": self.name,
                    "old_status": self.get_doc_before_save().status,
                    "new_status": self.status,
                    "user": frappe.session.user,
                    "timestamp": str(now())
                }
            )

    def _update_statistics(self) -> None:
        """Update KOT statistics"""
        try:
            self._update_kitchen_stats()
            self._update_waiter_stats()
        except Exception as e:
            frappe.log_error(
                f"Failed to update KOT statistics: {str(e)}",
                "KOT Statistics Error"
            )

    def _update_kitchen_stats(self) -> None:
        """Update kitchen statistics"""
        key = CacheKeys.get_key(
            CacheKeys.KITCHEN_STATS,
            branch=self.branch,
            date=self.creation.date()
        )
        stats = frappe.cache().get_value(key) or {
            "total_kots": 0,
            "total_items": 0,
            "status_counts": {}
        }
        
        stats["total_kots"] += 1
        stats["total_items"] += len(self.kot_items)
        stats["status_counts"][self.status] = (
            stats["status_counts"].get(self.status, 0) + 1
        )
        
        frappe.cache().set_value(
            key,
            stats,
            expires_in_sec=CacheExpiration.LONG
        )

    def _update_waiter_stats(self) -> None:
        """Update waiter statistics"""
        if not self.waiter:
            return
            
        key = CacheKeys.get_key(
            CacheKeys.WAITER_STATS,
            waiter=self.waiter,
            date=self.creation.date()
        )
        stats = frappe.cache().get_value(key) or {
            "total_kots": 0,
            "total_items": 0
        }
        
        stats["total_kots"] += 1
        stats["total_items"] += len(self.kot_items)
        
        frappe.cache().set_value(
            key,
            stats,
            expires_in_sec=CacheExpiration.LONG
        )

def get_permission_query_conditions(user: Optional[str] = None) -> str:
    """Get permission query conditions for KOT"""
    from pos_restaurant_itb.utils.permissions import get_kot_conditions
    return get_kot_conditions(user)

def has_permission(
    doc: Dict,
    user: Optional[str] = None,
    permission_type: Optional[str] = None
) -> bool:
    """Check permission for KOT"""
    from pos_restaurant_itb.utils.permissions import check_kot_permission
    return check_kot_permission(doc, user, permission_type)