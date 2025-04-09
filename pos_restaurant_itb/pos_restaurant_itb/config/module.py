from frappe import _

def get_data():
    return [
        {
            "label": _("Orders"),
            "items": [
                {
                    "type": "doctype",
                    "name": "POS Order",
                    "description": _("Manage POS Orders")
                },
                {
                    "type": "doctype",
                    "name": "POS Invoice",
                    "description": _("POS Invoices")
                }
            ]
        },
        {
            "label": _("Kitchen"),
            "items": [
                {
                    "type": "doctype",
                    "name": "KOT",
                    "description": _("Kitchen Order Tickets")
                },
                {
                    "type": "doctype",
                    "name": "Kitchen Display Order",
                    "description": _("Kitchen Display")
                },
                {
                    "type": "doctype",
                    "name": "Kitchen Station",
                    "description": _("Kitchen Stations")
                }
            ]
        },
        {
            "label": _("Setup"),
            "items": [
                {
                    "type": "doctype",
                    "name": "POS Restaurant Config",
                    "description": _("Restaurant Configuration")
                },
                {
                    "type": "doctype",
                    "name": "POS Table",
                    "description": _("Restaurant Tables")
                }
            ]
        },
        {
            "label": _("User Interface"),
            "items": [
                {
                    "type": "page",
                    "name": "waiter",
                    "label": _("Waiter UI"),
                    "description": _("Interface for waiters"),
                    "route": "/pos_restaurant_itb/waiter"
                }
            ]
        }
    ]