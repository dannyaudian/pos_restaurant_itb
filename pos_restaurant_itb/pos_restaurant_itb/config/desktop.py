"""
Desktop Configuration for POS Restaurant ITB
------------------------------------------
Configuration for desktop icons and module settings.

Author: dannyaudian
Created: 2025-04-06 07:37:57
"""

from frappe import _

# Add timestamp and author information
__created_date__ = '2025-04-06 07:37:57'
__author__ = 'dannyaudian'

def get_data():
    """
    Configure desktop icon for POS Restaurant Module
    """
    return [{
        "module_name": "pos_restaurant_itb",
        "color": "#ff4d4f",  # Merah untuk POS Restaurant
        "icon": "octicon octicon-clippy",
        "type": "module",
        "label": _("Restaurant Management"),
        "category": "Domains",
        "description": _("POS, Kitchen Order, and Restaurant Management"),
        "onboard_present": True,
        "links": [
            {
                "label": _("Orders"),
                "items": [
                    {
                        "type": "doctype",
                        "name": "POS Order",
                        "label": _("POS Order"),
                        "description": _("Manage restaurant orders")
                    },
                    {
                        "type": "doctype",
                        "name": "KOT",
                        "label": _("Kitchen Order"),
                        "description": _("Kitchen order tickets")
                    },
                    {
                        "type": "doctype",
                        "name": "Kitchen Display Order",
                        "label": _("Kitchen Display"),
                        "description": _("Kitchen display system")
                    }
                ]
            },
            {
                "label": _("Billing"),
                "items": [
                    {
                        "type": "doctype",
                        "name": "POS Invoice",
                        "label": _("POS Invoice"),
                        "description": _("Restaurant invoices and payments")
                    }
                ]
            },
            {
                "label": _("Setup"),
                "items": [
                    {
                        "type": "doctype",
                        "name": "Restaurant Settings",
                        "label": _("Restaurant Settings"),
                        "description": _("Configure restaurant settings")
                    }
                ]
            }
        ]
    }]