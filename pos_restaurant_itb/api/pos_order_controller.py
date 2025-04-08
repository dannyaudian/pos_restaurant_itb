import frappe
from frappe import _

@frappe.whitelist()
def get_order_context(order_name=None):
    data = {
        'no_cache': 1,
        'doc': None,
        'title': 'New Order'
    }
    
    if order_name:
        try:
            order = frappe.get_doc('POS Order', order_name)
            if order:
                data['doc'] = order
                data['title'] = f"Edit Order - {order_name}"
            else:
                frappe.throw(_("Order not found"))
        except frappe.DoesNotExistError:
            frappe.throw(_("Order not found"))
    
    return data

@frappe.whitelist()
def create_or_update_order(order_data, order_name=None):
    try:
        if order_name:
            # Update existing order
            doc = frappe.get_doc('POS Order', order_name)
            doc.update(frappe.parse_json(order_data))
            doc.save()
        else:
            # Create new order
            doc = frappe.get_doc(frappe.parse_json(order_data))
            doc.insert()
        
        return {
            'status': 'success',
            'message': _('Order saved successfully'),
            'order_name': doc.name
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _('Failed to save POS Order'))
        return {
            'status': 'error',
            'message': str(e)
        }
