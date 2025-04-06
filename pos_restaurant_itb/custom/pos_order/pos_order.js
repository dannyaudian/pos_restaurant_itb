/**
 * POS Restaurant ITB - POS Order Form
 * ---------------------------------
 * Form handler for POS Order document.
 * 
 * @author dannyaudian
 * @created 2025-04-06 08:24:10
 * @owner PT. Innovasi Terbaik Bangsa
 */

frappe.provide('pos_restaurant_itb.pos_order');

// Constants
const MESSAGES = {
    NO_BRANCH_ACCESS: "⚠️ Anda tidak memiliki akses ke cabang manapun.",
    SELECT_BRANCH_FIRST: "Pilih cabang terlebih dahulu.",
    TABLE_IN_USE: (table) => `❌ Meja ${table} sedang digunakan. Silakan pilih meja lain.`,
    NO_PRICE: (price_list) => `Harga tidak ditemukan di Price List: ${price_list}`,
    ATTRIBUTE_ADDED: "✔️ Atribut ditambahkan.",
    VARIANT_CHANGED: (name) => `🔄 Diganti ke Variant: ${name}`
};

// Main Handler Class
pos_restaurant_itb.pos_order = class POSOrderHandler {
    constructor(frm) {
        this.frm = frm;
        this.doc = frm.doc;
        this.setup();
    }

    setup() {
        this.setupFilters();
        this.setupValidations();
    }

    setupFilters() {
        // Branch Filter
        this.frm.set_query("branch", () => this.getBranchFilters());

        // Table Filter
        this.frm.set_query("table", () => this.getTableFilters());

        // Item Filter
        this.frm.fields_dict.pos_order_items.grid.get_field('item_code').get_query = 
            () => this.getItemFilters();
    }

    setupValidations() {
        // Add your validations here
    }

    async handleTableSelection() {
        if (!this.doc.table) return;

        try {
            const branchInfo = await this.getBranchFromTable();
            if (!branchInfo?.branch) return;

            await this.setBranch(branchInfo.branch);
            await this.validateTableAvailability(branchInfo.branch);
            await this.generateOrderId(branchInfo.branch);

        } catch (error) {
            this.handleError(error);
        }
    }

    async getBranchFromTable() {
        return await frappe.db.get_value('POS Table', this.doc.table, 'branch');
    }

    async setBranch(branch) {
        await this.frm.set_value('branch', branch);
    }

    async validateTableAvailability(branch) {
        const tables = await this.getAvailableTables(branch);
        const isAvailable = tables.some(t => t.name === this.doc.table);

        if (!isAvailable) {
            await this.frm.set_value("table", null);
            frappe.msgprint(MESSAGES.TABLE_IN_USE(this.doc.table));
            throw new Error('Table not available');
        }
    }

    async getAvailableTables(branch) {
        const result = await frappe.call({
            method: "pos_restaurant_itb.api.get_available_tables",
            args: { branch }
        });
        return result.message || [];
    }

    async generateOrderId(branch) {
        const result = await frappe.call({
            method: "pos_restaurant_itb.api.get_new_order_id",
            args: { branch }
        });
        
        if (result?.message) {
            await this.frm.set_value("order_id", result.message);
        }
    }

    getBranchFilters() {
        if (frappe.user.has_role("System Manager")) return {};

        const branches = frappe.user.get_perm("Branch") || [];
        if (!branches.length) {
            frappe.msgprint(__(MESSAGES.NO_BRANCH_ACCESS));
        }

        return {
            filters: { name: ["in", branches] }
        };
    }

    getTableFilters() {
        if (!this.doc.branch) {
            frappe.msgprint(MESSAGES.SELECT_BRANCH_FIRST);
            return { filters: { name: ["=", ""] } };
        }

        return {
            filters: [
                ["POS Table", "branch", "=", this.doc.branch],
                ["POS Table", "is_active", "=", 1]
            ]
        };
    }

    getItemFilters() {
        return {
            filters: {
                variant_of: ["is", "not set"],
                is_sales_item: 1,
                disabled: 0
            }
        };
    }

    handleError(error) {
        console.error("POS Order Error:", error);
        frappe.msgprint({
            title: __("Error"),
            indicator: 'red',
            message: __(error.message || "An error occurred")
        });
    }
};

// Item Handler Class
class POSOrderItemHandler {
    constructor(frm, cdt, cdn) {
        this.frm = frm;
        this.cdt = cdt;
        this.cdn = cdn;
        this.row = locals[cdt][cdn];
    }

    async handleItemCodeChange() {
        if (!this.row.item_code) return;

        try {
            await this.checkAndHandleVariants();
            await this.updateItemPrice();
        } catch (error) {
            console.error("Item Handler Error:", error);
        }
    }

    async checkAndHandleVariants() {
        const item = await frappe.db.get_value("Item", this.row.item_code, "has_variants");
        
        if (item?.has_variants) {
            await this.showVariantDialog();
        }
    }

    async showVariantDialog() {
        const attributes = await this.getItemAttributes();
        if (!attributes) return;

        const fields = this.prepareAttributeFields(attributes);
        const dialog = this.createAttributeDialog(fields);
        dialog.show();
    }

    async getItemAttributes() {
        const result = await frappe.call({
            method: "pos_restaurant_itb.api.get_attributes_for_item",
            args: { item_code: this.row.item_code }
        });
        return result.message;
    }

    prepareAttributeFields(attributes) {
        return attributes.map(attr => ({
            label: attr.attribute,
            fieldname: attr.attribute,
            fieldtype: "Select",
            options: (attr.values || []).join("\n"),
            reqd: 1
        }));
    }

    createAttributeDialog(fields) {
        return new frappe.ui.Dialog({
            title: 'Pilih Atribut',
            fields: fields,
            primary_action_label: 'Simpan',
            primary_action: (values) => this.handleAttributeSave(values)
        });
    }

    async handleAttributeSave(values) {
        const item_row = locals[this.row.doctype][this.row.name];
        item_row.dynamic_attributes = Object.entries(values).map(([key, value]) => ({
            attribute_name: key,
            attribute_value: value
        }));

        this.frm.refresh_field("pos_order_items");
        frappe.show_alert(MESSAGES.ATTRIBUTE_ADDED);
        await this.resolveVariant(values);
    }

    async resolveVariant(attributes) {
        const attr_array = Object.entries(attributes).map(([key, value]) => ({
            attribute_name: key,
            attribute_value: value
        }));

        const result = await frappe.call({
            method: "pos_restaurant_itb.api.resolve_variant",
            args: {
                template: this.row.item_code,
                attributes: attr_array
            }
        });

        if (result.message) {
            await this.updateVariantDetails(result.message);
        }
    }

    async updateVariantDetails(variant) {
        await frappe.model.set_value(this.row.doctype, this.row.name, {
            item_code: variant.item_code,
            item_name: variant.item_name,
            rate: variant.rate
        });

        frappe.show_alert({
            message: MESSAGES.VARIANT_CHANGED(variant.item_name),
            indicator: 'green'
        });
    }

    async updateItemPrice() {
        const price_list = this.frm.doc.selling_price_list || 'Standard Selling';
        const result = await this.getPriceListRate(price_list);
        
        const rate = result.message?.[0]?.price_list_rate || 0;
        await frappe.model.set_value(this.cdt, this.cdn, 'rate', rate);

        if (rate === 0) {
            frappe.msgprint(__(MESSAGES.NO_PRICE(price_list)));
        }
    }

    async getPriceListRate(price_list) {
        return await frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Item Price",
                filters: {
                    item_code: this.row.item_code,
                    price_list: price_list
                },
                fields: ["price_list_rate"],
                limit_page_length: 1
            }
        });
    }
}

// Form Events
frappe.ui.form.on('POS Order', {
    onload: function(frm) {
        new pos_restaurant_itb.pos_order(frm);
    },

    table: function(frm) {
        new pos_restaurant_itb.pos_order(frm).handleTableSelection();
    }
});

frappe.ui.form.on('POS Order Item', {
    item_code: function(frm, cdt, cdn) {
        new POSOrderItemHandler(frm, cdt, cdn).handleItemCodeChange();
    },

    qty: function(frm, cdt, cdn) {
        updateAmount(frm, cdt, cdn);
    },

    rate: function(frm, cdt, cdn) {
        updateAmount(frm, cdt, cdn);
    }
});

// Helper Functions
function updateAmount(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row) return;

    const amount = (row.qty || 0) * (row.rate || 0);
    frappe.model.set_value(cdt, cdn, "amount", amount);

    const total = (frm.doc.pos_order_items || [])
        .reduce((sum, item) => sum + (item.amount || 0), 0);

    frm.set_value("total_amount", total);
    frm.refresh_field("total_amount");
}