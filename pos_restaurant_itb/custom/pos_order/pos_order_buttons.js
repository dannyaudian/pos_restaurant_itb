frappe.ui.form.on('POS Order', {
    refresh(frm) {
        // Tombol "Kirim ke Dapur" saat Draft
        if (frm.doc.docstatus === 0 && frm.doc.status === "Draft") {
            frm.add_custom_button(__('Kirim ke Dapur'), () => {
                frappe.call({
                    method: 'pos_restaurant_itb.api.create_kot.create_kot_from_pos_order',
                    args: { pos_order_id: frm.doc.name },
                    callback: function (r) {
                        if (r.message) {
                            frappe.show_alert("✅ Pesanan dikirim ke dapur.");
                            frm.reload_doc();
                        }
                    }
                });
            }, __("Actions"));
        }

        // Tombol "Kirim Tambahan ke Dapur" saat In Progress
        if (frm.doc.docstatus === 0 && frm.doc.status === "In Progress") {
            frm.add_custom_button(__('Kirim Tambahan ke Dapur'), () => {
                frappe.call({
                    method: 'pos_restaurant_itb.api.create_kot.create_kot_from_pos_order',
                    args: { pos_order_id: frm.doc.name },
                    callback: function (r) {
                        if (r.message) {
                            frappe.show_alert("✅ Item tambahan dikirim ke dapur.");
                            frm.reload_doc();
                        }
                    }
                });
            }, __("Actions"));
        }

        // Tombol Print KOT
        frm.add_custom_button(__('Print KOT'), () => {
            frappe.call({
                method: 'pos_restaurant_itb.api.print_kot',
                args: { name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        const win = window.open();
                        win.document.write(r.message);
                        win.document.close();
                    }
                }
            });
        }, __("Actions"));

        // Tombol Print Receipt
        frm.add_custom_button(__('Print Receipt'), () => {
            frappe.call({
                method: 'pos_restaurant_itb.api.print_receipt',
                args: { name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        const win = window.open();
                        win.document.write(r.message);
                        win.document.close();
                    }
                }
            });
        }, __("Actions"));

        // Tombol Cancel Item (per baris)
        frm.fields_dict.pos_order_items.grid.add_custom_button(__('Cancel Item'), function () {
            const selected = frm.fields_dict.pos_order_items.grid.get_selected();
            if (!selected.length) {
                frappe.msgprint("Pilih item terlebih dahulu.");
                return;
            }

            const row = selected[0];
            frappe.prompt(
                [
                    {
                        label: 'Alasan Pembatalan',
                        fieldname: 'cancellation_note',
                        fieldtype: 'Small Text',
                        reqd: 1
                    }
                ],
                (values) => {
                    frappe.call({
                        method: "pos_restaurant_itb.api.sendkitchenandcancel.cancel_pos_order_item",
                        args: {
                            item_name: row.name,
                            reason: values.cancellation_note
                        },
                        callback: function (res) {
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

        // Tombol Mark as Served per baris
        if (["In Progress", "Ready for Billing"].includes(frm.doc.status)) {
            frm.fields_dict.pos_order_items.grid.add_custom_button(__('Mark as Served'), function () {
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
                    callback: function (res) {
                        if (res.message) {
                            frappe.show_alert("✅ Item ditandai sebagai 'Served'.");
                            frm.reload_doc();
                        }
                    }
                });
            });

            // Tombol Mass Update Semua ke Served
            frm.add_custom_button(__('✔️ Mark Semua as Served'), () => {
                frappe.confirm(
                    "Yakin ingin menandai semua item sebagai 'Served'?",
                    () => {
                        frappe.call({
                            method: "pos_restaurant_itb.api.sendkitchenandcancel.mark_all_served",
                            args: {
                                pos_order_id: frm.doc.name
                            },
                            callback: function (res) {
                                if (res.message) {
                                    frappe.show_alert("✅ Semua item telah ditandai sebagai 'Served'.");
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __("Actions"));
        }
    }
});
