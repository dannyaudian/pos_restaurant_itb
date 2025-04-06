# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

"""
POS Restaurant ITB - Hooks Configuration
--------------------------------------
Hooks and configurations for pos_restaurant_itb module.

Created: 2025-04-06 08:55:36
Author: dannyaudian
Owner: PT. Innovasi Terbaik Bangsa
"""

__created_date__ = '2025-04-06 08:55:36'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

app_name = "pos_restaurant_itb"
app_title = "POS Restaurant"
app_publisher = "PT. Innovasi Terbaik Bangsa"
app_description = "Restaurant POS Module"
app_email = "info@inovasiterbaik.co.id"
app_license = "MIT"
app_version = "1.0.0"

# Fixtures
fixtures = [
    "Client Script",
    "Server Script",
    "Custom Field",
    "Property Setter",
    "DocType",
    "Role",
    "Custom DocPerm",
    {
        "dt": "Role",
        "filters": [
            ["name", "in", [
                "Restaurant Manager",
                "Outlet Manager",
                "Waiter",
                "Kitchen User",
                "Cashier"
            ]]
        ]
    }
]

# Include JS per DocType
doctype_js = {
    "POS Order": [
        "custom/pos_order/pos_order.js",
        "custom/pos_order/pos_order_buttons.js",
        "custom/pos_order/pos_order_list.js"
    ],
    "POS Invoice": "custom/pos_invoice/pos_invoice.js",
    "POS Profile": "custom/pos_profile/pos_profile.js",
    "KOT": "custom/kot/kot_button.js",
    "Kitchen Display Order": "custom/kds/kds_list.js"
}

# Document Events
doc_events = {
    "POS Order": {
        "validate": [
            "pos_restaurant_itb.utils.error_handlers.handle_pos_errors()",
            "pos_restaurant_itb.utils.security.validate_branch_operation",
        ],
        "on_update": "pos_restaurant_itb.events.pos_order.handle_order_update",
        "on_submit": [
            "pos_restaurant_itb.events.pos_order.create_invoice",
            "pos_restaurant_itb.events.pos_order.update_table_status"
        ],
        "on_cancel": "pos_restaurant_itb.events.pos_order.handle_order_cancel",
        "after_insert": "pos_restaurant_itb.utils.optimization.update_pos_order_stats",
        "before_save": "pos_restaurant_itb.utils.common.validate_working_day"
    },
    "KOT": {
        "on_update": "pos_restaurant_itb.events.kot.notify_kitchen",
        "after_insert": "pos_restaurant_itb.events.kot.create_kds_order"
    }
}

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "pos_restaurant_itb.utils.optimization.cleanup_old_data"
    ],
    "hourly": [
        "pos_restaurant_itb.utils.optimization.update_stats"
    ],
    "cron": {
        "0 0 * * *": [  # Every midnight
            "pos_restaurant_itb.utils.data_cleanup.archive_old_orders"
        ]
    }
}

# Permission Query Conditions
permission_query_conditions = {
    "POS Order": "pos_restaurant_itb.utils.security.get_pos_permission_query",
    "KOT": "pos_restaurant_itb.utils.security.get_kot_permission_query"
}

# Has Permission
has_permission = {
    "POS Order": "pos_restaurant_itb.utils.security.validate_pos_permission",
    "pos_restaurant_itb.api.create_kot.create_kot_from_pos_order": "pos_restaurant_itb.auth.has_pos_permission"
}

# API Configuration
api_version = 1
rest_apis = [
    {
        "API": "pos_restaurant_itb.api",
        "URI": "/api/method/pos_restaurant_itb.api"
    }
]

# Override Standard DocTypes
override_doctype_class = {
    "POS Profile": "pos_restaurant_itb.overrides.pos_profile.CustomPOSProfile"
}

# Auto Reload
app_include_js = [
    "/assets/pos_restaurant_itb/js/auto_refresh.js"
]

# Portal Menu Items
portal_menu_items = [
    {
        "title": "My Orders",
        "route": "/orders",
        "reference_doctype": "POS Order"
    }
]

# Website Settings
website_route_rules = [
    {"from_route": "/orders", "to_route": "pos_restaurant_itb.www.orders"}
]

# Boot Info
boot_session = "pos_restaurant_itb.boot.boot_session"

# Error Handlers
error_handlers = [
    "pos_restaurant_itb.utils.error_handlers.handle_pos_errors",
    "pos_restaurant_itb.utils.error_handlers.POSRestaurantError",
]

# After Migrate
after_migrate = [
    "pos_restaurant_itb.setup.install.after_install"
]

# Before Tests
before_tests = [
    "pos_restaurant_itb.tests.test_setup.setup_test_data"
]

# Jinja Filters
jinja = {
    "filters": [
        "pos_restaurant_itb.utils.jinja_filters.format_currency",
        "pos_restaurant_itb.utils.jinja_filters.format_datetime"
    ]
}

# Translatable
translatable = [
    {
        "doctype": "POS Order",
        "language": ["id", "en"]
    }
]

# Redis Queue Configuration
rq_queues = [
    {
        "name": "pos_restaurant_itb",
        "connection_kwargs": {"queue_type": "default"}
    }
]

# Rate Limiting
rate_limit = [
    {
        "path": "/api/method/pos_restaurant_itb.api.create_order",
        "limit": 60,
        "seconds": 60
    }
]
# Add whitelisted methods
whitelisted_methods = [
    "pos_restaurant_itb.utils.common.get_new_order_id",
    "pos_restaurant_itb.utils.common.update_kot_item_status"
]