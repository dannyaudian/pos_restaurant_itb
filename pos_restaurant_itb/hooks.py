# pos_restaurant_itb/hooks.py

app_name = "pos_restaurant_itb"
app_title = "POS Restaurant"
app_publisher = "PT. Innovasi Terbaik Bangsa"
app_description = "Restaurant POS Module"
app_email = "info@inovasiterbaik.co.id"
app_license = "MIT"

# Include JS per Doctype
doctype_js = {
    "POS Order": [
        "custom/pos_order/pos_order.js"
    ]
}

# Document Events
doc_events = {
    "POS Order": {
        "after_insert": "pos_restaurant_itb.utils.pos_order.process_pos_order_after_insert",
        "on_submit": "pos_restaurant_itb.utils.pos_order.create_kot_from_pos_order"
    },
    "Kitchen Order Ticket": {
        "after_insert": [
            "pos_restaurant_itb.api.kds_handler.create_kds_from_kot",
            "pos_restaurant_itb.api.kitchen_station.create_kitchen_station_items_from_kot"
        ]
    }
}

# Fixtures
fixtures = [
    "Client Script",
    "Server Script",
    "Custom Field",
    "Workspace",
    "Property Setter",
    "Role",
    "Doctype"
    "Custom DocPerm"
]

# Whitelisted methods
whitelist_methods = {
    "pos_restaurant_itb.api.create_kot.create_kot_from_pos_order": True,
    "pos_restaurant_itb.api.get_attributes_for_item.get_attributes_for_item": True,
    "pos_restaurant_itb.api.resolve_variant.resolve_variant": True
}

# Scheduler tasks - for background processing if needed
scheduler_events = {
    "hourly": [
        "pos_restaurant_itb.utils.cleanup.clear_old_kitchen_sessions"
    ]
}

# Permissions hook
has_permission = {
    "Kitchen Display Order": "pos_restaurant_itb.utils.permissions.kds_permissions"
}