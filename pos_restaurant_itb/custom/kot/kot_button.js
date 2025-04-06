// Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
// For license information, please see license.txt

__created_date__ = '2025-04-06 09:33:58'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

frappe.ui.form.on('KOT', {
    refresh: function(frm) {
        add_action_buttons(frm);
        setup_realtime_updates(frm);
    },

    onload: function(frm) {
        setup_keyboard_shortcuts(frm);
    },

    validate: function(frm) {
        validate_kot_items(frm);
    }
});

function add_action_buttons(frm) {
    if (frm.doc.docstatus === 1) {
        // Add Kitchen Display button
        frm.add_custom_button(__("📺 Create Kitchen Display"), () => {
            create_kitchen_display(frm);
        }, __("Actions"));

        // Add Print KOT button
        frm.add_custom_button(__("🖨️ Print KOT"), () => {
            print_kot(frm);
        }, __("Actions"));

        // Add Refresh Status button
        frm.add_custom_button(__("🔄 Refresh Status"), () => {
            refresh_kot_status(frm);
        }, __("Actions"));
    }
}

function create_kitchen_display(frm) {
    frappe.call({
        method: "pos_restaurant_itb.api.kds_handler.create_kds_from_kot",
        args: { kot_id: frm.doc.name },
        freeze: true,
        freeze_message: __("Creating Kitchen Display..."),
        callback: function(r) {
            if (r.message && r.message.kds_name) {
                frappe.show_alert({
                    message: __("✅ Kitchen Display created successfully"),
                    indicator: 'green'
                });
                
                // Ask user if they want to view the KDS
                frappe.confirm(
                    __('Do you want to view the Kitchen Display?'),
                    () => {
                        frappe.set_route("Form", "Kitchen Display Order", r.message.kds_name);
                    }
                );
            } else {
                frappe.show_alert({
                    message: __("⚠️ Kitchen Display already exists"),
                    indicator: 'yellow'
                });
            }
        },
        error: function(r) {
            frappe.show_alert({
                message: __("❌ Failed to create Kitchen Display: {0}", [r.message]),
                indicator: 'red'
            });
        }
    });
}

function print_kot(frm) {
    frappe.show_progress(__("Preparing KOT Print"), 1, 2);
    
    frappe.db.get_value("Branch", frm.doc.branch, "printer_template", (r) => {
        if (r.printer_template) {
            frappe.show_progress(__("Preparing KOT Print"), 2, 2);
            frappe.render_template(r.printer_template, {
                doc: frm.doc,
                time: frappe.datetime.now_time(),
                date: frappe.datetime.now_date()
            }).then((html) => {
                frappe.show_progress(__("Printing KOT"), 1, 1);
                print_html(html);
            });
        } else {
            frappe.show_alert({
                message: __("⚠️ No printer template configured for this branch"),
                indicator: 'red'
            });
        }
    });
}

function refresh_kot_status(frm) {
    frappe.show_progress(__("Refreshing KOT Status"), 1, 1);
    frm.reload_doc();
}

function setup_realtime_updates(frm) {
    frappe.realtime.on(`kot_status_update_${frm.doc.name}`, function(data) {
        if (data.status !== frm.doc.status) {
            frm.reload_doc();
            
            frappe.show_alert({
                message: __("Status updated to: {0}", [__(data.status)]),
                indicator: get_status_indicator(data.status)
            });
        }
    });
}

function setup_keyboard_shortcuts(frm) {
    frappe.ui.keys.add_shortcut({
        shortcut: 'ctrl+k',
        action: () => create_kitchen_display(frm),
        description: __('Create Kitchen Display'),
        page: frm.page
    });

    frappe.ui.keys.add_shortcut({
        shortcut: 'ctrl+p',
        action: () => print_kot(frm),
        description: __('Print KOT'),
        page: frm.page
    });

    frappe.ui.keys.add_shortcut({
        shortcut: 'ctrl+r',
        action: () => refresh_kot_status(frm),
        description: __('Refresh KOT Status'),
        page: frm.page
    });
}

function validate_kot_items(frm) {
    if (!frm.doc.kot_items || !frm.doc.kot_items.length) {
        frappe.throw(__("❌ KOT must have at least one item"));
    }
}

function get_status_indicator(status) {
    const indicators = {
        'New': 'blue',
        'In Progress': 'orange',
        'Ready': 'green',
        'Served': 'green',
        'Cancelled': 'red'
    };
    return indicators[status] || 'gray';
}

// Register KOT Quick Entry
frappe.ui.form.on('KOT Item', {
    form_render: function(frm, cdt, cdn) {
        setup_item_quick_entry();
    }
});

function setup_item_quick_entry() {
    if (!frappe.ui.form.KOTItemQuickEntry) {
        class KOTItemQuickEntry extends frappe.ui.form.QuickEntryForm {
            render_dialog() {
                this.mandatory = [
                    {fieldname: 'item_code', fieldtype: 'Link', options: 'Item', label: 'Item'},
                    {fieldname: 'qty', fieldtype: 'Float', label: 'Quantity', default: 1},
                    {fieldname: 'note', fieldtype: 'Small Text', label: 'Note'}
                ];
                super.render_dialog();
            }
        }
        frappe.ui.form.KOTItemQuickEntry = KOTItemQuickEntry;
    }
}