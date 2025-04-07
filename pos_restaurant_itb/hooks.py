# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

"""
POS Restaurant ITB - Hooks Configuration
----------------------------------------
Hooks and configurations for pos_restaurant_itb module.

More info: https://github.com/PT-ITB/pos_restaurant_itb/wiki/Hooks-Configuration
"""

__created_date__ = '2025-04-06 15:25:01'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'
__version__ = '1.0.0'

# -----------------------------------------------------
# App Metadata
# -----------------------------------------------------
app_name = "pos_restaurant_itb"
app_title = "POS Restaurant"
app_publisher = "PT. Innovasi Terbaik Bangsa"
app_description = "Restaurant POS Module"
app_email = "info@inovasiterbaik.co.id"
app_license = "MIT"
app_version = "1.0.0"

# -----------------------------------------------------
# Fixtures
# -----------------------------------------------------
fixtures = [
    "Custom Field",
    "Property Setter",
    "Client Script",
    "Server Script",
    "DocType",
    "Custom DocPerm",
    {
        "dt": "Role",
        "filters": [["name", "in", [
            "Restaurant Manager",
            "Outlet Manager",
            "Waiter",
            "Kitchen User",
            "Cashier",
            "QR Order User"
        ]]]
    },
    {
        "dt": "POS Restaurant Settings",
        "filters": [["name", "=", "POS Restaurant Settings"]]
    }
]

# -----------------------------------------------------
# Frontend Assets
# -----------------------------------------------------
app_include_js = [
    "/assets/pos_restaurant_itb/js/auto_refresh.js",
    "/assets/pos_restaurant_itb/js/pos_extensions.js",
    "/assets/pos_restaurant_itb/js/kitchen_display.js"
]

app_include_css = [
    "/assets/pos_restaurant_itb/css/pos_restaurant.css",
    "/assets/pos_restaurant_itb/css/kitchen_display.css"
]

# -----------------------------------------------------
# Doctype Custom JS
# -----------------------------------------------------
doctype_js = {
    "POS Order": [
        "custom/pos_order/pos_order.js",
        "custom/pos_order/pos_order_buttons.js",
        "custom/pos_order/pos_order_list.js"
    ],
    "POS Invoice": "custom/pos_invoice/pos_invoice.js",
    "POS Profile": "custom/pos_profile/pos_profile.js",
    "KOT": [
        "custom/kot/kot_button.js",
        "custom/kot/kot_list.js"
    ],
    "Kitchen Display Order": [
        "custom/kds/kds_list.js",
        "custom/kds/kds_dashboard.js"
    ],
    "QR Order": "custom/qr_order/qr_order.js",
    "Queue Management": "custom/queue/queue_dashboard.js"
}

# -----------------------------------------------------
# Document Events
# -----------------------------------------------------
doc_events = {
    "POS Order": {
        "validate": [
            "pos_restaurant_itb.utils.error_handlers.handle_pos_errors",
            "pos_restaurant_itb.utils.security.validate_branch_operation"
        ],
        "before_save": [
            "pos_restaurant_itb.utils.common.validate_working_day",
            "pos_restaurant_itb.utils.common.validate_table_availability"
        ],
        "after_insert": "pos_restaurant_itb.utils.optimization.update_pos_order_stats",
        "on_update": [
            "pos_restaurant_itb.events.pos_order.handle_order_update",
            "pos_restaurant_itb.events.pos_order.sync_order_status"
        ],
        "on_submit": [
            "pos_restaurant_itb.events.pos_order.create_invoice",
            "pos_restaurant_itb.events.pos_order.update_table_status"
        ],
        "on_cancel": "pos_restaurant_itb.events.pos_order.handle_order_cancel"
    },
    "KOT": {
        "after_insert": [
            "pos_restaurant_itb.events.kot.create_kds_order",
            "pos_restaurant_itb.events.kot.notify_kitchen_station"
        ],
        "on_update": [
            "pos_restaurant_itb.events.kot.notify_kitchen",
            "pos_restaurant_itb.events.kot.update_order_status"
        ]
    },
    "QR Order": {
        "validate": "pos_restaurant_itb.utils.security.validate_qr_session",
        "on_update": "pos_restaurant_itb.events.qr_order.sync_order_status",
        "after_insert": "pos_restaurant_itb.events.qr_order.create_pos_order"
    }
}

# -----------------------------------------------------
# Scheduled Tasks
# -----------------------------------------------------
scheduler_events = {
    "daily": [
        "pos_restaurant_itb.utils.optimization.cleanup_old_data",
        "pos_restaurant_itb.utils.analytics.generate_daily_report"
    ],
    "hourly": [
        "pos_restaurant_itb.utils.optimization.update_stats",
        "pos_restaurant_itb.utils.analytics.update_metrics"
    ],
    "cron": {
        "0 0 * * *": [
            "pos_restaurant_itb.utils.data_cleanup.archive_old_orders",
            "pos_restaurant_itb.utils.analytics.reset_daily_counters"
        ],
        "*/15 * * * *": [
            "pos_restaurant_itb.utils.queue.update_wait_times",
            "pos_restaurant_itb.utils.analytics.update_realtime_metrics"
        ]
    }
}

# -----------------------------------------------------
# Permissions & Security
# -----------------------------------------------------
permission_query_conditions = {
    "POS Order": "pos_restaurant_itb.utils.security.get_pos_permission_query",
    "KOT": "pos_restaurant_itb.utils.security.get_kot_permission_query",
    "QR Order": "pos_restaurant_itb.utils.security.get_qr_order_permission_query"
}

has_permission = {
    "POS Order": "pos_restaurant_itb.utils.security.validate_pos_permission",
    "QR Order": "pos_restaurant_itb.utils.security.validate_qr_permission"
}

# -----------------------------------------------------
# REST API
# -----------------------------------------------------
rest_apis = [
    {
        "API": "pos_restaurant_itb.api",
        "URI": "/api/method/pos_restaurant_itb.api"
    },
    {
        "API": "pos_restaurant_itb.api.qr",
        "URI": "/api/method/pos_restaurant_itb.api.qr"
    }
]

whitelisted_methods = [
    "pos_restaurant_itb.utils.common.get_new_order_id",
    "pos_restaurant_itb.utils.common.update_kot_item_status",
    "pos_restaurant_itb.utils.common.get_business_date",
    "pos_restaurant_itb.api.kitchen_station.get_kitchen_items",
    "pos_restaurant_itb.api.kds.get_kds_dashboard",
    "pos_restaurant_itb.api.table_status.get_table_status",
    "pos_restaurant_itb.api.queue_manager.get_queue_status",
    "pos_restaurant_itb.api.qr_session.create_qr_session",
    "pos_restaurant_itb.api.qr_order.create_qr_order"
]

# -----------------------------------------------------
# Website Portal
# -----------------------------------------------------
portal_menu_items = [
    {"title": "My Orders", "route": "/orders", "reference_doctype": "POS Order"},
    {"title": "QR Orders", "route": "/qr-orders", "reference_doctype": "QR Order"}
]

website_route_rules = [
    {"from_route": "/orders", "to_route": "pos_restaurant_itb.www.orders"},
    {"from_route": "/qr-orders", "to_route": "pos_restaurant_itb.www.qr_orders"}
]

# -----------------------------------------------------
# Doctype Overrides
# -----------------------------------------------------
override_doctype_class = {
    "POS Profile": "pos_restaurant_itb.overrides.pos_profile.CustomPOSProfile",
    "POS Invoice": "pos_restaurant_itb.overrides.pos_invoice.CustomPOSInvoice"
}

# -----------------------------------------------------
# Redis Queues
# -----------------------------------------------------
rq_queues = [
    {"name": "pos_restaurant_itb", "connection_kwargs": {"queue_type": "default", "async_timeout": 30}},
    {"name": "pos_restaurant_itb_long", "connection_kwargs": {"queue_type": "long", "async_timeout": 600}}
]

# -----------------------------------------------------
# Session and Boot
# -----------------------------------------------------
boot_session = "pos_restaurant_itb.boot.boot_session"

# -----------------------------------------------------
# Error Handling
# -----------------------------------------------------
error_handlers = [
    "pos_restaurant_itb.utils.error_handlers.handle_pos_errors",
    "pos_restaurant_itb.utils.error_handlers.POSRestaurantError"
]

# -----------------------------------------------------
# Setup Tasks
# -----------------------------------------------------
after_migrate = [
    "pos_restaurant_itb.setup.install.after_install",
    "pos_restaurant_itb.setup.install.create_custom_fields"
]

before_tests = [
    "pos_restaurant_itb.tests.test_setup.setup_test_data",
    "pos_restaurant_itb.tests.test_setup.setup_test_config"
]

# -----------------------------------------------------
# Jinja Filters
# -----------------------------------------------------
jinja = {
    "filters": [
        "pos_restaurant_itb.utils.jinja_filters.format_currency",
        "pos_restaurant_itb.utils.jinja_filters.format_datetime",
        "pos_restaurant_itb.utils.jinja_filters.format_order_status"
    ]
}

# -----------------------------------------------------
# Translatable Content
# -----------------------------------------------------
translatable = [
    {"doctype": "POS Order", "language": ["id", "en"]},
    {"doctype": "QR Order", "language": ["id", "en"]}
]
