app_name = "pos_restaurant_itb"
app_title = "POS Restaurant"
app_publisher = "PT. Innovasi Terbaik Bangsa"
app_description = "Restaurant POS Module"
app_email = "info@inovasiterbaik.co.id"
app_license = "MIT"

# Fixtures
fixtures = [
    "Client Script",
    "Server Script",
    "Custom Field",
    "Property Setter",
    "Doctype",
    "Role",
    "Custom DocPerm"
]

# Include JS per Doctype
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

# Optional: Auto reload Desk
app_include_js = [
    "/assets/pos_restaurant_itb/js/auto_refresh.js"
]

# Tambahkan ini untuk mendaftarkan API routes
api_version = 1

# Whitelist API methods
has_permission = {
    "pos_restaurant_itb.api.create_kot.create_kot_from_pos_order": "pos_restaurant_itb.auth.has_pos_permission"
}

# API Configuration
rest_apis = [
    {
        "API": "pos_restaurant_itb.api",
        "URI": "/api/method/pos_restaurant_itb.api"
    }
]


website_route_rules = [
    {
        "from_route": "/pos_restaurant_itb/public/ui/login",
        "to_route": "pos_restaurant_itb/public/ui/login.html"
    }
]
