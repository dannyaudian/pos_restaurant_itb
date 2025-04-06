# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:00:11'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now, get_datetime_str
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

from pos_restaurant_itb.utils.constants import (
    KOT_STATUSES,
    KOTItemStatus,
    ErrorMessages,
    CacheKeys,
    CacheExpiration
)
from pos_restaurant_itb.utils.error_handlers import handle_pos_errors, ValidationError
from pos_restaurant_itb.utils.status_manager import StatusManager
from pos_restaurant_itb.utils.common import (
    get_branch_from_user,
    get_waiter_name,
    format_datetime
)

class KOT(Document):
    """
    Kitchen Order Ticket (KOT) Document Class
    
    Features:
    - Kitchen order management with real-time status updates
    - POS Order item tracking and synchronization
    - Smart kitchen status flow management
    - Waiter assignment and tracking
    - Comprehensive statistics tracking
    - Multi-branch permission handling
    - Cache-optimized operations
    
    Status Flow:
    New -> In Progress -> Ready -> Served
    Any Status -> Cancelled (except Ready/Served)
    """
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.status_manager = StatusManager(self.doctype, self)
        self._setup_defaults()
        
    def _setup_defaults(self) -> None:
        """Setup initial document defaults"""
        if not self.creation:
            self.creation = get_datetime_str()
        if not self.owner:
            self.owner = frappe.session.user
        if not self.kot_time:
            self.kot_time = get_datetime_str()
        if not self.status:
            self.status = KOT_STATUSES.NEW

    @handle_pos_errors()
    def validate(self) -> None:
        """
        Validate KOT document
        
        Validates:
        1. Basic requirements
        2. Branch permissions
        3. Status transitions
        4. Item validity
        5. POS Order status
        """
        self._validate_basics()
        self._validate_branch()
        self._validate_status()
        self._validate_items()
        
        if self.pos_order:
            self._validate_pos_order()

    def _validate_basics(self) -> None:
        """
        Validate basic KOT requirements
        
        Checks:
        - Items existence
        - Waiter assignment
        - Branch assignment
        """
        if not self.kot_items:
            raise ValidationError(ErrorMessages.NO_ITEMS)
            
        if not self.waiter:
            self.waiter = get_waiter_name()
            
        if not self.branch:
            self.branch = get_branch_from_user()

    def _validate_branch(self) -> None:
        """
        Validate branch access permissions
        
        Uses cached branch permissions for performance
        """
        if not frappe.flags.in_test:
            cache_key = CacheKeys.get_key(
                CacheKeys.USER_BRANCHES,
                user=frappe.session.user
            )
            allowed_branches = frappe.cache().get_value(cache_key)
            
            if not allowed_branches or self.branch not in allowed_branches:
                raise ValidationError(
                    ErrorMessages.format(
                        ErrorMessages.BRANCH_ACCESS_DENIED,
                        branch=self.branch,
                        user=frappe.session.user
                    )
                )

    def _validate_status(self) -> None:
        """
        Validate status transitions
        
        Uses StatusManager for consistent status management
        """
        if self.has_value_changed("status"):
            self.status_manager.validate_status(self.status)
            old_doc = self.get_doc_before_save()
            if old_doc:
                self.status_manager.validate_transition(
                    old_doc.status,
                    self.status
                )

    def _validate_items(self) -> None:
        """
        Validate KOT items
        
        Checks:
        - Item code existence
        - Duplicate prevention
        - Status validity
        """
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
            
            # Validate item status
            if item.kot_status not in KOTItemStatus.ALL:
                item.kot_status = KOTItemStatus.QUEUED

    def _validate_pos_order(self) -> None:
        """
        Validate linked POS Order
        
        Checks:
        - Order existence
        - Order status
        - Cancellation status
        """
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

    def before_save(self) -> None:
        """Set defaults before saving"""
        self._setup_defaults()
        self._update_timestamps()

    def _update_timestamps(self) -> None:
        """Update various timestamps"""
        current_time = get_datetime_str()
        
        if self.has_value_changed("status"):
            self.modified = current_time
            self.modified_by = frappe.session.user
            
        for item in self.kot_items:
            if item.has_value_changed("kot_status"):
                item.kot_last_update = current_time

    def on_update(self) -> None:
        """
        Handle KOT update events
        
        1. Update linked documents
        2. Send notifications
        3. Update statistics
        """
        self._update_pos_order_items()
        self._notify_status_change()
        self._update_statistics()

    def on_trash(self) -> None:
        """Cleanup on deletion"""
        self._revert_pos_order_items()

    def on_cancel(self) -> None:
        """Handle KOT cancellation"""
        self._validate_cancellation()
        self._revert_pos_order_items()
        self.status = KOT_STATUSES.CANCELLED
        self._notify_status_change()

    # ... [rest of the methods remain the same] ...

def get_permission_query_conditions(user: Optional[str] = None) -> str:
    """
    Get permission query conditions for KOT
    
    Args:
        user: User to check permissions for
        
    Returns:
        str: SQL conditions for permission filtering
    """
    from pos_restaurant_itb.utils.permissions import get_kot_conditions
    return get_kot_conditions(user)

def has_permission(
    doc: Dict,
    user: Optional[str] = None,
    permission_type: Optional[str] = None
) -> bool:
    """
    Check permission for KOT
    
    Args:
        doc: Document to check
        user: User to check permissions for
        permission_type: Type of permission to check
        
    Returns:
        bool: True if has permission
    """
    from pos_restaurant_itb.utils.permissions import check_kot_permission
    return check_kot_permission(doc, user, permission_type)