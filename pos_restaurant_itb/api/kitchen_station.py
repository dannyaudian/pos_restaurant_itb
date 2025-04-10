# pos_restaurant_itb/api/kitchen_station.py

# Update the existing function to properly handle variant_attributes
@frappe.whitelist()
def create_kitchen_station_items_from_kot(kot_id):
    """
    Create Kitchen Station items for each item in the KOT.
    For items with quantity > 1, creates multiple Kitchen Station entries.
    """
    if not kot_id:
        frappe.throw(_("KOT ID is required."))
    
    kot = frappe.get_doc("Kitchen Order Ticket", kot_id)
    created_items = []
    
    # Validate branch isolation - only process for active branches
    branch_is_active = frappe.db.get_value("Branch", kot.branch, "is_active")
    if not branch_is_active:
        frappe.throw(_("Cannot create kitchen station items for inactive branch."))
    
    for kot_item in kot.kot_items:
        # Skip cancelled items
        if kot_item.cancelled:
            continue
        
        # Get the item group
        item_group = frappe.db.get_value("Item", kot_item.item_code, "item_group")
        
        # For each quantity unit, create a separate Kitchen Station entry
        for i in range(int(kot_item.qty)):
            kitchen_item = frappe.new_doc("Kitchen Station")
            kitchen_item.kot = kot.name
            kitchen_item.branch = kot.branch  # Ensure branch isolation
            kitchen_item.item_code = kot_item.item_code
            kitchen_item.item_group = item_group
            kitchen_item.status = kot_item.kot_status or "Queued"
            kitchen_item.note = kot_item.note
            
            # Copy variant attributes
            kitchen_item.variant_attributes = kot_item.variant_attributes
            # Update attribute summary
            kitchen_item.attribute_summary = kot_item.attribute_summary
            
            kitchen_item.cancelled = kot_item.cancelled
            kitchen_item.cancellation_note = kot_item.cancellation_note
            
            # Save the Kitchen Station item
            kitchen_item.insert(ignore_permissions=True)
            created_items.append(kitchen_item.name)
    
    if created_items:
        frappe.db.commit()
        return {
            "status": "success",
            "message": _(f"Created {len(created_items)} Kitchen Station items for KOT {kot_id}"),
            "items": created_items
        }
    else:
        return {
            "status": "warning",
            "message": _(f"No items created for KOT {kot_id}")
        }