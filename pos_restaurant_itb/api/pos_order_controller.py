import frappe
from frappe import _

def get_context(context):
    context.no_cache = 1
    
    # Get order name from route
    order_name = frappe.form_dict.get('name')
    
    if order_name:
        try:
            order = frappe.get_doc('POS Order', order_name)
            if order:
                context.doc = order
                context.title = f"Edit Order - {order_name}"
            else:
                frappe.throw(_("Order not found"))
        except frappe.DoesNotExistError:
            frappe.throw(_("Order not found"))
    else:
        context.title = "New Order"

    return context
