frappe.ui.form.on('POS Order', {
    refresh(frm) {
        const isDraft = frm.doc.docstatus === 0;
        const status = frm.doc.status;

        // 🔘 Tombol: Kirim ke Dapur (saat Draft)
        if (isDraft && status === "Draft") {
            frm.add_custom_button(__('Kirim ke Dapur'), () => {
                sendToKitchen(frm);
            }, __("Actions"));
        }

        // 🔘 Tombol: Kirim Tambahan ke Dapur (saat In Progress)
        if (isDraft && status === "In Progress") {
            frm.add_custom_button(__('Kirim Tambahan ke Dapur'), () => {
                sendToKitchen(frm);
            }, __("Actions"));
        }

        // 🔘 Tombol: Print KOT
        frm.add_custom_button(__('Print KOT'), () => {
            frappe.call({
                method: 'pos_restaurant_itb.api.print_kot',
                args: { name: frm.doc.name },
                callback(r) {
                    if (r.message) {
                        const win = window.open();
                        win.document.write(r.message);
                        win.document.close();
                    }
                }
            });
        }, __("Actions"));

        // 🔘 Tombol: Print Receipt
        frm.add_custom_button(__('Print Receipt'), () => {
            frappe.call({
                method: 'pos_restaurant_itb.api.print_receipt',
                args: { name: frm.doc.name },
                callback(r) {
                    if (r.message) {
                        const win = window.open();
                        win.document.write(r.message);
                        win.document.close();
                    }
                }
            });
        }, __("Actions"));

        // ❌ Tombol: Cancel Item per baris
        frm.fields_dict.pos_order_items.grid.add_custom_button(__('Cancel Item'), () => {
            const selected = frm.fields_dict.pos_order_items.grid.get_selected();
            if (!selected.length) {
                frappe.msgprint("Pilih item terlebih dahulu.");
                return;
            }

            const row = selected[0];
            frappe.prompt(
                [{
                    label: 'Alasan Pembatalan',
                    fieldname: 'cancellation_note',
                    fieldtype: 'Small Text',
                    reqd: 1
                }],
                (values) => {
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
                },
                'Konfirmasi Pembatalan',
                'Batalkan'
            );
        });

        // ✅ Tombol: Mark as Served (per item dan semua)
        if (["In Progress", "Ready for Billing"].includes(status)) {
            // Per item
            frm.fields_dict.pos_order_items.grid.add_custom_button(__('Mark as Served'), () => {
                const selected = frm.fields_dict.pos_order_items.grid.get_selected();
                if (!selected.length) {
                    frappe.msgprint("Pilih item terlebih dahulu.");
                    return;
                }

                const row = selected[0];
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

            // Semua item
            frm.add_custom_button(__('✔️ Mark Semua as Served'), () => {
                frappe.confirm("Yakin ingin menandai semua item sebagai 'Served'?", () => {
                    frappe.call({
                        method: "pos_restaurant_itb.api.sendkitchenandcancel.mark_all_served",
                        args: { pos_order_id: frm.doc.name },
                        callback(res) {
                            if (res.message) {
                                frappe.show_alert("✅ Semua item telah ditandai sebagai 'Served'.");
                                frm.reload_doc();
                            }
                        }
                    });
                });
            }, __("Actions"));
        }
    }
});

// 🔄 Fungsi Kirim ke Dapur (digunakan untuk draft dan tambahan)
function sendToKitchen(frm) {
    // Validasi sebelum kirim
    if (!frm.doc.pos_order_items || !frm.doc.pos_order_items.length) {
        frappe.msgprint({
            title: __("Validasi"),
            indicator: 'red',
            message: __('Tidak ada item untuk dikirim ke dapur.')
        });
        return;
    }

    // Cek item yang belum dikirim
    const itemsToSend = frm.doc.pos_order_items.filter(
        item => !item.sent_to_kitchen && !item.cancelled
    );

    if (!itemsToSend.length) {
        frappe.msgprint({
            title: __("Informasi"),
            indicator: 'yellow',
            message: __('Semua item sudah dikirim ke dapur atau dibatalkan.')
        });
        return;
    }

    // Tampilkan konfirmasi dengan detail item
    const itemList = itemsToSend.map(
        item => `${item.qty}x ${item.item_name}`
    ).join('\n');

    frappe.confirm(
        `Kirim item berikut ke dapur?\n\n${itemList}`,
        () => {
            frappe.call({
                method: 'pos_restaurant_itb.api.create_kot.create_kot_from_pos_order',
                args: { 
                    pos_order_id: frm.doc.name 
                },
                freeze: true,
                freeze_message: __('Mengirim ke dapur...'),
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __(`✅ KOT dibuat: ${r.message}`),
                            indicator: 'green'
                        });
                    }
                },
                error: function(r) {
                    // Log error untuk debugging
                    console.error("KOT Error:", r);
                    
                    frappe.msgprint({
                        title: __('Error'),
                        indicator: 'red',
                        message: __(
                            'Gagal mengirim ke dapur. Detail:\n' +
                            (r.exc_message || r._server_messages || r.message || 'Unknown error')
                        )
                    });
                }
            });
        }
    );
}
