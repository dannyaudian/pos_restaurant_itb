// Bridge between HTML UI and Frappe framework
class POSOrderBridge {
    constructor() {
        this.frm = null;
        this.initializeBridge();
    }

    initializeBridge() {
        // Initialize Select2
        $('#table, #branch, #customer, #modal_item_code').select2({
            width: '100%'
        });

        // Handle table selection
        $('#table').on('change', (e) => {
            if (!e.target.value) return;
            
            frappe.db.get_value('POS Table', e.target.value, 'branch', (r) => {
                if (r?.branch) {
                    $('#branch').val(r.branch).trigger('change');
                    this.checkTableAvailability(r.branch, e.target.value);
                }
            });
        });

        // Handle branch filtering
        this.setupBranchFilter();
        
        // Handle table filtering
        this.setupTableFilter();
        
        // Handle item filtering
        this.setupItemFilter();
        
        // Setup event handlers
        this.setupEventHandlers();
    }

    setupBranchFilter() {
        if (frappe.user.has_role("System Manager")) {
            this.fetchAllBranches();
        } else {
            this.fetchUserBranches();
        }
    }

    setupTableFilter() {
        $('#branch').on('change', (e) => {
            if (!e.target.value) {
                $('#table').html('<option value="">Select Table</option>').trigger('change');
                return;
            }

            frappe.db.get_list('POS Table', {
                filters: {
                    branch: e.target.value,
                    is_active: 1
                },
                fields: ['name', 'table_number']
            }).then(tables => {
                const options = tables.map(t => 
                    `<option value="${t.name}">${t.table_number}</option>`
                );
                $('#table').html('<option value="">Select Table</option>' + options.join('')).trigger('change');
            });
        });
    }

    setupItemFilter() {
        $('#modal_item_code').select2({
            ajax: {
                url: '/api/method/frappe.client.get_list',
                data: function (params) {
                    return {
                        doctype: 'Item',
                        filters: {
                            variant_of: ['is', 'not set'],
                            is_sales_item: 1,
                            disabled: 0,
                            name: ['like', `%${params.term}%`]
                        },
                        fields: ['name', 'item_name']
                    };
                },
                processResults: function (data) {
                    return {
                        results: data.message.map(item => ({
                            id: item.name,
                            text: `${item.name} - ${item.item_name}`
                        }))
                    };
                }
            }
        });
    }

    setupEventHandlers() {
        // Handle item selection
        $('#modal_item_code').on('select2:select', (e) => {
            const itemCode = e.target.value;
            if (!itemCode) return;

            // Check for variants
            frappe.db.get_value('Item', itemCode, 'has_variants', (r) => {
                if (r?.has_variants) {
                    this.showAttributeDialog(itemCode);
                } else {
                    this.fetchItemPrice(itemCode);
                }
            });
        });

        // Handle Send to Kitchen
        $('#send_to_kitchen').click(() => {
            if (this.validateBeforeSend()) {
                this.sendToKitchen();
            }
        });

        // Handle Print KOT
        $('#print_kot').click(() => {
            this.printKOT();
        });

        // Handle Print Receipt
        $('#print_receipt').click(() => {
            this.printReceipt();
        });

        // Handle item cancellation
        $(document).on('click', '.cancel-item', (e) => {
            const row = $(e.target).closest('tr');
            this.showCancelItemDialog(row);
        });

        // Handle Mark as Served
        $(document).on('click', '.serve-item', (e) => {
            const row = $(e.target).closest('tr');
            this.showServeItemDialog(row);
        });
    }

    // Utility functions
    checkTableAvailability(branch, table) {
        frappe.call({
            method: "pos_restaurant_itb.api.get_available_tables",
            args: { branch: branch },
            callback: (res) => {
                const available_tables = res.message || [];
                const is_available = available_tables.some(t => t.name === table);

                if (!is_available) {
                    frappe.msgprint(`❌ Meja ${table} sedang digunakan. Silakan pilih meja lain.`);
                    $('#table').val('').trigger('change');
                    return;
                }

                // Generate order ID
                this.generateOrderId(branch);
            }
        });
    }

    generateOrderId(branch) {
        frappe.call({
            method: "pos_restaurant_itb.api.get_new_order_id",
            args: { branch: branch },
            callback: (res) => {
                if (res?.message) {
                    $('#order_id').val(res.message);
                }
            }
        });
    }

    showAttributeDialog(itemCode) {
        frappe.call({
            method: "pos_restaurant_itb.api.get_attributes_for_item",
            args: { item_code: itemCode },
            callback: (res) => {
                if (!res.message) return;
                
                const container = $('#dynamic_attributes_container');
                container.empty();

                res.message.forEach(attr => {
                    const select = `
                        <div class="mb-3">
                            <label class="form-label required-field">${attr.attribute}</label>
                            <select class="form-select dynamic-attribute" data-name="${attr.attribute}">
                                <option value="">Select ${attr.attribute}</option>
                                ${attr.values.map(v => `<option value="${v}">${v}</option>`).join('')}
                            </select>
                        </div>
                    `;
                    container.append(select);
                });
            }
        });
    }

    fetchItemPrice(itemCode) {
        const priceList = 'Standard Selling'; // Or get from settings
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Item Price",
                filters: {
                    item_code: itemCode,
                    price_list: priceList
                },
                fields: ["price_list_rate"],
                limit_page_length: 1
            },
            callback: (res) => {
                const rate = res.message?.[0]?.price_list_rate || 0;
                $('#modal_rate').val(rate);
                if (rate === 0) {
                    frappe.msgprint(__('Harga tidak ditemukan di Price List: ' + priceList));
                }
            }
        });
    }

    validateBeforeSend() {
        if ($('#status').text() !== 'Draft') {
            frappe.msgprint('Only Draft orders can be sent to kitchen');
            return false;
        }

        if (!$('#items_table tr').length) {
            frappe.msgprint('Please add items before sending to kitchen');
            return false;
        }

        return true;
    }

    sendToKitchen() {
        const orderId = $('#order_id').val();
        if (!orderId) return;

        frappe.call({
            method: 'pos_restaurant_itb.api.create_kot.create_kot_from_pos_order',
            args: { pos_order_id: orderId },
            freeze: true,
            freeze_message: __('Mengirim ke dapur...'),
            callback: (r) => {
                if (r.message) {
                    this.refreshOrder();
                    frappe.show_alert({
                        message: __(`✅ KOT dibuat: ${r.message}`),
                        indicator: 'green'
                    });
                }
            }
        });
    }

    printKOT() {
        const orderId = $('#order_id').val();
        if (!orderId) return;

        frappe.call({
            method: 'pos_restaurant_itb.api.print_kot',
            args: { name: orderId },
            callback: (r) => {
                if (r.message) {
                    const win = window.open();
                    win.document.write(r.message);
                    win.document.close();
                }
            }
        });
    }

    printReceipt() {
        const orderId = $('#order_id').val();
        if (!orderId) return;

        frappe.call({
            method: 'pos_restaurant_itb.api.print_receipt',
            args: { name: orderId },
            callback: (r) => {
                if (r.message) {
                    const win = window.open();
                    win.document.write(r.message);
                    win.document.close();
                }
            }
        });
    }

    refreshOrder() {
        location.reload();
    }
}

// Initialize when document is ready
$(document).ready(() => {
    window.posOrderBridge = new POSOrderBridge();
});
