// pos_restaurant_itb/custom/pos_invoice/pos_invoice.js

frappe.ui.form.on('POS Invoice', {
  refresh(frm) {
    // Tombol: Load Order dari Waiter
    frm.add_custom_button("Load Order dari Waiter", () => {
      frappe.prompt([
        {
          label: "POS Order",
          fieldname: "pos_order",
          fieldtype: "Link",
          options: "POS Order",
          get_query: () => ({
            filters: {
              status: "Ready for Billing",
              branch: frm.doc.branch
            }
          })
        }
      ], async (values) => {
        const res = await frappe.call({
          method: "frappe.client.get",
          args: {
            doctype: "POS Order",
            name: values.pos_order
          }
        });

        const order = res.message;
        frm.doc.customer = order.customer;
        frm.doc.items = [];

        (order.pos_order_items || []).forEach(item => {
          frm.add_child("items", {
            item_code: item.item_code,
            qty: item.qty,
            rate: item.rate,
            amount: item.amount
          });
        });

        frm.refresh_field("customer");
        frm.refresh_field("items");

        // Simpan info referensi
        frm.doc.notes = `Order dari Waiter: ${order.name}`;
        frm.refresh_field("notes");
      });
    });

    // Tombol: Print Struk
    frm.add_custom_button("Print Struk", () => {
      frappe.call({
        method: "pos_restaurant_itb.api.print_receipt",
        args: { name: frm.doc.name },
        callback: function(r) {
          if (r.message) {
            const win = window.open();
            win.document.write(r.message);
            win.document.close();
          }
        }
      });
    });
  },

  validate(frm) {
    if (!frm.doc.customer) {
      frappe.throw("Customer belum dipilih.");
    }
    if (!frm.doc.items || frm.doc.items.length === 0) {
      frappe.throw("Item masih kosong.");
    }
  },

  after_save(frm) {
    if (frm.doc.notes && frm.doc.notes.includes("Order dari Waiter")) {
      const order_id = frm.doc.notes.split(":")[1].trim();
      frappe.call({
        method: "frappe.client.set_value",
        args: {
          doctype: "POS Order",
          name: order_id,
          fieldname: "status",
          value: "Billed"
        }
      });
    }
  }
});
