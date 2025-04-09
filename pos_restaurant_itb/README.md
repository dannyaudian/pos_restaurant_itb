# Restaurant POS Core

Aplikasi Frappe untuk operasional restoran modern:  
pengelolaan order, dapur, meja, dan printer.

## Modul Utama
- **POS Order**: Pusat transaksi
- **KOT (Kitchen Order Ticket)**: Tiket masakan dari order
- **Kitchen Display (KDS)**: Tampilkan order per meja
- **Kitchen Station**: Tampilkan order per item
- **Item Attributes**: Contoh: sauce, side dish
- **Table Management**: Status & alokasi meja

---

## Struktur Folder (Custom Script)
- `custom/pos_order/` → Logika & tombol order POS
- `custom/kot/` → Script KOT & pemrosesan dapur
- `custom/kitchen_station/` → Update & pengelompokan station
- `custom/kitchen_display_order/` → Tampilan dapur
- `custom/pos_profile/` → Pengaturan kasir

---

## API Utama (`pos_restaurant_itb/api/`)

| File                        | Fungsi                                      |
|-----------------------------|---------------------------------------------|
| `resolve_variant.py`        | Resolve item variant dari template          |
| `kitchen_station.py`        | Buat station dari KOT, ringkasan atribut    |
| `kds_handler.py`            | Buat KDS otomatis dari KOT                  |
| `create_kot.py`             | Generate KOT dari POS Order                 |
| `get_available_tables.py`   | List meja aktif yang belum dipakai          |
| `get_attributes_for_item.py`| Ambil opsi atribut dari item template       |
| `sendkitchenandcancel.py`   | Kirim ke dapur, cancel item, tandai served  |
| `kitchen_station_handler.py`| Ambil item per station, update status       |
| `kot_status_update.py`      | Update status KDS dari KOT                  |
| `api.py`                    | API umum: update status, buat KDS, dsb      |

### API Integration
Semua API di sistem ini mengikuti pendekatan integrasi yang konsisten, memungkinkan update status dan pembuatan KDS dengan akurat dan cepat.

---

## Utility Functions (`pos_restaurant_itb/utils/`)

| File                  | Fungsi                                           |
|-----------------------|--------------------------------------------------|
| `kot_helpers.py`      | Helper functions untuk KOT dan attribute_summary |
| `cleanup.py`          | Pembersihan data lama secara otomatis            |
| `boot.py`             | Konfigurasi boot untuk POS Restaurant            |

### Helper Functions yang Penting

**get_attribute_summary**: 
- Tersedia di KOTItem class sebagai method instance
- Tersedia di kot_helpers.py sebagai fungsi utility reusable
- Digunakan untuk mengkonversi dynamic_attributes JSON ke string yang mudah dibaca
- Memiliki penanganan error untuk memastikan tidak pernah gagal

---

## POS Order

### Fungsi
- Auto ID → cabang + tanggal
- Validasi cabang aktif
- Hitung total + ubah status otomatis

### Field Penting
- `order_id`, `table`, `branch`, `order_type`, `customer`
- `items`, `total_amount`, `status`, `final_billed`, `sales_invoice`

### Status Flow
- Draft → In Progress → Ready for Billing → Paid / Cancelled

### Akses
| Role           | Hak Akses |
|----------------|-----------|
| System Manager | CRUD      |
| Sales User     | CRU       |
| Waiter         | CRU       |

---

## POS Table

### Field
- `table_id`, `branch`, `is_active`

### Akses
- System Manager: CRUD

---

## Kitchen Order Ticket (KOT)

### Fungsi
- Dibuat otomatis dari POS Order
- Menampung item yang perlu dimasak
- Hooks after_insert untuk generate Kitchen Station items

### Field
- `kot_id`, `pos_order`, `table`, `branch`
- `kot_time`, `items`, `status`, `waiter`

### Status
- New → In Progress → Ready → Served / Cancelled

### Akses
| Role           | Hak Akses |
|----------------|-----------|
| System Manager | CRUD      |
| Sales User     | CRU       |

### Detail Document Events
- Setiap event handler memastikan bahwa KOT diterjemahkan dengan benar ke dalam item Kitchen Station yang sesuai.

---

## KOT Item

### Field Database
- `item_code`, `item_name`, `qty`, `note`
- `kot_status`, `cancelled`, `cancellation_note`
- `dynamic_attributes` (JSON string): Menyimpan atribut dinamis dalam format JSON
- `waiter`, `order_id`, `branch`

### Property Dinamis
- `attribute_summary`: **Bukan field database**, melainkan property yang dihasilkan dari `dynamic_attributes` secara otomatis saat diakses
- Diimplementasikan sebagai Python property dengan getter method `get_attribute_summary()`
- Tersedia di semua instance KOTItem tanpa perlu disimpan di database

### Akses
- System Manager: CRUD

---

## Dynamic Attributes dan Attribute Summary

### Konsep
- **dynamic_attributes**: Field JSON yang menyimpan data atribut di database
- **attribute_summary**: Property yang menghasilkan tampilan user-friendly dari atribut dengan multi-level fallback untuk memastikan data selalu tersedia

### Format Dynamic Attributes (JSON)
```json
[
  {"attribute_name": "Spice Level", "attribute_value": "Medium"},
  {"attribute_name": "Toppings", "attribute_value": "Extra Cheese"}
]

## Kitchen SLA Log
- Logging performa dapur
- Akses: System Manager (CRUD)

---

## Kitchen Station Setup

### Field
- `station_name`, `branch`, `item_group`
- `status`, `assigned_printers`, `print_format`

### Akses
- System Manager: CRUD

---

## Kitchen Display Order

### Field
- `kot`, `table`, `branch`, `items`
- `status`, `last_updated`

### Akses
| Role           | Hak Akses |
|----------------|-----------|
| Kitchen Staff  | CRU       |
| System Manager | CRUD      |

---

## Kitchen Station

### Field
- `kot`, `item_code`, `status`, `last_updated`
- `attribute_summary`, `note`, `cancelled`, `cancellation_note`

### Akses
| Role           | Hak Akses |
|----------------|-----------|
| Kitchen Staff  | CR        |
| System Manager | CRUD      |

---

## POS Dynamic Attribute

### Field
- `attribute_name`, `attribute_value`
- `mapped_item`, `extra_price`, `pos_order_item`

### Akses
| Role           | Hak Akses |
|----------------|-----------|
| Waiter         | CRU       |
| System Manager | CRUD      |

---

## Printer Mapping

### Field
- `printer_name`, `printer_type`
- `printer_ip`, `bluetooth_identifier`
- `print_format`

### Akses
- System Manager: CRUD

---

## Troubleshooting

### Masalah Umum
- "KOTItem object has no attribute 'attribute_summary'"

### Solusi
- Memastikan bahwa pembaruan terhadap `KOTItem` menambahkan dan memproses `attribute_summary` dengan langkah-langkah yang akurat, memastikan bahwa seluruh data dipertahankan dan tersedia sebagaimana diperlukan.
---

## ERD
![ERD - POS Restaurant ITB](./pos_restaurant_itb_erd.png)

