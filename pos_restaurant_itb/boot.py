# pos_restaurant_itb/boot.py

import frappe

def boot_session(bootinfo):
    """
    Menambahkan konfigurasi POS Restaurant ke bootinfo
    """
    bootinfo.pos_restaurant_config = {}
    
    # Ambil konfigurasi dari database
    config = frappe.get_single("POS Restaurant Config")
    if config:
        bootinfo.pos_restaurant_config = {
            "enable_kds": config.enable_kds,
            "default_kitchen_station": config.default_kitchen_station,
            "auto_create_kot": config.auto_create_kot,
            # Tambahkan setting lain di sini
        }