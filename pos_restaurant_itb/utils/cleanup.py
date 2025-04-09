# pos_restaurant_itb/utils/cleanup.py

import frappe
from datetime import datetime, timedelta

def clear_old_kitchen_sessions():
    """
    Membersihkan sesi dapur yang sudah lama dan tidak aktif
    """
    # Contoh: Bersihkan item Kitchen Station yang sudah selesai dan lebih dari 7 hari
    cutoff_date = datetime.now() - timedelta(days=7)
    
    frappe.db.sql("""
        DELETE FROM `tabKitchen Station`
        WHERE kot_status IN ('Ready', 'Served', 'Cancelled')
        AND modified < %s
    """, cutoff_date)
    
    frappe.db.commit()