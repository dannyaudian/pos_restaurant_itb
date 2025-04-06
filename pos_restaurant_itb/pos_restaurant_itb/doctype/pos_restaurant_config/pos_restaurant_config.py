# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 11:00:01'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe.model.document import Document
from frappe import _
from typing import Dict, Optional, List
from enum import Enum

class RestaurantType(str, Enum):
    """Restaurant service types"""
    FULL_SERVICE = "Full Service"
    QUICK_SERVICE = "Quick Service"
    COUNTER_SERVICE = "Counter Service"

class QRType(str, Enum):
    """QR code types"""
    DYNAMIC = "Dynamic"
    STATIC_ORDER = "Static Order"
    STATIC_MENU = "Static Menu"
    NONE = "None"

class POSRestaurantSettings(Document):
    """
    POS Restaurant Settings
    
    Features:
    1. Restaurant Type Configuration
    2. Table Management with QR
    3. Monitoring Systems:
       - KDS (Outlet-level order monitoring)
       - Kitchen Stations (Item-level kitchen monitoring)
    4. Order Management
    """
    
    def validate(self) -> None:
        """Validate settings and dependencies"""
        self._validate_pos_profile()
        self._validate_restaurant_type()
        self._validate_table_management()
        self._validate_monitoring_systems()
        self._validate_order_types()
        
    def _validate_pos_profile(self) -> None:
        """Ensure unique settings per POS Profile"""
        if not self.pos_profile:
            frappe.throw(_("POS Profile is mandatory"))
            
        exists = frappe.db.exists(
            "POS Restaurant Settings",
            {
                "pos_profile": self.pos_profile,
                "name": ["!=", self.name]
            }
        )
        if exists:
            frappe.throw(_("Settings already exist for this POS Profile"))
            
    def _validate_restaurant_type(self) -> None:
        """Validate requirements for each restaurant type"""
        if not self.restaurant_type:
            frappe.throw(_("Restaurant Type is mandatory"))
            
        if self.restaurant_type == RestaurantType.FULL_SERVICE:
            if not self.enable_table_management:
                frappe.throw(_("Table Management is required for Full Service"))
                
        elif self.restaurant_type == RestaurantType.QUICK_SERVICE:
            if not self.enable_table_management:
                frappe.throw(_("Table Management is required for Quick Service"))
            # Reset monitoring for Quick Service
            self.enable_kds = 0
            self.enable_kitchen_stations = 0
                
        elif self.restaurant_type == RestaurantType.COUNTER_SERVICE:
            # Reset features for Counter Service
            self.enable_table_management = 0
            self.enable_kds = 0
            self.enable_kitchen_stations = 0
            
    def _validate_table_management(self) -> None:
        """Validate table management settings"""
        if self.enable_table_management:
            if not self.table_groups:
                frappe.throw(_("At least one Table Group must be defined"))
                
            if not self.qr_type:
                frappe.throw(_("QR Type is mandatory for Table Management"))
                
            if self.qr_type != QRType.NONE:
                if not self.qr_box_size or self.qr_box_size < 1:
                    self.qr_box_size = 10
                if not self.qr_border or self.qr_border < 0:
                    self.qr_border = 4
                    
    def _validate_monitoring_systems(self) -> None:
        """Validate KDS and Kitchen Station settings"""
        if self.enable_kds:
            if not self.kds_refresh_interval or self.kds_refresh_interval < 10:
                self.kds_refresh_interval = 30
                
        if self.enable_kitchen_stations:
            if not self.kitchen_station_settings:
                frappe.throw(_("Kitchen Station Settings is required when Kitchen Stations are enabled"))
                
            # Validate kitchen station settings exist
            if not frappe.db.exists("Kitchen Station Settings", self.kitchen_station_settings):
                frappe.throw(_("Invalid Kitchen Station Settings"))
                
    def _validate_order_types(self) -> None:
        """Validate order types configuration"""
        if not self.order_types:
            frappe.throw(_("At least one Order Type must be defined"))

    def get_features(self) -> Dict:
        """Get enabled features configuration"""
        return {
            "type": self.restaurant_type,
            "table_management": {
                "enabled": self.enable_table_management,
                "groups": [group.as_dict() for group in self.table_groups] if self.table_groups else [],
                "qr": {
                    "type": self.qr_type,
                    "box_size": self.qr_box_size,
                    "border": self.qr_border
                } if self.qr_type != QRType.NONE else None
            } if self.enable_table_management else None,
            "monitoring": {
                "kds": {
                    "enabled": self.enable_kds,
                    "refresh_interval": self.kds_refresh_interval
                } if self.enable_kds else None,
                "kitchen_stations": {
                    "enabled": self.enable_kitchen_stations,
                    "settings": self.kitchen_station_settings
                } if self.enable_kitchen_stations else None
            }
        }
        
    def get_order_config(self) -> Dict:
        """Get order configuration"""
        return {
            "types": [ot.as_dict() for ot in self.order_types]
        }

def get_settings(pos_profile: str) -> Optional[Dict]:
    """
    Get cached restaurant settings
    
    Args:
        pos_profile: POS Profile name
        
    Returns:
        Dict: Settings configuration or None
    """
    cache_key = f"pos_restaurant_settings:{pos_profile}"
    
    settings = frappe.cache().get_value(cache_key)
    if not settings:
        doc = frappe.get_doc(
            "POS Restaurant Settings",
            {"pos_profile": pos_profile}
        )
        settings = {
            "features": doc.get_features(),
            "order": doc.get_order_config()
        }
        frappe.cache().set_value(
            cache_key,
            settings,
            expires_in_sec=3600
        )
    return settings