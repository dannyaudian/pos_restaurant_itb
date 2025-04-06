# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:08:22'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime_str
from typing import Dict, Optional, List

from pos_restaurant_itb.utils.error_handlers import handle_pos_errors, ValidationError
from pos_restaurant_itb.utils.constants import (
    KOT_STATUSES,
    ErrorMessages,
    CacheKeys,
    CacheExpiration
)
from pos_restaurant_itb.utils.common import get_waiter_name

class KOTItem(Document):
    """
    Kitchen Order Ticket Item Document Class
    
    Features:
    - Kitchen item status management
    - Status transition validation
    - Cancellation handling
    - Dynamic attributes support
    - Waiter tracking
    - Real-time updates
    
    Status Flow:
    Queued -> Cooking -> Ready -> Served
    Any Status -> Cancelled (except Served)
    """
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._status_transitions = {
            KOT_STATUSES.QUEUED: [KOT_STATUSES.COOKING, KOT_STATUSES.CANCELLED],
            KOT_STATUSES.COOKING: [KOT_STATUSES.READY, KOT_STATUSES.CANCELLED],
            KOT_STATUSES.READY: [KOT_STATUSES.SERVED, KOT_STATUSES.CANCELLED],
            KOT_STATUSES.SERVED: [],  # Final state
            KOT_STATUSES.CANCELLED: []  # Final state
        }
    
    @handle_pos_errors()
    def validate(self) -> None:
        """
        Validate KOT Item
        
        Validates:
        1. Default values
        2. Status transitions
        3. Cancellation requirements
        4. Item details
        """
        self._set_defaults()
        self._validate_item()
        self._validate_status()
        self._validate_cancellation()
        
    def _set_defaults(self) -> None:
        """
        Set default values
        
        Sets:
        - Initial status
        - Timestamps
        - Waiter assignment
        """
        if not self.kot_status:
            self.kot_status = KOT_STATUSES.QUEUED
            
        if self.kot_status and not self.kot_last_update:
            self.kot_last_update = get_datetime_str()
            
        if not self.waiter:
            self._set_waiter()
            
    def _set_waiter(self) -> None:
        """
        Set waiter from parent or current user
        
        Priority:
        1. Parent KOT waiter
        2. Current user
        3. System default
        """
        if self.parent:
            parent_waiter = frappe.db.get_value(
                "KOT",
                self.parent,
                "waiter",
                cache=True
            )
            self.waiter = parent_waiter or get_waiter_name()
        else:
            self.waiter = get_waiter_name()
            
    def _validate_item(self) -> None:
        """
        Validate item details
        
        Checks:
        - Item existence
        - Item status
        - Dynamic attributes
        """
        if not frappe.db.exists("Item", self.item_code):
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.ITEM_NOT_FOUND,
                    item=self.item_code
                )
            )
            
        item = frappe.get_cached_doc("Item", self.item_code)
        if not item.is_active:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INACTIVE_ITEM,
                    item=self.item_code
                )
            )
            
        # Validate dynamic attributes if present
        if self.dynamic_attributes:
            self._validate_dynamic_attributes()
            
    def _validate_dynamic_attributes(self) -> None:
        """Validate dynamic attributes if present"""
        try:
            attrs = frappe.parse_json(self.dynamic_attributes)
            if not isinstance(attrs, list):
                raise ValidationError(ErrorMessages.INVALID_ATTRIBUTES)
                
            for attr in attrs:
                if not all(key in attr for key in ["attribute_name", "attribute_value"]):
                    raise ValidationError(ErrorMessages.INVALID_ATTRIBUTE_FORMAT)
                    
        except Exception:
            raise ValidationError(ErrorMessages.INVALID_JSON)
            
    def _validate_status(self) -> None:
        """
        Validate KOT status transitions
        
        Checks:
        - Valid status value
        - Valid transition
        - Updates timestamp
        """
        if self.kot_status not in KOT_STATUSES.ALL:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INVALID_STATUS,
                    status=self.kot_status,
                    valid_statuses=", ".join(KOT_STATUSES.ALL)
                )
            )
            
        if self.has_value_changed("kot_status"):
            old_status = self.get_doc_before_save().kot_status
            self._validate_status_transition(old_status)
            self.kot_last_update = get_datetime_str()
            self._notify_status_change(old_status)
                
    def _validate_status_transition(self, old_status: str) -> None:
        """
        Validate if status transition is allowed
        
        Args:
            old_status: Previous status value
        """
        if (old_status in self._status_transitions and 
            self.kot_status not in self._status_transitions[old_status]):
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INVALID_TRANSITION,
                    old=old_status,
                    new=self.kot_status
                )
            )
            
    def _validate_cancellation(self) -> None:
        """
        Validate cancellation requirements
        
        Checks:
        - Note requirement
        - Status update
        - Timestamp update
        """
        if self.cancelled:
            if not self.cancellation_note:
                raise ValidationError(ErrorMessages.MISSING_CANCEL_NOTE)
                
            self.kot_status = KOT_STATUSES.CANCELLED
            self.kot_last_update = get_datetime_str()
            
    def _notify_status_change(self, old_status: str) -> None:
        """
        Notify status change to relevant parties
        
        Args:
            old_status: Previous status value
        """
        frappe.publish_realtime(
            "kot_item_status_update",
            {
                "kot": self.parent,
                "item": self.name,
                "item_name": self.item_name,
                "old_status": old_status,
                "new_status": self.kot_status,
                "user": frappe.session.user,
                "timestamp": str(now_datetime()),
                "waiter": self.waiter
            }
        )