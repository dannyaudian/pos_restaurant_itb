import frappe
from frappe import _
from frappe.utils import now

def create_kitchen_station_items_from_kot(kot_name: str) -> None:
    """
    Membuat item Kitchen Station dari KOT yang diberikan
    
    :param kot_name: Nama dokumen KOT
    """
    try:
        kot = frappe.get_doc("KOT", kot_name)
        
        # Temukan semua kitchen station aktif untuk cabang ini
        kitchen_stations = frappe.get_list(
            "Kitchen Station",
            filters={"branch": kot.branch, "is_active": 1},
            fields=["name", "item_groups", "items"]
        )
        
        if not kitchen_stations:
            frappe.logger().info(f"Tidak ada Kitchen Station aktif untuk cabang {kot.branch}")
            return
        
        # Buat kitchen display order untuk setiap kitchen station yang relevan
        for station in kitchen_stations:
            station_doc = frappe.get_doc("Kitchen Station", station.name)
            items_for_station = []
            
            # Periksa item KOT mana yang harus pergi ke kitchen station ini
            for kot_item in kot.kot_items:
                # PERBAIKAN: Tangani attribute_summary yang tidak ada
                try:
                    # Jika perlu mengakses attribute_summary, gunakan dynamic_attributes
                    # atau buat attribute_summary secara dinamis jika diperlukan
                    attribute_summary = ""
                    
                    # Jika kot_item memiliki dynamic_attributes, konversi ke summary
                    if hasattr(kot_item, 'dynamic_attributes') and kot_item.dynamic_attributes:
                        try:
                            # Jika dynamic_attributes adalah string JSON
                            import json
                            attrs = json.loads(kot_item.dynamic_attributes)
                            if isinstance(attrs, list):
                                attr_pairs = [f"{attr.get('attribute_name')}: {attr.get('attribute_value')}" 
                                             for attr in attrs if attr.get('attribute_name') and attr.get('attribute_value')]
                                attribute_summary = ", ".join(attr_pairs)
                        except:
                            # Jika bukan JSON valid, gunakan as-is
                            attribute_summary = str(kot_item.dynamic_attributes)
                    
                    # Cek apakah item ini termasuk di station ini
                    should_include = False
                    
                    # Cek berdasarkan item code
                    if station_doc.items and kot_item.item_code in [i.item for i in station_doc.items]:
                        should_include = True
                    
                    # Cek berdasarkan item group
                    if not should_include and station_doc.item_groups:
                        item_group = frappe.db.get_value("Item", kot_item.item_code, "item_group")
                        if item_group in [g.item_group for g in station_doc.item_groups]:
                            should_include = True
                    
                    if should_include:
                        items_for_station.append({
                            "item_code": kot_item.item_code,
                            "item_name": kot_item.item_name,
                            "qty": kot_item.qty,
                            "notes": kot_item.note or "",
                            "status": "New",
                            "attribute_summary": attribute_summary,  # Gunakan nilai yang kita buat
                            "kot_item": kot_item.name,
                            "table": kot.table,
                            "order_id": kot.pos_order
                        })
                except Exception as e:
                    frappe.logger().error(f"Error processing KOT item {kot_item.name}: {str(e)}")
                    continue  # Lanjutkan dengan item berikutnya
            
            # Jika ada item untuk station ini, buat kitchen display order
            if items_for_station:
                kds = frappe.new_doc("Kitchen Display Order")
                kds.update({
                    "kitchen_station": station.name,
                    "kot_id": kot.name,
                    "table": kot.table,
                    "branch": kot.branch,
                    "waiter": kot.waiter,
                    "status": "New",
                    "order_time": now()
                })
                
                # Tambahkan items ke kitchen display order
                for item in items_for_station:
                    kds.append("items", item)
                
                kds.insert(ignore_permissions=True)
                frappe.db.commit()
    
    except Exception as e:
        frappe.logger().error(f"Error creating kitchen station items from KOT {kot_name}: {str(e)}")
        raise
