/**
 * POS Restaurant ITB - Auto Refresh
 * --------------------------------
 * Auto refresh functionality for POS interfaces.
 * 
 * Created: 2025-04-06 08:33:29
 * Author: dannyaudian 
 */

frappe.provide('pos_restaurant_itb.auto_refresh');

pos_restaurant_itb.auto_refresh = class AutoRefresh {
    constructor(opts) {
        $.extend(this, opts);
        this.setup();
    }

    setup() {
        this.refreshInterval = 30000; // 30 seconds
        this.setupRefreshTimer();
        this.setupEventHandlers();
    }

    setupRefreshTimer() {
        if (this.timer) clearInterval(this.timer);

        this.timer = setInterval(() => {
            this.refreshPage();
        }, this.refreshInterval);
    }

    setupEventHandlers() {
        // Clear interval when leaving page
        $(document).on('page-change', () => {
            if (this.timer) clearInterval(this.timer);
        });

        // Add refresh button
        if (cur_page.page.page_actions) {
            cur_page.page.add_inner_button(__('Refresh Now'), () => {
                this.refreshPage(true);
            });
        }
    }

    async refreshPage(showNotification = false) {
        try {
            if (cur_list) {
                await cur_list.refresh();
            } else if (cur_frm) {
                await cur_frm.reload_doc();
            }

            if (showNotification) {
                frappe.show_alert({
                    message: __('Page refreshed'),
                    indicator: 'green'
                });
            }
        } catch (error) {
            console.error("Refresh Error:", error);
        }
    }
}

// Initialize auto refresh for relevant pages
$(document).ready(function() {
    if (frappe.get_route_str().includes('pos-restaurant')) {
        new pos_restaurant_itb.auto_refresh();
    }
});