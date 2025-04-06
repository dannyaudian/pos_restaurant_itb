# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:11:59'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime_str
from typing import Optional

from pos_restaurant_itb.utils.error_handlers import handle_pos_errors, ValidationError
from pos_restaurant_itb.utils.constants import (
    KOT_STATUSES,
    ErrorMessages,
    CacheKeys,
    CacheExpiration,
    NamingSeries
)

class KitchenStation(Document):
    """
    Kitchen Station Document Class
    
    Features:
    - Station identification and naming
    - KOT item tracking
    - Status management
    - Real-time updates
    - Branch-based operations
    
    Naming Pattern:
    KS-{branch_code}-{sequence}
    Example: KS-JKT01-0001
    """
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._setup_defaults()
    
    def _setup_defaults(self) -> None:
        """Setup initial document defaults"""
        if not self.kot_status:
            self.kot_status = KOT_STATUSES.QUEUED
        if not self.kot_last_update:
            self.kot_last_update = get_datetime_str()

    @handle_pos_errors()
    def autoname(self) -> None:
        """
        Generate unique kitchen station ID
        
        Format: KS-{branch_code}-{sequence}
        Example: KS-JKT01-0001
        
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
                    ErrorMessages.MISSING_CONFIG,
                    config_name="Branch Code",
                    branch=self.branch
                )
            )

        branch_code = branch_code.strip().upper()
        sequence = self._get_next_sequence()
        
        self.name = NamingSeries.KITCHEN_STATION.format(
            branch_code=branch_code,
            seq=str(sequence).zfill(4)
        )

    def _get_next_sequence(self) -> int:
        """
        Get next sequence number for station ID
        
        Uses cached counter for performance
        
        Returns:
            int: Next sequence number
        """
        key = CacheKeys.get_key(
            CacheKeys.KITCHEN_STATION_SEQUENCE,
            branch=self.branch
        )
        
        count = frappe.cache().get_value(key)
        if count is None:
            count = frappe.db.count(
                "Kitchen Station",
                {"branch": self.branch}
            )
            frappe.cache().set_value(
                key,
                count,
                expires_in_sec=CacheExpiration.LONG
            )
        
        next_seq = count + 1
        frappe.cache().set_value(key, next_seq)
        return next_seq

    @handle_pos_errors()
    def validate(self) -> None:
        """
        Validate kitchen station document
        
        Validates:
        1. Basic requirements
        2. KOT reference
        3. Status transitions
        4. Cancellation handling
        """
        self._validate_basics()
        self._validate_kot()
        self._validate_status()
        self._handle_cancellation()

    def _validate_basics(self) -> None:
        """
        Validate basic requirements
        
        Checks:
        - Branch existence
        - Required fields
        - Status validity
        """
        if not self.branch:
            raise ValidationError(ErrorMessages.BRANCH_REQUIRED)
            
        if not self.kot_id:
            raise ValidationError(ErrorMessages.KOT_REQUIRED)
            
        if self.kot_status not in KOT_STATUSES.ALL:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.INVALID_STATUS,
                    status=self.kot_status
                )
            )

    def _validate_kot(self) -> None:
        """
        Validate KOT reference
        
        Checks:
        - KOT existence
        - KOT status
        - Branch match
        """
        kot = frappe.get_cached_doc("KOT", self.kot_id)
        
        if kot.docstatus == 2:  # Cancelled
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.KOT_CANCELLED,
                    kot=self.kot_id
                )
            )
            
        if kot.branch != self.branch:
            raise ValidationError(
                ErrorMessages.format(
                    ErrorMessages.BRANCH_MISMATCH,
                    kot=self.kot_id,
                    branch=self.branch
                )
            )

    def _validate_status(self) -> None:
        """
        Validate status changes
        
        Updates:
        - Last update timestamp
        - Notifications
        """
        if self.has_value_changed("kot_status"):
            self.kot_last_update = get_datetime_str()
            self._notify_status_change()

    def _handle_cancellation(self) -> None:
        """Handle item cancellation"""
        if self.cancelled and not self.cancellation_note:
            self.cancellation_note = "Cancelled from kitchen station"
            self.kot_status = KOT_STATUSES.CANCELLED
            self.kot_last_update = get_datetime_str()

    def _notify_status_change(self) -> None:
        """Notify status changes to relevant parties"""
        if self.has_value_changed("kot_status"):
            frappe.publish_realtime(
                "kitchen_station_update",
                {
                    "station": self.name,
                    "kot": self.kot_id,
                    "item": self.item_code,
                    "item_name": self.item_name,
                    "old_status": self.get_doc_before_save().kot_status,
                    "new_status": self.kot_status,
                    "user": frappe.session.user,
                    "timestamp": str(now_datetime()),
                    "branch": self.branch
                }
            )