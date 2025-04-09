# pos_restaurant_itb/utils/kot_helpers.py

import frappe
import json
from frappe import _
from frappe.utils import now, now_datetime

def get_waiter_from_user(user_id: str) -> str:
    """
    Mendapatkan Employee ID dari user, atau kembalikan user_id jika tidak ditemukan
    """
    emp = frappe.db.get_value("Employee", {"user_id": user_id}, "name", cache=True)
    return emp or user_id

def generate_kot_id(branch: str) -> str:
    """
    Menghasilkan KOT ID dengan format: KOT-BRANCH-YYYYMMDD-####
    """
    import datetime

    today = datetime.datetime.now()
    date_str = today.strftime('%Y%m%d')

    latest_kot = frappe.db.sql("""
        SELECT kot_id FROM `tabKOT`
        WHERE kot_id LIKE %s
        ORDER BY creation DESC LIMIT 1
    """, f"KOT-{branch}-{date_str}-%")

    if latest_kot:
        last_id = latest_kot[0][0]
        seq = int(last_id.split('-')[-1]) + 1
    else:
        seq = 1

    return f"KOT-{branch}-{date_str}-{seq:04d}"

def get_attribute_summary(dynamic_attributes):
    """
    Mengkonversi dynamic_attributes dalam format JSON ke string yang mudah dibaca
    Fungsi utility yang dapat digunakan di berbagai tempat
    """
    try:
        if not dynamic_attributes:
            return ""
            
        if isinstance(dynamic_attributes, str):
            attrs = json.loads(dynamic_attributes or "[]")
        else:
            attrs = dynamic_attributes or []
            
        attr_pairs = [
            f"{attr.get('attribute_name')}: {attr.get('attribute_value')}" 
            for attr in attrs 
            if attr.get('attribute_name') and attr.get('attribute_value')
        ]
        return ", ".join(attr_pairs)
    except Exception as e:
        frappe.log_error(f"Error in get_attribute_summary: {str(e)}")
        return ""

def validate_kot_item(doc, method=None):
    """
    Memastikan KOT Item memiliki data yang valid, termasuk attribute_summary
    """
    # Jika diperlukan, lakukan validasi tambahan di sini
    
    # Default status jika belum diisi
    if not doc.kot_status:
        doc.kot_status = "Queued"

    # Timestamp jika status diubah
    if doc.kot_status and not doc.kot_last_update:
        doc.kot_last_update = now_datetime()
    
    # Tidak perlu mengisi attribute_summary di sini karena KOTItem class
    # sudah memiliki property untuk itu

def process_kot_item_insert(doc, method=None):
    """
    Proses setelah KOT Item diinsert
    """
    # Update parent KOT jika diperlukan
    if doc.parent:
        frappe.db.set_value("KOT", doc.parent, "last_updated", now())
        
    # Update related POS Order Item if applicable
    if doc.order_id and doc.item_code:
        pos_order_items = frappe.get_all(
            "POS Order Item", 
            filters={
                "parent": doc.pos_order,
                "item_code": doc.item_code,
                "sent_to_kitchen": 0
            },
            fields=["name"]
        )
        
        if pos_order_items:
            frappe.db.set_value("POS Order Item", pos_order_items[0].name, {
                "sent_to_kitchen": 1,
                "kot_id": doc.parent
            })