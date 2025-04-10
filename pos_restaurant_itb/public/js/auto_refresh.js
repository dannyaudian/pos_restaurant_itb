// POS Restaurant ITB Auto Refresh Script
frappe.provide("pos_restaurant_itb");

pos_restaurant_itb.setup_auto_refresh = function() {
    // Pages to auto-refresh
    const auto_refresh_pages = [
        "Kitchen-Display-Order",
        "POS-Order"
    ];
    
    // Check if current page should auto-refresh
    if (frappe.get_route() && frappe.get_route()[0] === "List" && 
        auto_refresh_pages.includes(frappe.get_route()[1])) {
        
        // Set up a 30-second refresh interval
        if (!window.pos_refresh_interval) {
            window.pos_refresh_interval = setInterval(function() {
                if (cur_list) cur_list.refresh();
            }, 30000); // 30 seconds
            
            console.log("Auto-refresh enabled for", frappe.get_route()[1]);
        }
    } else {
        // Clear interval if we navigate away
        if (window.pos_refresh_interval) {
            clearInterval(window.pos_refresh_interval);
            window.pos_refresh_interval = null;
        }
    }
};

// Set up page refresh on route change
$(document).on("page-change", function() {
    pos_restaurant_itb.setup_auto_refresh();
});