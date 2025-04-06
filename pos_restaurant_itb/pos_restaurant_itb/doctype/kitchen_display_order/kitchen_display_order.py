# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:20:11'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now, get_datetime_str
from typing import Optional, Tuple

from pos_restaurant_itb.utils.error_handlers import handle_pos_errors, ValidationError
from pos_restaurant_itb.utils.constants import (
    KOT_STATUSES,
    ErrorMessages,
    CacheKeys,
    CacheExpiration,
    NamingSeries
)

class KitchenDisplayOrder(Document):
    """
    Kitchen Display Order Document Class
    
    Features:
    - Smart naming sequence
    - KOT synchronization
    - Status tracking
    - Timestamp management
    - Branch-based operations
    
    Naming Pattern:
    KDS-{branch_code}-{YYYYMMDD}-{sequence}
    Example: KDS-JKT01-20250406-0001
    """
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._setup_defaults()
        
    def _setup_defaults(self) -> None:
        """Setup initial document defaults"""
        if not self.status:
            self.status = KOT_STATUSES.NEW
        if not self.last_updated:
            self.last_updated = get_datetime_str()

    @handle_pos_errors()
    def autoname(self) -> None:
        """
        Generate unique KDS order ID
        
        Format: KDS-{branch_code}-{YYYYMMDD}-{sequence}
        Example: KDS-JKT01-20250406-0001
        
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

        # Generate prefix with date
        prefix = NamingSeries.KDS_PREFIX.format(
            branch_code=branch_code.upper(),
            date=now().strftime('%Y%m%d')
        )
        
        # Get last sequence with cache
        last_number = self._get_last_sequence(prefix)
        
        # Generate full name
        self.name = NamingSeries.KDS_FULL.format(
            prefix=prefix,
            seq=str(last_number + 1).zfill(4)
        )

    def _get_last_sequence(self, prefix: str) -> int:
        """
        Get last used sequence number
        
        Args:
            prefix: Order ID prefix
            
        Returns:
            int: Last sequence number used
        """
        cache_key = CacheKeys.get_key(
            CacheKeys.KDS_SEQUENCE,
            prefix=prefix
        )
        
        last_number = frappe.cache().get_value(cache_key)
        if last_number is None:
            # Get last number from DB
            last = frappe.db.sql("""
                SELECT name 
                FROM `tabKitchen Display Order`
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
            
        next_seq = last_number + 1
        frappe.cache().set_value(cache_key, next_seq)
        return last_number

    def before_insert(self) -> None:
        """
        Setup document before insertion
        
        Sets:
        - Initial status
        - Timestamp
        - Branch and table from KOT
        """
        self.last_updated = get_datetime_str()
        self.status = KOT_STATUSES.NEW

        if self.kot_id:
            self._sync_kot_data()

    def _sync_kot_data(self) -> None:
        """
        Synchronize data from KOT
        
        Updates:
        - Branch
        - Table
        - Items (if needed)
        """
        kot = frappe.get_cached_doc("KOT", self.kot_id)
        
        # Sync basic info
        if not self.branch:
            self.branch = kot.branch
        if not self.table:
            self.table = kot.table
            
        # Optional: Sync items if needed
        if not self.item_list and kot.kot_items:
            self._sync_kot_items(kot)

    def _sync_kot_items(self, kot: Document) -> None:
        """
        Synchronize items from KOT
        
        Args:
            kot: KOT document to sync from
        """
        for item in kot.kot_items:
            if not item.cancelled:
                self.append("item_list", {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "qty": item.qty,
                    "note": item.note,
                    "kot_status": item.kot_status
                })

    def on_update(self) -> None:
        """
        Handle document updates
        
        Updates:
        - Timestamp
        - Cache
        - Notifications
        """
        self.last_updated = get_datetime_str()
        self._notify_update()
        self._update_cache()

    def _notify_update(self) -> None:
        """Notify relevant parties about update"""
        frappe.publish_realtime(
            "kds_update",
            {
                "order": self.name,
                "kot": self.kot_id,
                "table": self.table,
                "status": self.status,
                "timestamp": str(now()),
                "branch": self.branch
            }
        )

    def _update_cache(self) -> None:
        """Update document cache"""
        cache_key = CacheKeys.get_key(
            CacheKeys.KDS_ORDER,
            order=self.name
        )
        
        frappe.cache().set_value(
            cache_key,
            {
                "name": self.name,
                "kot": self.kot_id,
                "table": self.table,
                "status": self.status,
                "last_updated": str(self.last_updated)
            },
            expires_in_sec=CacheExpiration.MEDIUM
        )