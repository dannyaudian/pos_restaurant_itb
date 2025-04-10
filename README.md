🍽️ POS Restaurant ITB
Aplikasi Frappe untuk operasional restoran modern.
Mendukung pengelolaan meja, transaksi, dapur, dan printer dalam satu sistem terpadu.

🧩 Modul Utama
Table Management
Manajemen status dan alokasi meja.

POS Order
Modul transaksi utama restoran.

Item Attributes
Atribut tambahan untuk item (contoh: Spice Level, Toppings).

KOT (Kitchen Order Ticket)
Tiket dapur otomatis dari pesanan pelanggan.

Kitchen Display (KDS)
Tampilan order per meja, berdasarkan data dari KOT.

Kitchen Station
Menampilkan order berdasarkan item per quantity. Data diambil dari KDS dan dipecah per item sesuai station (berdasarkan item group).

POS Kasir
Menggunakan modul POS bawaan ERPNext yang dimodifikasi untuk kebutuhan restoran.

🧾 POS Order
Fungsi
Auto-generate Order ID (berbasis cabang + tanggal)

Validasi cabang aktif

Perhitungan total otomatis

Transisi status otomatis

Alur Status
rust
Copy
Edit
Draft → In Progress → Ready for Billing → Paid / Cancelled
🪑 POS Table
Manajemen meja dalam restoran, termasuk:

Alokasi meja ke pelanggan

Status aktif/tidak aktif

Hubungan ke cabang restoran

🍳 Kitchen Order Ticket (KOT)
Fungsi
Dibuat otomatis saat POS Order disubmit

Menyimpan item yang perlu dimasak

Memicu pembuatan Kitchen Display Order

Alur Status
sql
Copy
Edit
New → In Progress → Ready → Served / Cancelled
Integrasi
Event handler otomatis mengonversi KOT menjadi entri Kitchen Station berdasarkan item yang perlu dimasak.

🧾 KOT Item
Menyimpan data tiap item makanan yang dikirim ke dapur.

Mewarisi dynamic_attributes dari POS Order.

Menyediakan properti otomatis attribute_summary.

Properti: attribute_summary
Bukan field database

Dihasilkan otomatis dari field dynamic_attributes

Berupa string deskriptif, misalnya:

yaml
Copy
Edit
Spice Level: Medium | Toppings: Extra Cheese
🧠 Dynamic Attributes Flow
1. Pemilihan Atribut di POS Order
User memilih atribut saat menambahkan item

Disimpan dalam field JSON dynamic_attributes pada POS Order Item

json
Copy
Edit
[
  { "attribute_name": "Spice Level", "attribute_value": "Medium" },
  { "attribute_name": "Toppings", "attribute_value": "Extra Cheese" }
]
2. Penyalinan ke KOT Item
Saat KOT dibuat dari POS Order, dynamic_attributes disalin ke tiap item KOT

3. Pembentukan attribute_summary
Dihitung sebagai properti Python

Tidak disimpan di DB, hanya muncul saat dibutuhkan

📺 Kitchen Display Order
Menampilkan pesanan ke dapur berdasarkan meja.

Field Utama
kot

table

branch

items

status

last_updated

🔪 Kitchen Station
Mengelompokkan dan menampilkan tiap item makanan yang sedang diproses berdasarkan station.

Field Utama
kot

item_code

status

last_updated

attribute_summary

note

cancelled

cancellation_note

⚙️ Kitchen Station Setup
Pengaturan dapur berdasarkan:

Nama station

Branch terkait

Group item yang ditangani

Format cetakan dan printer

🎛️ POS Dynamic Attribute
Digunakan untuk mendefinisikan atribut tambahan item (opsional):

attribute_name

attribute_value

mapped_item

pos_order_item

📌 Ringkasan Alur Dinamis Atribut
mathematica
Copy
Edit
POS Order Item (pilih atribut)
        ↓
Submit POS Order
        ↓
KOT Item menerima copy dynamic_attributes
        ↓
attribute_summary dihitung otomatis dari JSON
        ↓
Digunakan untuk KDS, Kitchen Station, dan cetakan
