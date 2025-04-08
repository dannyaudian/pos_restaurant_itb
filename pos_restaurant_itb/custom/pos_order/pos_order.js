frappe.ui.form.on('POS Order', {
    table: function (frm) {
        if (!frm.doc.table) return;

        frappe.db.get_value('POS Table', frm.doc.table, 'branch', function (r) {
            if (r?.branch) {
                frm.set_value('branch', r.branch);

                // Cek apakah meja masih tersedia via API
                frappe.call({
                    method: "pos_restaurant_itb.api.get_available_tables",
                    args: { branch: r.branch },
                    callback: function (res) {
                        const available_tables = res.message || [];
                        const is_available = available_tables.some(t => t.name === frm.doc.table);

                        if (!is_available) {
                            frappe.msgprint(`❌ Meja ${frm.doc.table} sedang digunakan. Silakan pilih meja lain.`);
                            frm.set_value("table", null);
                            return;
                        }

                        // ✅ Jika tersedia → generate order ID
                        frappe.call({
                            method: "pos_restaurant_itb.api.get_new_order_id",
                            args: { branch: r.branch },
                            callback: function (res) {
                                if (res?.message) {
                                    frm.set_value("order_id", res.message);
                                }
                            }
                        });
                    }
                });
            }
        });
    },

    onload: function (frm) {
        // 🔐 Filter cabang sesuai permission user
        frm.set_query("branch", () => {
            if (frappe.user.has_role("System Manager")) return {};

            const branches = frappe.user.get_perm("Branch") || [];
            if (!branches.length) {
                frappe.msgprint(__("⚠️ Anda tidak memiliki akses ke cabang manapun."));
            }

            return {
                filters: { name: ["in", branches] }
            };
        });

        // 📛 Filter meja berdasarkan ketersediaan (via API)
        frm.set_query("table", () => {
            if (!frm.doc.branch) {
              frappe.msgprint("Pilih cabang terlebih dahulu.");
              return { filters: { name: ["=", ""] } };
            }

            return {
              filters: [
                ["POS Table", "branch", "=", frm.doc.branch],
                ["POS Table", "is_active", "=", 1]
              ]
            };
        });

        // 🧾 Filter item template saja
        frm.fields_dict.pos_order_items.grid.get_field('item_code').get_query = () => ({
            filters: {
                variant_of: ["is", "not set"],
                is_sales_item: 1,
                disabled: 0
            }
        });
    },

    validate: function (frm) {
        if (!frm.doc.branch) {
            frappe.msgprint("Cabang harus dipilih.");
            frappe.validated = false;
            return;
        }

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Kitchen Station",
                filters: {
                    branch: frm.doc.branch,
                    status: "Active"
                },
                limit_page_length: 1
            },
            async: false,
            callback: function (res) {
                if (!res.message.length) {
                    frappe.msgprint("❌ Tidak ada Kitchen Station aktif di cabang ini.");
                    frappe.validated = false;
                }
            }
        });
    }
});

frappe.ui.form.on('POS Order Item', {
    item_code: function (frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.item_code) return;

        // Cek apakah item punya varian
        frappe.db.get_value("Item", row.item_code, "has_variants", function (r) {
            if (r?.has_variants) {
                frappe.call({
                    method: "pos_restaurant_itb.api.get_attributes_for_item",
                    args: { item_code: row.item_code },
                    callback: function (res) {
                        if (!res.message) return;

                        const fields = res.message.map(attr => ({
                            label: attr.attribute,
                            fieldname: attr.attribute,
                            fieldtype: "Select",
                            options: (attr.values || []).join("\n"),
                            reqd: 1
                        }));

                        const d = new frappe.ui.Dialog({
                            title: 'Pilih Atribut',
                            fields: fields,
                            primary_action_label: 'Simpan',
                            primary_action(values) {
                                const item_row = locals[row.doctype][row.name];
                                item_row.dynamic_attributes = [];

                                for (const [key, value] of Object.entries(values)) {
                                    item_row.dynamic_attributes.push({
                                        attribute_name: key,
                                        attribute_value: value
                                    });
                                }

                                frm.refresh_field("pos_order_items");
                                frappe.show_alert("✔️ Atribut ditambahkan.");
                                resolve_variant_after_save(frm, row, values);
                                d.hide();
                            }
                        });

                        d.show();
                    }
                });
            }
        });

        // Ambil harga dari price list
        const price_list = frm.doc.selling_price_list || 'Standard Selling';
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Item Price",
                filters: {
                    item_code: row.item_code,
                    price_list: price_list
                },
                fields: ["price_list_rate"],
                limit_page_length: 1
            },
            callback: function (res) {
                const rate = res.message?.[0]?.price_list_rate || 0;
                frappe.model.set_value(cdt, cdn, 'rate', rate);
                if (rate === 0) {
                    frappe.msgprint(__('Harga tidak ditemukan di Price List: ' + price_list));
                }
            }
        });
    },

    qty: update_item_amount_and_total,
    rate: update_item_amount_and_total
});

function resolve_variant_after_save(frm, row, attributes) {
    const attr_array = Object.entries(attributes).map(([key, value]) => ({
        attribute_name: key,
        attribute_value: value
    }));

    frappe.call({
        method: "pos_restaurant_itb.api.resolve_variant",
        args: {
            template: row.item_code,
            attributes: attr_array
        },
        callback: function (r) {
            if (r.message) {
                frappe.model.set_value(row.doctype, row.name, 'item_code', r.message.item_code);
                frappe.model.set_value(row.doctype, row.name, 'item_name', r.message.item_name);
                frappe.model.set_value(row.doctype, row.name, 'rate', r.message.rate);

                frappe.show_alert({
                    message: `🔄 Diganti ke Variant: ${r.message.item_name}`,
                    indicator: 'green'
                });
            }
        }
    });
}

function update_item_amount_and_total(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row) return;

    const qty = row.qty || 0;
    const rate = row.rate || 0;
    const amount = qty * rate;

    frappe.model.set_value(cdt, cdn, "amount", amount);

    let total = 0;
    (frm.doc.pos_order_items || []).forEach(item => {
        total += item.amount || 0;
    });

    frm.set_value("total_amount", total);
    frm.refresh_field("total_amount");
}
