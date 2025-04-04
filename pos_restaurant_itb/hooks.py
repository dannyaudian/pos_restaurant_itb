app_name = "pos_restaurant_itb"
app_title = "POS Restaurant"
app_publisher = "PT. Innovasi Terbaik Bangsa"
app_description = "Restaurant POS Module"
app_email = "info@inovasiterbaik.co.id"
app_license = "MIT"

fixtures = [
    "Client Script",
    "Server Script",
    "Custom Field",
    "Property Setter",
    "Doctype"
]

doctype_js = {
    "POS Order": "custom/pos_order/pos_order.js",
    "POS Invoice": "custom/pos_invoice/pos_invoice.js",
    "POS Profile": "custom/pos_profile/pos_profile.js"
}
