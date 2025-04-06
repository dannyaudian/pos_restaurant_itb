import frappe
from frappe import _
from frappe.utils import now, cstr
from pos_restaurant_itb.api.kitchen_station import create_kitchen_station_items_from_kot

@frappe.whitelist()
def create_kot_from_pos_order(pos_order_id):
    """
    Membuat Kitchen Order Ticket (KOT) dari POS Order
    
    Args:
        pos_order_id (str): ID dari POS Order
        
    Returns:
        str: Nama/ID dari KOT yang dibuat
        
    Raises:
        frappe.ValidationError: Jika ada masalah validasi
        frappe.DoesNotExistError: Jika POS Order tidak ditemukan
    """
    try:
        # Validasi input
        if not pos_order_id:
            frappe.throw(_("POS Order tidak boleh kosong."))
            
        # Log untuk tracking
        frappe.logger().debug(f"📝 Memulai pembuatan KOT untuk POS Order: {pos_order_id}")
        
        # Ambil POS Order
        try:
            pos_order = frappe.get_doc("POS Order", pos_order_id)
        except frappe.DoesNotExistError:
            frappe.throw(_("POS Order {0} tidak ditemukan.").format(pos_order_id))
            
        # Validasi status dokumen
        validate_pos_order(pos_order)
        
        # Ambil item yang belum dikirim
        items_to_send = get_items_to_send(pos_order)
        if not items_to_send:
            frappe.throw(_("Semua item dalam order ini sudah dikirim ke dapur atau dibatalkan."))
            
        # Buat KOT
        kot = create_kot_document(pos_order, items_to_send)
        
        # Update POS Order
        update_pos_order_items(pos_order, kot.name, items_to_send)
        
        # Commit perubahan database
        frappe.db.commit()
        
        # Proses Kitchen Station
        process_kitchen_station(kot.name)
        
        frappe.logger().info(f"✅ KOT berhasil dibuat: {kot.name}")
        return kot.name
        
    except Exception as e:
        frappe.db.rollback()
        log_error(e, pos_order_id)
        raise

def validate_pos_order(pos_order):
    """Validasi status POS Order"""
    if pos_order.docstatus != 0:
        frappe.throw(_("POS Order sudah final dan tidak dapat dikirim ke dapur."))

def get_items_to_send(pos_order):
    """Ambil item yang belum dikirim ke dapur"""
    return [
        item for item in pos_order.pos_order_items
        if not item.sent_to_kitchen and not item.cancelled
    ]

def create_kot_document(pos_order, items_to_send):
    """Buat dokumen KOT baru"""
    try:
        kot = frappe.new_doc("KOT")
        kot.update({
            "pos_order": pos_order.name,
            "table": pos_order.table,
            "branch": pos_order.branch,
            "kot_time": now(),
            "status": "New",
            "waiter": get_waiter_from_user(frappe.session.user)
        })
        
        # Tambahkan items
        for item in items_to_send:
            kot.append("kot_items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "note": item.note,
                "kot_status": "Queued",
                "kot_last_update": now(),
                "dynamic_attributes": frappe.as_json(item.dynamic_attributes or []),
                "order_id": pos_order.order_id,
                "branch": pos_order.branch,
                "waiter": kot.waiter
            })
            
        kot.insert(ignore_permissions=True)
        return kot
        
    except Exception as e:
        frappe.log_error(
            message=f"Gagal membuat KOT untuk POS Order {pos_order.name}: {str(e)}",
            title="❌ Gagal Create KOT"
        )
        raise

def update_pos_order_items(pos_order, kot_name, items_to_send):
    """Update status item di POS Order"""
    try:
        for item in pos_order.pos_order_items:
            if item in items_to_send:
                item.sent_to_kitchen = 1
                item.kot_id = kot_name
        
        pos_order.save(ignore_permissions=True)
        
    except Exception as e:
        frappe.log_error(
            message=f"Gagal update POS Order {pos_order.name}: {str(e)}",
            title="❌ Gagal Update POS Order"
        )
        raise

def process_kitchen_station(kot_name):
    """Proses pembuatan Kitchen Station Items"""
    try:
        create_kitchen_station_items_from_kot(kot_name)
    except Exception as e:
        frappe.log_error(
            message=f"Gagal membuat Kitchen Station Items untuk KOT {kot_name}: {str(e)}",
            title="❌ Warning: Kitchen Station"
        )
        frappe.msgprint(
            _("KOT berhasil dibuat, namun gagal menambahkan item ke Kitchen Station.")
        )

def get_waiter_from_user(user_id):
    """
    Ambil nama Employee berdasarkan user_id.
    
    Args:
        user_id (str): ID user yang sedang login
        
    Returns:
        str: Nama employee atau user_id jika tidak ditemukan
    """
    emp = frappe.db.get_value(
        "Employee",
        {"user_id": user_id},
        "name",
        cache=True
    )
    return emp or user_id

def log_error(error, pos_order_id):
    """Log error dengan detail"""
    error_msg = f"""
    Error saat membuat KOT
    ----------------------
    POS Order: {pos_order_id}
    User: {frappe.session.user}
    Time: {now()}
    Error: {str(error)}
    Traceback: {frappe.get_traceback()}
    """
    
    frappe.log_error(
        message=error_msg,
        title="❌ KOT Creation Error"
    )
