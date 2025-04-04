app_name = "pos_restaurant_itb"
app_title = "POS Restaurant"
app_publisher = "PT. Innovasi Terbaik Bangsa"
app_description = "Restaurant POS Module"
app_email = "info@inovasiterbaik.co.id"
app_license = "MIT"

# Fixtures akan ditambahkan nanti setelah migrate berhasil


fixtures = [
    "Client Script",
    "Server Script",
    "Custom Field",
    "Property Setter"
]


# Tambahkan custom JS untuk Form bawaan ERPNext (POS Invoice, POS Profile, POS Order)
doctype_js = {
    "POS Order": "public/js/pos_order_autoname.js"
    "POS Order": "custom/pos_order/pos_order.js",
    "POS Invoice": "custom/pos_invoice/pos_invoice.js",
    "POS Profile": "custom/pos_profile/pos_profile.js"
}
