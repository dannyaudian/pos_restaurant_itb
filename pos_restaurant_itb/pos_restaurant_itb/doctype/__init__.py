from __future__ import unicode_literals

def safe_import(module_path, class_name):
    try:
        module = __import__(module_path, fromlist=[class_name])
        globals()[class_name] = getattr(module, class_name)
    except ImportError:
        pass  # Doctype belum tersedia saat install awal
    except Exception as e:
        import frappe
        frappe.logger().error(f"Error importing {class_name} from {module_path}: {e}")

# List Doctype dan lokasi module
controllers = [
    ("pos_restaurant_itb.pos_restaurant_itb.doctype.pos_order_item.pos_order_item", "POSOrderItem"),
    ("pos_restaurant_itb.pos_restaurant_itb.doctype.pos_table.pos_table", "POSTable"),
    ("pos_restaurant_itb.pos_restaurant_itb.doctype.pos_restaurant_config.pos_restaurant_config", "POSRestaurantConfig"),
    ("pos_restaurant_itb.pos_restaurant_itb.doctype.kot_item.kot_item", "KOTItem"),
    ("pos_restaurant_itb.pos_restaurant_itb.doctype.kot.kot", "KOT"),
    ("pos_restaurant_itb.pos_restaurant_itb.doctype.pos_order.pos_order", "POSOrder"),
    ("pos_restaurant_itb.pos_restaurant_itb.doctype.pos_dynamic_attribute.pos_dynamic_attribute", "POSDynamicAttribute")
]

# Jalankan safe_import untuk masing-masing
for module_path, class_name in controllers:
    safe_import(module_path, class_name)
