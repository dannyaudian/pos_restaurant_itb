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

function addKitchenButton(frm, label) {
    const btn = frm.add_custom_button(__(label), async () => {
        const needsOrderId = frm.doc.docstatus === 0 && !frm.doc.order_id && frm.doc.branch;

        if (needsOrderId) {
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
    }, __("Actions"));

    if (btn?.addClass) {
        btn.addClass("btn-primary");
    }
}

function addPrintButton(frm, label, method) {
    frm.add_custom_button(__(label), () => {
        frappe.call({
            method,
            args: { name: frm.doc.name },
            callback: (r) => {
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

        frappe.prompt([
            {
                label: 'Alasan Pembatalan',
                fieldname: 'cancellation_note',
                fieldtype: 'Small Text',
                reqd: 1
            }
        ], (values) => {
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
                // Submit jika masih draft
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
            } catch (r) {
                console.error("KOT Error:", r);
                frappe.msgprint({
                    title: __('Error'),
                    indicator: 'red',
                    message: `Gagal mengirim ke dapur. Detail:\n${r?.message || r._server_messages || 'Unknown error'}`
                });
            }
        }
    );
}
