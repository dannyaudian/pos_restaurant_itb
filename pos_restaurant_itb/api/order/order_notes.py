# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 14:40:57'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Dict, List, Optional
from datetime import datetime

from pos_restaurant_itb.utils.error_handlers import handle_api_error
from pos_restaurant_itb.utils.constants import (
    NoteType,
    NoteVisibility,
    ErrorMessages,
    CacheKeys
)
from pos_restaurant_itb.utils.realtime import notify_note_update

@frappe.whitelist()
@handle_api_error
def add_order_note(
    order_id: str,
    note_type: str,
    note: str,
    visibility: str = NoteVisibility.ALL,
    item_code: Optional[str] = None
) -> Dict:
    """
    Tambah catatan ke pesanan
    
    Args:
        order_id: ID pesanan (KOT/KDS)
        note_type: Tipe catatan
        note: Isi catatan
        visibility: Visibility catatan
        item_code: Kode item (optional)
        
    Returns:
        Dict: Note details
    """
    if note_type not in NoteType.ALL:
        frappe.throw(_(ErrorMessages.INVALID_NOTE_TYPE))
        
    if visibility not in NoteVisibility.ALL:
        frappe.throw(_(ErrorMessages.INVALID_VISIBILITY))
    
    # Create note
    note_doc = frappe.get_doc({
        "doctype": "Order Note",
        "order": order_id,
        "note_type": note_type,
        "note": note,
        "visibility": visibility,
        "item_code": item_code,
        "created_by": frappe.session.user,
        "created_at": frappe.utils.now()
    })
    
    note_doc.insert()
    
    # Update order's last_note_update
    order_doc = frappe.get_doc(
        "Kitchen Display Order" if "KDS" in order_id else "KOT",
        order_id
    )
    order_doc.last_note_update = frappe.utils.now()
    order_doc.save()
    
    # Notify update
    notify_note_update(note_doc)
    
    return {
        "success": True,
        "note_id": note_doc.name,
        "timestamp": frappe.utils.now()
    }

@frappe.whitelist()
@handle_api_error
def get_order_notes(
    order_id: str,
    note_type: Optional[List[str]] = None,
    visibility: Optional[List[str]] = None
) -> List[Dict]:
    """
    Get catatan pesanan
    
    Args:
        order_id: ID pesanan
        note_type: Filter by tipe
        visibility: Filter by visibility
        
    Returns:
        List[Dict]: Order notes
    """
    filters = {"order": order_id}
    
    if note_type:
        filters["note_type"] = ["in", note_type]
    if visibility:
        filters["visibility"] = ["in", visibility]
        
    # Check cache
    cache_key = f"{CacheKeys.ORDER_NOTES}:{order_id}"
    notes = frappe.cache().get_value(cache_key)
    
    if not notes:
        notes = frappe.get_all(
            "Order Note",
            filters=filters,
            fields=[
                "name", "note_type", "note",
                "visibility", "item_code",
                "created_by", "created_at"
            ],
            order_by="created_at desc"
        )
        
        # Add user details
        for note in notes:
            user = frappe.get_cached_doc("User", note.created_by)
            note["user_fullname"] = user.full_name
            note["user_image"] = user.user_image
        
        frappe.cache().set_value(
            cache_key,
            notes,
            expires_in_sec=300  # 5 minutes
        )
    
    return notes

@frappe.whitelist()
@handle_api_error
def update_note(
    note_id: str,
    note: str,
    visibility: Optional[str] = None
) -> Dict:
    """
    Update catatan
    
    Args:
        note_id: ID catatan
        note: Catatan baru
        visibility: Visibility baru (optional)
        
    Returns:
        Dict: Update status
    """
    note_doc = frappe.get_doc("Order Note", note_id)
    
    # Check permission
    if note_doc.created_by != frappe.session.user:
        frappe.throw(_(ErrorMessages.NOTE_UPDATE_DENIED))
    
    # Update note
    note_doc.note = note
    if visibility:
        if visibility not in NoteVisibility.ALL:
            frappe.throw(_(ErrorMessages.INVALID_VISIBILITY))
        note_doc.visibility = visibility
        
    note_doc.modified_by = frappe.session.user
    note_doc.modified = frappe.utils.now()
    note_doc.save()
    
    # Clear cache
    frappe.cache().delete_value(
        f"{CacheKeys.ORDER_NOTES}:{note_doc.order}"
    )
    
    # Notify update
    notify_note_update(note_doc)
    
    return {
        "success": True,
        "note_id": note_id,
        "timestamp": frappe.utils.now()
    }

@frappe.whitelist()
@handle_api_error
def delete_note(note_id: str) -> Dict:
    """
    Hapus catatan
    
    Args:
        note_id: ID catatan
        
    Returns:
        Dict: Delete status
    """
    note_doc = frappe.get_doc("Order Note", note_id)
    
    # Check permission
    if note_doc.created_by != frappe.session.user:
        frappe.throw(_(ErrorMessages.NOTE_DELETE_DENIED))
    
    # Store order ID for cache clearing
    order_id = note_doc.order
    
    # Delete note
    frappe.delete_doc("Order Note", note_id)
    
    # Clear cache
    frappe.cache().delete_value(
        f"{CacheKeys.ORDER_NOTES}:{order_id}"
    )
    
    return {
        "success": True,
        "timestamp": frappe.utils.now()
    }

@frappe.whitelist()
@handle_api_error
def get_note_templates(
    branch: str,
    note_type: Optional[str] = None
) -> List[Dict]:
    """
    Get template catatan
    
    Args:
        branch: ID branch
        note_type: Filter by tipe
        
    Returns:
        List[Dict]: Note templates
    """
    filters = {
        "branch": branch,
        "disabled": 0
    }
    
    if note_type:
        if note_type not in NoteType.ALL:
            frappe.throw(_(ErrorMessages.INVALID_NOTE_TYPE))
        filters["note_type"] = note_type
    
    # Get templates with cache
    cache_key = f"{CacheKeys.NOTE_TEMPLATES}:{branch}"
    templates = frappe.cache().get_value(cache_key)
    
    if not templates:
        templates = frappe.get_all(
            "Note Template",
            filters=filters,
            fields=[
                "name", "note_type", "template",
                "shortcut", "visibility"
            ],
            order_by="note_type, shortcut"
        )
        
        frappe.cache().set_value(
            cache_key,
            templates,
            expires_in_sec=3600  # 1 hour
        )
    
    return templates