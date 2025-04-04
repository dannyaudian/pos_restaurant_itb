import frappe

@frappe.whitelist()
def load_pos_restaurant_config(profile):
    if not profile:
        frappe.throw("POS Profile is required.")

    config = frappe.get_all(
        "POS Restaurant Config",
        filters={"pos_profile": profile},
        fields=[
            "name",
            "enable_kot_printing",
            "enable_customer_display",
            "receipt_template",
            "enable_qris_payment",
            "default_kitchen_station"
        ],
        limit=1
    )

    if config:
        data = config[0]
        return {
            "name": data.get("name"),
            "is_restaurant_pos": 1,
            "enable_kot_printing": data.get("enable_kot_printing", 0),
            "enable_customer_display": data.get("enable_customer_display", 0),
            "receipt_template": data.get("receipt_template", ""),
            "enable_qris_payment": data.get("enable_qris_payment", 0),
            "default_kitchen_station": data.get("default_kitchen_station", None)
        }

    return {
        "is_restaurant_pos": 0
    }