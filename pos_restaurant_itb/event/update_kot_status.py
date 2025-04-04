import frappe

def update_pos_order_status(pos_order):
    kot_statuses = [item.kot_status for item in pos_order.pos_order_items]
    if all(status == "Ready" for status in kot_statuses):
        pos_order.status = "Ready for Billing"
    elif any(status == "Cooking" for status in kot_statuses):
        pos_order.status = "In Progress"
    else:
        pos_order.status = "Submitted"
