frappe.listview_settings['Kitchen Display Order'] = {
  onload(listview) {
    // ✅ Tambahkan filter default jika belum ada
    if (listview && listview.filter_area) {
      listview.filter_area.add([
        ['status', 'in', ['New', 'In Progress', 'Ready']]
      ]);
    }

    // ✅ Hindari duplikasi interval
    if (!listview.kitchen_display_refresh_interval) {
      listview.kitchen_display_refresh_interval = setInterval(() => {
        const route = frappe.get_route();
        if (route && route[1] === "Kitchen Display Order") {
          listview.refresh();
        } else {
          clearInterval(listview.kitchen_display_refresh_interval);
          listview.kitchen_display_refresh_interval = null;
        }
      }, 10000);
    }
  }
};
