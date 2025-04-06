# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 15:07:38'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, Optional
from datetime import datetime

from pos_restaurant_itb.utils.error_handlers import (
    handle_api_error,
    ValidationError
)
from pos_restaurant_itb.utils.security import validate_pos_profile_access
from pos_restaurant_itb.utils.constants import (
    CacheKeys,
    ConfigDefaults,
    ErrorMessages
)

@frappe.whitelist()
@handle_api_error
def load_pos_restaurant_config(profile: str) -> Dict:
    """
    Load POS Restaurant configuration for a profile
    
    Args:
        profile: POS Profile name
        
    Returns:
        Dict: Configuration data
            {
                "name": str,
                "is_restaurant_pos": bool,
                "enable_kot_printing": bool,
                "enable_customer_display": bool,
                "receipt_template": str,
                "enable_qris_payment": bool,
                "default_kitchen_station": str,
                "table_management": {
                    "enabled": bool,
                    "default_section": str,
                    "allow_table_merger": bool,
                    "max_customers_per_table": int
                },
                "kitchen_management": {
                    "enabled": bool,
                    "default_station": str,
                    "auto_print_kot": bool,
                    "preparation_time": {
                        "enabled": bool,
                        "default": int,
                        "warning_threshold": int
                    }
                },
                "payment_options": {
                    "qris": {
                        "enabled": bool,
                        "provider": str,
                        "settings": Dict
                    },
                    "card": {
                        "enabled": bool,
                        "providers": List[str]
                    }
                },
                "integrations": {
                    "customer_display": {
                        "enabled": bool,
                        "type": str,
                        "settings": Dict
                    },
                    "kitchen_display": {
                        "enabled": bool,
                        "type": str,
                        "settings": Dict
                    }
                }
            }
    """
    if not profile:
        raise ValidationError(
            "POS Profile is required",
            "Missing Data"
        )
    
    # Validate profile access
    validate_pos_profile_access(
        profile,
        frappe.session.user
    )
    
    # Check cache
    cache_key = f"{CacheKeys.POS_CONFIG}:{profile}"
    config_data = frappe.cache().get_value(cache_key)
    
    if not config_data:
        # Get base configuration
        config = get_base_config(profile)
        
        if config:
            # Process configuration
            config_data = process_config(config)
        else:
            # Return default non-restaurant config
            config_data = get_default_config()
        
        # Cache for 5 minutes
        frappe.cache().set_value(
            cache_key,
            config_data,
            expires_in_sec=300
        )
        
        # Log config load
        log_config_load(profile, config_data)
    
    return config_data

def get_base_config(profile: str) -> Optional[Dict]:
    """
    Get base configuration from database
    
    Args:
        profile: POS Profile name
        
    Returns:
        Optional[Dict]: Raw configuration data
    """
    config = frappe.get_all(
        "POS Restaurant Config",
        filters={"pos_profile": profile},
        fields=[
            "name",
            "enable_kot_printing",
            "enable_customer_display",
            "receipt_template",
            "enable_qris_payment",
            "default_kitchen_station",
            "table_management_settings",
            "kitchen_management_settings",
            "payment_settings",
            "integration_settings"
        ],
        limit=1
    )
    
    return config[0] if config else None

def process_config(raw_config: Dict) -> Dict:
    """
    Process raw configuration into structured format
    
    Args:
        raw_config: Raw configuration data
        
    Returns:
        Dict: Processed configuration
    """
    # Parse JSON settings
    table_settings = frappe.parse_json(
        raw_config.get("table_management_settings")
    ) or {}
    
    kitchen_settings = frappe.parse_json(
        raw_config.get("kitchen_management_settings")
    ) or {}
    
    payment_settings = frappe.parse_json(
        raw_config.get("payment_settings")
    ) or {}
    
    integration_settings = frappe.parse_json(
        raw_config.get("integration_settings")
    ) or {}
    
    return {
        "name": raw_config.get("name"),
        "is_restaurant_pos": True,
        "enable_kot_printing": raw_config.get(
            "enable_kot_printing",
            ConfigDefaults.ENABLE_KOT_PRINTING
        ),
        "enable_customer_display": raw_config.get(
            "enable_customer_display",
            ConfigDefaults.ENABLE_CUSTOMER_DISPLAY
        ),
        "receipt_template": raw_config.get(
            "receipt_template",
            ConfigDefaults.RECEIPT_TEMPLATE
        ),
        "enable_qris_payment": raw_config.get(
            "enable_qris_payment",
            ConfigDefaults.ENABLE_QRIS
        ),
        "default_kitchen_station": raw_config.get(
            "default_kitchen_station"
        ),
        "table_management": {
            "enabled": table_settings.get("enabled", True),
            "default_section": table_settings.get("default_section"),
            "allow_table_merger": table_settings.get("allow_merger", False),
            "max_customers_per_table": table_settings.get("max_customers", 10)
        },
        "kitchen_management": {
            "enabled": kitchen_settings.get("enabled", True),
            "default_station": kitchen_settings.get("default_station"),
            "auto_print_kot": kitchen_settings.get("auto_print", True),
            "preparation_time": {
                "enabled": kitchen_settings.get("prep_time_enabled", True),
                "default": kitchen_settings.get("default_prep_time", 30),
                "warning_threshold": kitchen_settings.get("warning_threshold", 80)
            }
        },
        "payment_options": {
            "qris": {
                "enabled": payment_settings.get("qris_enabled", False),
                "provider": payment_settings.get("qris_provider"),
                "settings": payment_settings.get("qris_settings", {})
            },
            "card": {
                "enabled": payment_settings.get("card_enabled", False),
                "providers": payment_settings.get("card_providers", [])
            }
        },
        "integrations": {
            "customer_display": {
                "enabled": integration_settings.get("customer_display_enabled", False),
                "type": integration_settings.get("customer_display_type"),
                "settings": integration_settings.get("customer_display_settings", {})
            },
            "kitchen_display": {
                "enabled": integration_settings.get("kitchen_display_enabled", False),
                "type": integration_settings.get("kitchen_display_type"),
                "settings": integration_settings.get("kitchen_display_settings", {})
            }
        }
    }

def get_default_config() -> Dict:
    """
    Get default non-restaurant configuration
    
    Returns:
        Dict: Default configuration
    """
    return {
        "is_restaurant_pos": False,
        "enable_kot_printing": False,
        "enable_customer_display": False,
        "receipt_template": "",
        "enable_qris_payment": False,
        "default_kitchen_station": None,
        "table_management": {
            "enabled": False
        },
        "kitchen_management": {
            "enabled": False
        },
        "payment_options": {
            "qris": {"enabled": False},
            "card": {"enabled": False}
        },
        "integrations": {
            "customer_display": {"enabled": False},
            "kitchen_display": {"enabled": False}
        }
    }

def log_config_load(profile: str, config: Dict) -> None:
    """
    Log configuration load event
    
    Args:
        profile: POS Profile name
        config: Loaded configuration
    """
    frappe.logger().debug(
        f"POS Config Load\n"
        f"Profile: {profile}\n"
        f"Is Restaurant: {config.get('is_restaurant_pos')}\n"
        f"User: {frappe.session.user}\n"
        f"Time: {frappe.utils.now()}"
    )