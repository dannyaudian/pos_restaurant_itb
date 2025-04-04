import frappe

def create_sales_invoice_and_payment(pos_order):
    table = frappe.get_doc("POS Table", pos_order.table)
    if not table.is_active:
        frappe.throw(f"Meja {table.table_id} sedang tidak aktif.")

    existing = frappe.db.exists("POS Order", {
        "table": pos_order.table,
        "status": ["not in", ["Paid", "Cancelled"]],
        "name": ["!=", pos_order.name]
    })
    if existing:
        frappe.throw(f"Meja {pos_order.table} sudah memiliki pesanan aktif.")

    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = pos_order.customer
    invoice.set_posting_time = True

    for item in pos_order.pos_order_items:
        invoice.append("items", {
            "item_code": item.item_code,
            "qty": item.qty,
            "rate": item.rate,
            "amount": item.amount
        })

    invoice.insert()
    invoice.submit()

    pos_order.sales_invoice = invoice.name

    if pos_order.payment_method == "QRIS":
        payment_entry = frappe.new_doc("Payment Entry")
        payment_entry.payment_type = "Receive"
        payment_entry.party_type = "Customer"
        payment_entry.party = pos_order.customer
        payment_entry.paid_amount = pos_order.total_amount
        payment_entry.received_amount = pos_order.total_amount
        payment_entry.reference_no = pos_order.name
        payment_entry.reference_date = frappe.utils.nowdate()
        payment_entry.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": invoice.name,
            "allocated_amount": pos_order.total_amount
        })
        payment_entry.insert()
        payment_entry.submit()
