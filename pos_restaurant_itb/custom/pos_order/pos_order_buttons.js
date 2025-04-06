/**
 * POS Restaurant ITB - POS Order Buttons
 * ------------------------------------
 * Custom buttons handler for POS Order form.
 * 
 * @file pos_order_buttons.js
 * @package pos_restaurant_itb
 * @copyright 2024 PT. Innovasi Terbaik Bangsa
 * @created 2025-04-06 08:20:37
 * @version 1.0.0
 * @author dannyaudian
 */

frappe.provide('pos_restaurant_itb.pos_order');

// Constants
const BUTTON_GROUPS = {
    ACTIONS: __("Actions")
};

const STATUS = {
    DRAFT: "Draft",
    IN_PROGRESS: "In Progress",
    READY_FOR_BILLING: "Ready for Billing"
};

// Button Handlers
pos_restaurant_itb.pos_order = {
    /**
     * Send items to kitchen
     * @param {object} frm - The form object
     */
    async sendToKitchen(frm) {
        // Validations
        if (!this.validateItems(frm)) return;
        
        const itemsToSend = this.getItemsToSend(frm);
        if (!itemsToSend.length) {
            this.showMessage('warning', 'Semua item sudah dikirim ke dapur atau dibatalkan.');
            return;
        }

        // Show confirmation
        const itemList = this.formatItemList(itemsToSend);
        if (await this.confirmSendToKitchen(itemList)) {
            this.processKotCreation(frm, itemsToSend);
        }
    },

    /**
     * Print KOT document
     * @param {object} frm - The form object
     */
    printKOT(frm) {
        this.callPrintAPI('print_kot', frm.doc.name);
    },

    /**
     * Print receipt document
     * @param {object} frm - The form object
     */
    printReceipt(frm) {
        this.callPrintAPI('print_receipt', frm.doc.name);
    },

    /**
     * Cancel selected item
     * @param {object} frm - The form object
     */
    async cancelItem(frm) {
        const selected = frm.fields_dict.pos_order_items.grid.get_selected();
        if (!selected.length) {
            this.showMessage('warning', 'Pilih item terlebih dahulu.');
            return;
        }

        const values = await this.showCancellationDialog();
        if (values) {
            this.processCancellation(frm, selected[0], values.cancellation_note);
        }
    },

    /**
     * Mark item as served
     * @param {object} frm - The form object
     * @param {boolean} allItems - Whether to mark all items or just selected
     */
    async markAsServed(frm, allItems = false) {
        if (allItems) {
            if (await this.confirmMarkAllServed()) {
                this.processMarkAllServed(frm);
            }
            return;
        }

        const selected = frm.fields_dict.pos_order_items.grid.get_selected();
        if (!selected.length) {
            this.showMessage('warning', 'Pilih item terlebih dahulu.');
            return;
        }

        this.processMarkAsServed(frm, selected[0]);
    },

    // Helper Methods
    validateItems(frm) {
        if (!frm.doc.pos_order_items?.length) {
            this.showMessage('error', 'Tidak ada item untuk dikirim ke dapur.');
            return false;
        }
        return true;
    },

    getItemsToSend(frm) {
        return frm.doc.pos_order_items.filter(
            item => !item.sent_to_kitchen && !item.cancelled
        );
    },

    formatItemList(items) {
        return items.map(item => `${item.qty}x ${item.item_name}`).join('\n');
    },

    async confirmSendToKitchen(itemList) {
        return new Promise(resolve => {
            frappe.confirm(
                `Kirim item berikut ke dapur?\n\n${itemList}`,
                () => resolve(true),
                () => resolve(false)
            );
        });
    },

    async showCancellationDialog() {
        return new Promise(resolve => {
            frappe.prompt(
                [{
                    label: 'Alasan Pembatalan',
                    fieldname: 'cancellation_note',
                    fieldtype: 'Small Text',
                    reqd: 1
                }],
                values => resolve(values),
                'Konfirmasi Pembatalan',
                'Batalkan'
            );
        });
    },

    async confirmMarkAllServed() {
        return new Promise(resolve => {
            frappe.confirm(
                "Yakin ingin menandai semua item sebagai 'Served'?",
                () => resolve(true),
                () => resolve(false)
            );
        });
    },

    showMessage(type, message) {
        const config = {
            title: __(type === 'error' ? 'Error' : 'Informasi'),
            indicator: type === 'error' ? 'red' : type === 'warning' ? 'yellow' : 'green',
            message: __(message)
        };
        
        frappe.msgprint(config);
    },

    // API Calls
    async processKotCreation(frm) {
        try {
            const response = await frappe.call({
                method: 'pos_restaurant_itb.api.create_kot.create_kot_from_pos_order',
                args: { pos_order_id: frm.doc.name },
                freeze: true,
                freeze_message: __('Mengirim ke dapur...')
            });

            if (response.message) {
                frm.reload_doc();
                frappe.show_alert({
                    message: __(`✅ KOT dibuat: ${response.message}`),
                    indicator: 'green'
                });
            }
        } catch (error) {
            console.error("KOT Error:", error);
            this.showMessage('error', 
                `Gagal mengirim ke dapur. Detail:\n${error.message || 'Unknown error'}`
            );
        }
    },

    async callPrintAPI(method, name) {
        try {
            const response = await frappe.call({
                method: `pos_restaurant_itb.api.${method}`,
                args: { name }
            });

            if (response.message) {
                const win = window.open();
                win.document.write(response.message);
                win.document.close();
            }
        } catch (error) {
            this.showMessage('error', `Gagal mencetak dokumen: ${error.message}`);
        }
    },

    async processCancellation(frm, item, reason) {
        try {
            const response = await frappe.call({
                method: "pos_restaurant_itb.api.sendkitchenandcancel.cancel_pos_order_item",
                args: {
                    item_name: item.name,
                    reason: reason
                }
            });

            if (response.message) {
                frappe.show_alert(response.message);
                frm.reload_doc();
            }
        } catch (error) {
            this.showMessage('error', `Gagal membatalkan item: ${error.message}`);
        }
    },

    async processMarkAsServed(frm, item) {
        try {
            const response = await frappe.call({
                method: "pos_restaurant_itb.api.update_kot_item_status",
                args: {
                    order: frm.doc.name,
                    item_code: item.item_code,
                    status: "Served"
                }
            });

            if (response.message) {
                frappe.show_alert("✅ Item ditandai sebagai 'Served'.");
                frm.reload_doc();
            }
        } catch (error) {
            this.showMessage('error', `Gagal menandai item: ${error.message}`);
        }
    },

    async processMarkAllServed(frm) {
        try {
            const response = await frappe.call({
                method: "pos_restaurant_itb.api.sendkitchenandcancel.mark_all_served",
                args: { pos_order_id: frm.doc.name }
            });

            if (response.message) {
                frappe.show_alert("✅ Semua item telah ditandai sebagai 'Served'.");
                frm.reload_doc();
            }
        } catch (error) {
            this.showMessage('error', `Gagal menandai semua item: ${error.message}`);
        }
    }
};

// Form Event Handler
frappe.ui.form.on('POS Order', {
    refresh(frm) {
        const isDraft = frm.doc.docstatus === 0;
        const status = frm.doc.status;
        const handlers = pos_restaurant_itb.pos_order;

        // Kitchen Buttons
        if (isDraft && status === STATUS.DRAFT) {
            frm.add_custom_button(
                __('Kirim ke Dapur'),
                () => handlers.sendToKitchen(frm),
                BUTTON_GROUPS.ACTIONS
            );
        }

        if (isDraft && status === STATUS.IN_PROGRESS) {
            frm.add_custom_button(
                __('Kirim Tambahan ke Dapur'),
                () => handlers.sendToKitchen(frm),
                BUTTON_GROUPS.ACTIONS
            );
        }

        // Print Buttons
        frm.add_custom_button(
            __('Print KOT'),
            () => handlers.printKOT(frm),
            BUTTON_GROUPS.ACTIONS
        );

        frm.add_custom_button(
            __('Print Receipt'),
            () => handlers.printReceipt(frm),
            BUTTON_GROUPS.ACTIONS
        );

        // Cancel Item Button
        frm.fields_dict.pos_order_items.grid.add_custom_button(
            __('Cancel Item'),
            () => handlers.cancelItem(frm)
        );

        // Served Buttons
        if ([STATUS.IN_PROGRESS, STATUS.READY_FOR_BILLING].includes(status)) {
            frm.fields_dict.pos_order_items.grid.add_custom_button(
                __('Mark as Served'),
                () => handlers.markAsServed(frm)
            );

            frm.add_custom_button(
                __('✔️ Mark Semua as Served'),
                () => handlers.markAsServed(frm, true),
                BUTTON_GROUPS.ACTIONS
            );
        }
    }
});