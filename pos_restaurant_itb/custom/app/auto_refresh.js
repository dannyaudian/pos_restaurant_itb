frappe.listview_settings['Kitchen Display Order'] = {
    onload(listview) {
      // Set default filter (optional)
      listview.filter_area.add([
        ['status', 'in', ['New', 'In Progress', 'Ready']]
      ]);
  
      // Auto-refresh setiap 10 detik jika masih di halaman ini
      const interval = setInterval(() => {
        const route = frappe.get_route();
        if (route && route[1] === "Kitchen Display Order") {
          listview.refresh();
        } else {
          clearInterval(interval); // stop jika user berpindah halaman
        }
      }, 10000);
    }
  };
  