
frappe.pages['pos'].on_page_load = function(wrapper) {
  frappe.ui.form.on('POS Invoice', {
    refresh(frm) {
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
          frm.refresh_field("items");
        });
      });

      frm.add_custom_button("Print Struk", () => {
        frappe.call({
          method: "restaurant_pos_core.api.print_receipt",
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
    }
  });
};
