/**
 * POS Restaurant ITB - POS Order List
 * ---------------------------------
 * List view handler for POS Order document.
 * 
 * @file pos_order_list.js
 * @package pos_restaurant_itb
 * @copyright 2024 PT. Innovasi Terbaik Bangsa
 * @created 2025-04-06 08:20:37
 * @version 1.0.0
 * @author dannyaudian
 */

frappe.provide('pos_restaurant_itb.pos_order_list');

// Constants
const INACTIVE_STATUS = ["Final Billed", "Cancelled"];
const DEFAULT_REFRESH_INTERVAL = 30000; // 30 seconds

pos_restaurant_itb.pos_order_list = class POSOrderListHandler {
    constructor(listview) {
        this.listview = listview;
        this.user = frappe.session.user;
        this.isSystemManager = frappe.user.has_role("System Manager");
        this.setup();
    }

    async setup() {
        try {
            await this.setupFilters();
            this.setupAutoRefresh();
            this.setupCustomButtons();
            this.setupIndicators();
        } catch (error) {
            this.handleError(error);
        }
    }

    /**
     * Setup list filters based on user permissions
     */
    async setupFilters() {
        try {
            const branches = await this.getUserBranches();
            this.applyBranchFilters(branches);
            this.applyStatusFilter();
            
            // Log for monitoring
            console.log("Filters applied:", {
                user: this.user,
                branches: branches,
                timestamp: frappe.datetime.now_datetime()
            });
        } catch (error) {
            console.error("Filter Setup Error:", error);
            throw error;
        }
    }

    /**
     * Get user's authorized branches
     * @returns {Promise<string[]>} Array of branch names
     */
    async getUserBranches() {
        if (this.isSystemManager) return [];

        const result = await frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "User Permission",
                filters: {
                    user: this.user,
                    allow: "Branch"
                },
                fields: ["for_value"]
            }
        });

        return result.message?.map(p => p.for_value) || [];
    }

    /**
     * Apply branch filters based on user permissions
     * @param {string[]} branches - Array of authorized branches
     */
    applyBranchFilters(branches) {
        if (this.isSystemManager) return;

        if (branches.length === 1) {
            this.addFilter(["branch", "=", branches[0]]);
        } else if (branches.length > 1) {
            this.addFilter(["branch", "in", branches]);
        } else {
            frappe.show_alert({
                message: __("⚠️ Anda tidak memiliki akses ke cabang manapun"),
                indicator: 'red'
            });
        }
    }

    /**
     * Apply status filter to exclude inactive orders
     */
    applyStatusFilter() {
        this.addFilter(["status", "not in", INACTIVE_STATUS]);
    }

    /**
     * Add filter to the list view
     * @param {Array} filter - Filter array [field, operator, value]
     */
    addFilter(filter) {
        this.listview.filter_area.add([["POS Order", ...filter]]);
    }

    /**
     * Setup auto-refresh functionality
     */
    setupAutoRefresh() {
        if (this.refreshInterval) clearInterval(this.refreshInterval);

        this.refreshInterval = setInterval(() => {
            this.listview.refresh();
            this.showRefreshNotification();
        }, DEFAULT_REFRESH_INTERVAL);

        // Clear interval when leaving the page
        $(document).on('page-change', () => {
            if (this.refreshInterval) clearInterval(this.refreshInterval);
        });
    }

    /**
     * Setup custom buttons in the list view
     */
    setupCustomButtons() {
        // Add refresh button
        this.listview.page.add_inner_button(__('Refresh Now'), () => {
            this.listview.refresh();
            this.showRefreshNotification();
        });

        // Add export button for managers
        if (frappe.user.has_role(["System Manager", "Restaurant Manager"])) {
            this.listview.page.add_inner_button(__('Export Orders'), () => {
                this.exportOrders();
            });
        }
    }

    /**
     * Setup status indicators
     */
    setupIndicators() {
        this.listview.get_indicator = (doc) => {
            return this.getStatusIndicator(doc);
        };
    }

    /**
     * Get status indicator configuration
     * @param {Object} doc - Document object
     * @returns {Array} Indicator configuration [label, color]
     */
    getStatusIndicator(doc) {
        const indicators = {
            "Draft": ["orange", "docstatus,=,0"],
            "In Progress": ["blue", "status,=,In Progress"],
            "Ready for Billing": ["green", "status,=,Ready for Billing"],
            "Final Billed": ["gray", "status,=,Final Billed"],
            "Cancelled": ["red", "status,=,Cancelled"]
        };

        return [
            __(doc.status),
            indicators[doc.status]?.[0] || "gray",
            indicators[doc.status]?.[1] || ""
        ];
    }

    /**
     * Show refresh notification
     */
    showRefreshNotification() {
        frappe.show_alert({
            message: __("📋 Daftar order diperbarui"),
            indicator: 'green'
        }, 3);
    }

    /**
     * Export orders to CSV
     */
    async exportOrders() {
        try {
            const filters = this.listview.get_filters_for_args();
            
            const result = await frappe.call({
                method: "pos_restaurant_itb.api.export_orders",
                args: { filters: filters }
            });

            if (result.message) {
                window.open(result.message);
            }
        } catch (error) {
            this.handleError(error);
        }
    }

    /**
     * Handle errors
     * @param {Error} error - Error object
     */
    handleError(error) {
        console.error("POS Order List Error:", error);
        frappe.show_alert({
            message: __(`Error: ${error.message || "Something went wrong"}`),
            indicator: 'red'
        });
    }
}

// Initialize list view settings
frappe.listview_settings['POS Order'] = {
    onload(listview) {
        new pos_restaurant_itb.pos_order_list(listview);
    },

    refresh(listview) {
        // Add any refresh-specific logic here
    },

    formatters: {
        status(value) {
            const colors = {
                "Draft": "orange",
                "In Progress": "blue",
                "Ready for Billing": "green",
                "Final Billed": "gray",
                "Cancelled": "red"
            };
            return `<span class="indicator-pill ${colors[value] || 'gray'}">${value}</span>`;
        },
        
        total_amount(value) {
            return format_currency(value, frappe.defaults.get_default("currency"));
        }
    }
};