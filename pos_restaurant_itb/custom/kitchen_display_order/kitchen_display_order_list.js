frappe.listview_settings['Kitchen Display Order'] = {
  onload: function (listview) {
    // Filter hanya status: New, In Progress, Ready
    listview.filter_area.add([
      ['status', 'in', ['New', 'In Progress', 'Ready']]
    ]);

    // Filter hanya KOT dari POS Order yang belum Paid
    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "POS Order",
        filters: {
          status: ["!=", "Paid"]
        },
        fields: ["name"]
      },
      callback: function (res) {
        const active_orders = res.message.map(o => o.name);
        if (active_orders.length > 0) {
          listview.filter_area.add([
            ['kot_id', 'in', active_orders]
          ]);
        } else {
          // Kalau tidak ada yang aktif, tetap tambahkan filter kosong agar tidak tampil semua
          listview.filter_area.add([
            ['kot_id', '=', '']
          ]);
        }
      }
    });

    // Auto-refresh setiap 10 detik
    const interval = setInterval(() => {
      if (frappe.get_route()[1] === "Kitchen Display Order") {
        listview.refresh();
      } else {
        clearInterval(interval);
      }
    }, 10000);
  },

  formatters: {
    table_number(value) {
      return `<b style="font-size: 16px;">🍽️ ${value}</b>`;
    },
    status(value) {
      const color = {
        "New": "orange",
        "In Progress": "blue",
        "Ready": "green",
        "Served": "green"
      }[value] || "dark";
      return `<span class="indicator ${color}">${value}</span>`;
    }
  }
};
