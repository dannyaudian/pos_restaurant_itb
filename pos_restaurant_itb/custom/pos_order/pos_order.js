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

        // 📛 Filter meja berdasarkan ketersediaan
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
        }
    }
});

frappe.ui.form.on('POS Order Item', {
    item_code: function (frm, cdt, cdn)_
