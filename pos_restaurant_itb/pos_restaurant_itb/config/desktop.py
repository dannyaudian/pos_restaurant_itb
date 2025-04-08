from frappe import _

def get_data():
    return [{
        "module_name": "pos_restaurant_itb",
        "color": "#ff4d4f",
        "icon": "octicon octicon-clippy",
        "type": "module",
        "label": _("Restaurant Management"),
        "items": [
            {
                "type": "doctype",
                "name": "POS Order",
                "label": _("POS Order"),
                "description": _("Manage POS Orders")
            },
            {
                "type": "doctype",
                "name": "KOT",
                "label": _("Kitchen Order Ticket (KOT)"),
                "description": _("Manage Kitchen Order Tickets")
            },
            {
                "type": "doctype",
                "name": "Kitchen Display Order",
                "label": _("Kitchen Display Order"),
                "description": _("Manage Kitchen Display Orders")
            },
            {
                "type": "page",
                "name": "waiter",
                "label": _("Waiter UI"),
                "description": _("Interface for waiters to manage orders"),
                "url": "/pos_restaurant_itb/waiter"
            }
        ]
    }]