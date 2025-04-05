frappe.listview_settings['POS Order'] = {
    onload: function(listview) {
        const user = frappe.session.user;

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "User Permission",
                filters: {
                    user: user,
                    allow: "Branch"
                },
                fields: ["for_value"]
            },
            callback: function(res) {
                const branches = res.message?.map(p => p.for_value) || [];

                // Jika bukan System Manager
                if (!frappe.user.has_role("System Manager")) {
                    if (branches.length === 1) {
                        listview.filter_area.add([[ "POS Order", "branch", "=", branches[0] ]]);
                    } else if (branches.length > 1) {
                        listview.filter_area.add([[ "POS Order", "branch", "in", branches ]]);
                    }
                }

                // Tambahkan filter status aktif
                listview.filter_area.add([[ "POS Order", "status", "not in", ["Final Billed", "Cancelled"] ]]);
            }
        });
    }
};
