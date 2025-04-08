# Restaurant POS Core

Frappe app untuk mengelola operasional POS restoran modern:

## Modul & Fungsionalitas

### POS Order
- Auto-generate Order ID (by branch + date)
- Hitung total otomatis, validasi item
- Status: Draft → In Progress → Ready → Paid → Cancelled
- Relasi: `Order` → `Order Item`, `Sales Invoice`

### POS Table
- Data meja & cabang
- Status aktif/non-aktif

### KOT (Kitchen Order Ticket)
- Terhubung ke POS Order
- Status: New, In Progress, Ready, Served, Cancelled
- Diinput oleh waiter, ditampilkan di KDS

### KOT Item
- Detail per item makanan
- Status per item: Queued, Cooking, Ready, Cancelled
- Atribut dinamis (extra topping, note, dll)

### Kitchen Display Order
- Menampilkan KOT berdasarkan status
- Realtime untuk dapur

### Kitchen Station
- Memetakan item ke station tertentu
- Status: Draft, Active, Inactive
- Sinkronisasi dengan printer dapur

### Printer Mapping
- Thermal / Bluetooth printer
- Mapping ke station dan format print

### POS Dynamic Attribute
- Atribut tambahan untuk item (e.g. pedas, topping)
- Bisa menambah harga

---

## Role-based Access

| Modul                    | Waiter     | Sales User  | Kitchen Staff | System Manager |
|--------------------------|------------|-------------|----------------|----------------|
| POS Order                | CRU        | CRU         | -              | CRUD           |
| POS Table                | -          | -           | -              | CRUD           |
| KOT                      | CRU        | CRU         | -              | CRUD           |
| KOT Item                 | -          | -           | -              | CRUD           |
| Kitchen Display Order    | -          | -           | CRU            | CRUD           |
| Kitchen Station          | -          | -           | RU             | CRUD           |
| Dynamic Attribute        | CRU        | -           | -              | CRUD           |
| Printer Mapping          | -          | -           | -              | CRUD           |

---

## Alur Utama

```text
Customer → Waiter input Order → KOT terbit → Kitchen Display → Item dimasak
→ Status Ready → Pelayan antar → Order ditagih → Sales Invoice
