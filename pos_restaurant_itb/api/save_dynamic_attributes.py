@frappe.whitelist()
def save_dynamic_attributes(parent_pos_order_item, attributes):
    if not parent_pos_order_item or not attributes:
        frappe.throw(_("Parameter tidak lengkap."))

    if isinstance(attributes, str):
        attributes = json.loads(attributes)

    doc = frappe.get_doc("POS Order Item", parent_pos_order_item).as_dict()

    doc["dynamic_attributes"] = []

    for key, value in attributes.items():
        if not key or not value:
            continue
        doc["dynamic_attributes"].append({
            "doctype": "POS Dynamic Attribute",
            "attribute_name": key,
            "attribute_value": value
        })

    # Tambahkan ignore_permissions
    frappe.model.update_doc("POS Order Item", doc, ignore_permissions=True)

    return {
        "status": "success",
        "message": f"{len(doc['dynamic_attributes'])} atribut disimpan.",
        "dynamic_attributes": doc["dynamic_attributes"]
    }
