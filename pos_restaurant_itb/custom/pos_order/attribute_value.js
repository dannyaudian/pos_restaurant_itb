frappe.ui.form.on('POS Dynamic Attribute', {
    attribute_name: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.attribute_name) return;

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Item Attribute Value",
                filters: {
                    parent: row.attribute_name
                },
                fields: ["name"]
            },
            callback: function(r) {
                if (r.message) {
                    let values = r.message.map(i => i.name).join('\n');
                    frappe.meta.get_docfield("POS Dynamic Attribute", "attribute_value", frm.doc.name).options = values;
                }
            }
        });
    }
});
