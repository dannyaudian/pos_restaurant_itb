frappe.listview_settings['Kitchen Station'] = {
    onload: function (listview) {
      // ⏳ Filter otomatis hanya untuk status Queued dan Cooking
      listview.filter_area.add([
        ['kot_status', 'in', ['Queued', 'Cooking']]
      ]);
  
      // 🔁 Auto-refresh list setiap 10 detik
      const refresh_interval = 10000; // ms
  
      const interval = setInterval(() => {
        // Hanya refresh jika masih di halaman list Kitchen Station
        if (frappe.get_route()[1] === "Kitchen Station") {
          listview.refresh();
        } else {
          clearInterval(interval);
        }
      }, refresh_interval);
    }
  };
  