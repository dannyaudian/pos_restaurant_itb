import frappe
from frappe import _

def create_kot_from_pos_order(pos_order, method=None):
    """
    Create a Kitchen Order Ticket from a submitted POS Order
    """
    # Skip if already processed or no items need to be sent to kitchen
    items_to_send = [
        item for item in pos_order.items 
        if not item.sent_to_kitchen and not item.cancelled
    ]
    
    if not items_to_send:
        return
    
    # Create new KOT
    kot = frappe.new_doc("Kitchen Order Ticket")
    kot.pos_order = pos_order.name
    kot.table = pos_order.table
    kot.branch = pos_order.branch
    
    # Add items that haven't been sent to kitchen yet
    for item in items_to_send:
        kot.append("kot_items", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "note": item.note,
            "dynamic_attributes": item.dynamic_attributes
        })
    
    # Save and submit KOT
    kot.insert()
    
    frappe.msgprint(_("Kitchen Order Ticket {0} created").format(kot.kot_id))
    
    return kot

def process_pos_order_after_insert(doc, method=None):
    """
    Process a POS Order after insert:
    1. Create Kitchen Order Ticket for items
    2. This will trigger creation of KDS and Kitchen Station via other hooks
    
    Args:
        doc: The POS Order document
        method: The method that triggered this hook (unused)
    """
    try:
        # Skip processing if no items or all items are already sent to kitchen
        items_to_send = [
            item for item in doc.items 
            if not item.sent_to_kitchen and not item.cancelled
        ]
        
        if not items_to_send:
            return
            
        # Check if branch is active
        branch_is_active = frappe.db.get_value("Branch", doc.branch, "is_active")
        if not branch_is_active:
            frappe.throw(_("Cannot create kitchen orders for inactive branch."))
            
        # Import and call KOT creation function
        from pos_restaurant_itb.api.create_kot import create_kot_from_pos_order
        result = create_kot_from_pos_order(doc.name)
        
        if result.get("status") == "success":
            # Log success message
            frappe.msgprint(_(
                "Kitchen Order Ticket {0} created and sent to kitchen."
            ).format(result.get("kot_id")))
            
            # We don't need to trigger KDS and Kitchen Station creation explicitly
            # as they will be triggered by the KOT's after_insert hooks
        
        elif result.get("status") == "error":
            frappe.msgprint(result.get("message"), indicator="red", alert=True)
            
    except Exception as e:
        frappe.log_error(
            title=f"Error Processing POS Order {doc.name}",
            message=f"Error: {str(e)}\n\nTraceback: {frappe.get_traceback()}"
        )
        frappe.msgprint(_(
            "Error processing order for kitchen: {0}"
        ).format(str(e)), indicator="red", alert=True)