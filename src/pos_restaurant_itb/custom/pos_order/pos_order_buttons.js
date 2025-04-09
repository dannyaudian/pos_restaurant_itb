/**
 * POS Order Buttons Script
 *
 * Script ini menambahkan tombol-tombol pada form POS Order seperti:
 * - Tombol Add Item: untuk menambahkan item baru ke pesanan
 * - Tombol Kirim ke Dapur: untuk mengirim item ke dapur (secara otomatis memeriksa item baru)
 * - Tombol Print: untuk mencetak KOT dan receipt
 * - Tombol Cancel Item: untuk membatalkan item
 * - Tombol Mark as Served: untuk menandai item telah disajikan
 */

frappe.ui.form.on('POS Order', {
    /**
     * Event refresh yang dipanggil setiap kali form di-refresh
     * Menambahkan tombol-tombol berdasarkan status dokumen
     *
     * @param {Object} frm - Form objek DocType POS Order
     */
    refresh(frm) {
        const { docstatus, status, final_billed } = frm.doc;

        console.log('DEBUG - Refresh UI:', {
            status: status,
            docstatus: docstatus,
            final_billed: final_billed || false,
            excludedStatuses: ["Paid", "Cancelled"],
            shouldShowButtons: !["Paid", "Cancelled"].includes(status) && !(final_billed || false)
        });

        const excludedStatuses = ["Paid", "Cancelled"];
        const isFinalBilled = final_billed || false;
        if (!excludedStatuses.includes(status) && !isFinalBilled) {
            console.log('DEBUG - Menampilkan tombol Add Item dan Kirim ke Dapur');
            ensureAddItemButton(frm);
            addKitchenButton(frm, 'Kirim ke Dapur');
        } else {
            console.log('DEBUG - Tidak menampilkan tombol karena:', {
                statusExcluded: excludedStatuses.includes(status),
                isFinalBilled: isFinalBilled
            });
        }

        addPrintButton(frm, 'Print KOT', 'pos_restaurant_itb.api.print_kot');
        addPrintButton(frm, 'Print Receipt', 'pos_restaurant_itb.api.print_receipt');
        if (!excludedStatuses.includes(status) && !isFinalBilled) {
            addCancelItemButton(frm);
        }

        if (["In Progress", "Ready for Billing"].includes(status) && !isFinalBilled) {
            addMarkServedButtons(frm);
        }
    }
});

/**
 * Fungsi untuk menambahkan tombol Add Item ke form
 *
 * @param {Object} frm - Form objek DocType POS Order
 */
function ensureAddItemButton(frm) {
    frm.add_custom_button(__('Add Item'), () => {
        const item = frm.add_child('pos_order_items', {});
        frm.refresh_field('pos_order_items');
        setTimeout(() => {
            const gridRows = frm.fields_dict.pos_order_items.grid.grid_rows;
            if (gridRows && gridRows.length > 0) {
                gridRows[gridRows.length - 1].toggle_view(true);
            }
        }, 100);
    }, __("Actions")).addClass("btn-secondary");
}

/**
 * Fungsi untuk menambahkan tombol Kirim ke Dapur ke form
 *
 * @param {Object} frm - Form objek DocType POS Order
 * @param {string} label - Label untuk tombol (Kirim ke Dapur)
 */
function addKitchenButton(frm, label) {
    frm.add_custom_button(__(label), async () => {
        if (!frm.doc.order_id && frm.doc.branch) {
            const res = await frappe.call({
                method: "pos_restaurant_itb.api.get_new_order_id",
                args: { branch: frm.doc.branch }
            });

            if (res.message) {
                await frm.set_value("order_id", res.message);
                await frm.save();
            } else {
                frappe.msgprint("❌ Gagal generate Order ID.");
                return;
            }
        }
        await sendToKitchen(frm);
    }, __("Actions")).addClass("btn-primary");
}

/**
 * Fungsi untuk menambahkan tombol Print ke form
 *
 * @param {Object} frm - Form objek DocType POS Order
 * @param {string} label - Label untuk tombol (Print KOT atau Print Receipt)
 * @param {string} method - Metode API yang akan dipanggil untuk mencetak
 */
function addPrintButton(frm, label, method) {
    frm.add_custom_button(__(label), () => {
        frappe.call({
            method,
            args: { name: frm.doc.name },
            callback: r => {
                if (r.message) {
                    const win = window.open('', '_blank');
                    if (win) {
                        win.document.write(r.message);
                        win.document.close();
                    }
                } else {
                    frappe.msgprint(__('Tidak ada output untuk dicetak.'));
                }
            }
        });
    }, __("Actions"));
}

/**
 * Fungsi untuk menambahkan tombol Cancel Item ke grid item pesanan
 *
 * @param {Object} frm - Form objek DocType POS Order
 */
function addCancelItemButton(frm) {
    const grid = frm.fields_dict.pos_order_items.grid;
    grid.add_custom_button(__('Cancel Item'), () => {
        const selected = grid.get_selected();

        if (!selected.length) {
            frappe.msgprint("Pilih item terlebih dahulu.");
            return;
        }

        const row = locals["POS Order Item"][selected[0]];
        if (!row?.name) {
            frappe.msgprint("Item tidak valid.");
            return;
        }

        frappe.prompt({
            label: 'Alasan Pembatalan',
            fieldname: 'cancellation_note',
            fieldtype: 'Small Text',
            reqd: 1
        }, (values) => {
            frappe.call({
                method: "pos_restaurant_itb.api.sendkitchenandcancel.cancel_pos_order_item",
                args: {
                    item_name: row.name,
                    reason: values.cancellation_note
                },
                callback(res) {
                    if (res.message) {
                        frappe.show_alert(res.message);
                        frm.reload_doc();
                    }
                }
            });
        }, 'Konfirmasi Pembatalan', 'Batalkan');
    });
}

/**
 * Fungsi untuk menambahkan tombol Mark as Served ke grid item
 * dan tombol Mark Semua as Served ke form
 *
 * @param {Object} frm - Form objek DocType POS Order
 */
function addMarkServedButtons(frm) {
    const grid = frm.fields_dict.pos_order_items.grid;
    grid.add_custom_button(__('Mark as Served'), () => {
        const selected = grid.get_selected();
        if (!selected.length) {
            frappe.msgprint("Pilih item terlebih dahulu.");
            return;
        }

        const row = locals["POS Order Item"][selected[0]];
        frappe.call({
            method: "pos_restaurant_itb.api.update_kot_item_status",
            args: {
                order: frm.doc.name,
                item_code: row.item_code,
                status: "Served"
            },
            callback(res) {
                if (res.message) {
                    frappe.show_alert("✅ Item ditandai sebagai 'Served'.");
                    frm.reload_doc();
                }
            }
        });
    });

    frm.add_custom_button(__('✔️ Mark Semua as Served'), () => {
        frappe.confirm("Yakin ingin menandai semua item sebagai 'Served'?", () => {
            frappe.call({
                method: "pos_restaurant_itb.api.sendkitchenandcancel.mark_all_served",
                args: { pos_order_id: frm.doc.name },
                callback(res) {
                    if (res.message) {
                        frappe.show_alert(res.message);
                        frm.reload_doc();
                    }
                }
            });
        });
    }, __("Actions"));
}

/**
 * Fungsi untuk mengirim item ke dapur
 * Memeriksa item yang belum dikirim, menampilkan konfirmasi,
 * dan memanggil API untuk membuat KOT
 *
 * @param {Object} frm - Form objek DocType POS Order
 */
async function sendToKitchen(frm) {
    const items = frm.doc.pos_order_items || [];

    if (!items.length) {
        frappe.msgprint({
            title: __("Validasi"),
            indicator: 'red',
            message: __('Tidak ada item untuk dikirim ke dapur.')
        });
        return;
    }

    const itemsToSend = items.filter(item => !item.sent_to_kitchen && !item.cancelled);

    if (!itemsToSend.length) {
        frappe.msgprint({
            title: __("Informasi"),
            indicator: 'yellow',
            message: __('Semua item sudah dikirim ke dapur atau dibatalkan.')
        });
        return;
    }

    const itemList = itemsToSend.map(item => `${item.qty}x ${item.item_name}`).join('\n');

    frappe.confirm(
        `Kirim item berikut ke dapur?\n\n${itemList}`,
        async () => {
            try {
                if (frm.doc.docstatus === 0) {
                    await frm.save('Submit');
                }

                const r = await frappe.call({
                    method: 'pos_restaurant_itb.api.create_kot.create_kot_from_pos_order',
                    args: { pos_order_id: frm.doc.name },
                    freeze: true,
                    freeze_message: __('Mengirim ke dapur...')
                });

                if (r.message) {
                    frm.reload_doc();
                    frappe.show_alert({
                        message: `✅ KOT dibuat: ${r.message}`,
                        indicator: 'green'
                    });
                }
            } catch (err) {
                console.error("KOT Error:", err);
                frappe.msgprint({
                    title: __('Error'),
                    indicator: 'red',
                    message: `Gagal mengirim ke dapur. Detail:\n${err?.message || err._server_messages || 'Unknown error'}`
                });
            }
        }
    );
}
