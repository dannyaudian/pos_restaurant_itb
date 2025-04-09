import frappe

def boot_session(bootinfo):
    bootinfo.pos_restaurant_config = {}
    
    default_config = {
        "pos_profile": None,
        "enable_kot_printing": 0,
        "enable_customer_display": 0,
        "default_kitchen_station": None,
        "receipt_template": "Thermal",
        "enable_qris_payment": 0
    }
    
    try:
        if frappe.db.exists("POS Restaurant Config", "POS Restaurant Config"):
            config = frappe.get_single("POS Restaurant Config")
            
            bootinfo.pos_restaurant_config = {
                "pos_profile": getattr(config, "pos_profile", default_config["pos_profile"]),
                "enable_kot_printing": getattr(config, "enable_kot_printing", default_config["enable_kot_printing"]),
                "enable_customer_display": getattr(config, "enable_customer_display", default_config["enable_customer_display"]),
                "default_kitchen_station": getattr(config, "default_kitchen_station", default_config["default_kitchen_station"]),
                "receipt_template": getattr(config, "receipt_template", default_config["receipt_template"]),
                "enable_qris_payment": getattr(config, "enable_qris_payment", default_config["enable_qris_payment"])
            }
            
            bootinfo.pos_restaurant_config["enable_kds"] = bootinfo.pos_restaurant_config["enable_kot_printing"]
            bootinfo.pos_restaurant_config["auto_create_kot"] = bootinfo.pos_restaurant_config["enable_customer_display"]
        else:
            # Record belum ada, gunakan nilai default
            bootinfo.pos_restaurant_config = default_config
            
            # Tambahkan key tambahan untuk backward compatibility
            bootinfo.pos_restaurant_config["enable_kds"] = default_config["enable_kot_printing"]
            bootinfo.pos_restaurant_config["auto_create_kot"] = default_config["enable_customer_display"]
            
            # Log bahwa record tidak ditemukan
            frappe.log_error("POS Restaurant Config record not found, using defaults", "boot_session")
    except Exception as e:
        # Log error tapi jangan crash boot process
        frappe.log_error(f"Error in boot_session: {str(e)}", "POS Restaurant Config")
        
        # Gunakan default sebagai fallback
        bootinfo.pos_restaurant_config = default_config
        
        # Tambahkan key tambahan untuk backward compatibility
        bootinfo.pos_restaurant_config["enable_kds"] = default_config["enable_kot_printing"]
        bootinfo.pos_restaurant_config["auto_create_kot"] = default_config["enable_customer_display"]