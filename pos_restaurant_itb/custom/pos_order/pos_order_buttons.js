frappe.ui.form.on('POS Order', {
    refresh(frm) {
        const { docstatus, status } = frm.doc;
        const isDraft = docstatus === 0;

        if (isDraft && status === "Draft") {
            addKitchenButton(frm, 'Kirim ke Dapur');
        }

        if (isDraft && status === "In Progress") {
            addKitchenButton(frm, 'Kirim Tambahan ke Dapur');
        }

        addPrintButton(frm, 'Print KOT', 'pos_restaurant_itb.api.print_kot');
        addPrintButton(frm, 'Print Receipt', 'pos_restaurant_itb.api.print_receipt');

        addCancelItemButton(frm);

        if (["In Progress", "Ready for Billing"].includes(status)) {
            addMarkServedButtons(frm);
        }
    }
});

// 🔘 Tombol Kirim ke Dapur
function addKitchenButton(frm, label) {
    const btn = frm.add_custom_button(__(label), async () => {
        const isDraftStatus = frm.doc.docstatus === 0 && frm.doc.status === "Draft";

        if (isDraftStatus) {
            frappe.msgprint({
                title: __("Validasi"),
                indicator: 'yellow',
                message: __('POS Order dalam status Draft. Menyimpan terlebih dahulu sebelum mengirim ke dapur...')
            });
            await frm.save();
        }

        sendToKitchen(frm);
    }, __("Actions"));

    btn?.addClass?.("btn-primary");
}

// 🖨️ Tombol Print
function addPrintButton(frm, label, method) {
    frm.add_custom_button(__(label), () => {
        frappe.call({
            method,
            args: { name: frm.doc.name },
            callback(r) {
                if (r.message) {
                    const win = window.open('', '_blank');
                    win?.document.write(r.message);
                    win?.document.close();
                } else {
                    frappe.msgprint(__('Tidak ada output untuk dicetak.'));
                }
            }
        });
    }, __("Actions"));
}

// ❌ Cancel Item
function addCancelItemButton(frm) {
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
}

// ✅ Mark as Served (per item & semua)
function addMarkServedButtons(frm) {
    const grid = frm.fields_dict.pos_order_items.grid;

    // Per item
    grid.add_custom_button(__('Mark as Served'), () => {
        const selected = grid.get_selected();

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

// 🔄 Kirim ke Dapur
function sendToKitchen(frm) {
    const items = frm.doc.pos_order_items || [];

    if (!items.length) {
        return frappe.msgprint({
            title: __("Validasi"),
            indicator: 'red',
            message: __('Tidak ada item untuk dikirim ke dapur.')
        });
    }

    const itemsToSend = items.filter(item => !item.sent_to_kitchen && !item.cancelled);

    if (!itemsToSend.length) {
        return frappe.msgprint({
            title: __("Informasi"),
            indicator: 'yellow',
            message: __('Semua item sudah dikirim ke dapur atau dibatalkan.')
        });
    }

    const itemList = itemsToSend.map(item => `${item.qty}x ${item.item_name}`).join('\n');

    frappe.confirm(
        `Kirim item berikut ke dapur?\n\n${itemList}`,
        () => {
            frappe.call({
                method: 'pos_restaurant_itb.api.create_kot.create_kot_from_pos_order',
                args: { pos_order_id: frm.doc.name },
                freeze: true,
                freeze_message: __('Mengirim ke dapur...'),
                callback(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __(`✅ KOT dibuat: ${r.message}`),
                            indicator: 'green'
                        });
                    }
                },
                error(r) {
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
