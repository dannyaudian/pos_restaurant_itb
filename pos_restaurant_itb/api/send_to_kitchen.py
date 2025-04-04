# pos_restaurant_itb/api/send_to_kitchen.py

import frappe

@frappe.whitelist()
def send_to_kitchen(pos_order):
    from pos_restaurant_itb.doctype.kot.kot import create_kot_from_pos_order

    kot_name = create_kot_from_pos_order(pos_order)

    # Ambil kembali POS Order dan KOT setelah submit untuk update kot_id
    pos_order_doc = frappe.get_doc("POS Order", pos_order)
    kot_doc = frappe.get_doc("KOT", kot_name)

    # Tandai kot_id di setiap item yang dikirim
    for kot_item in kot_doc.kot_items:
        for order_item in pos_order_doc.pos_order_items:
            if (
                order_item.item_code == kot_item.item_code
                and order_item.qty == kot_item.qty
                and not order_item.kot_id
                and order_item.sent_to_kitchen
            ):
                order_item.kot_id = kot_doc.name

    pos_order_doc.save()
    return kot_name