frappe.listview_settings['Kitchen Display Order'] = {
    onload: function (listview) {
      listview.filter_area.add([
        ['status', 'in', ['New', 'In Progress', 'Ready']]
      ]);
  
      const interval = setInterval(() => {
        if (frappe.get_route()[1] === "Kitchen Display Order") {
          listview.refresh();
        } else {
          clearInterval(interval);
        }
      }, 10000); // refresh setiap 10 detik
    }
  };
  