# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 09:01:39'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from functools import wraps

class POSRestaurantError(Exception):
    """Base exception class for POS Restaurant"""
    def __init__(self, message, title=None, **kwargs):
        self.message = message
        self.title = title or "Error"
        self.kwargs = kwargs
        super().__init__(self.message)

class TableError(POSRestaurantError):
    """Table related errors"""
    pass

class OrderError(POSRestaurantError):
    """Order related errors"""
    pass

class KitchenError(POSRestaurantError):
    """Kitchen related errors"""
    pass

class ValidationError(POSRestaurantError):
    """Validation related errors"""
    pass

def handle_pos_errors(log_error=True):
    """
    Decorator for handling POS Restaurant errors
    
    Args:
        log_error (bool): Whether to log error in Error Log
        
    Usage:
        @handle_pos_errors()
        def my_function():
            # Your code here
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except POSRestaurantError as e:
                if log_error:
                    frappe.log_error(
                        message=f"POS Error: {str(e)}",
                        title=e.title,
                        **e.kwargs
                    )
                frappe.throw(_(str(e)), title=_(e.title))
            except Exception as e:
                if log_error:
                    frappe.log_error(
                        message=f"Unexpected Error: {str(e)}",
                        title="POS System Error"
                    )
                frappe.throw(
                    _("An unexpected error occurred. Please contact support."),
                    title=_("System Error")
                )
        return wrapper
    return decorator

def log_pos_activity(activity_type, title=None):
    """
    Decorator for logging POS activities
    
    Args:
        activity_type (str): Type of activity
        title (str): Optional title for the log
        
    Usage:
        @log_pos_activity("order_creation")
        def create_order():
            # Your code here
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                # Log successful activity
                frappe.log_error(
                    message=f"Activity: {activity_type}\nUser: {frappe.session.user}\nResult: Success",
                    title=title or f"POS Activity: {activity_type}",
                    type="Activity Log"
                )
                
                return result
            except Exception as e:
                # Log failed activity
                frappe.log_error(
                    message=f"Activity: {activity_type}\nUser: {frappe.session.user}\nError: {str(e)}",
                    title=title or f"POS Activity Error: {activity_type}"
                )
                raise
        return wrapper
    return decorator

def handle_transaction_error(doc, silent=False):
    """Handle transaction related errors"""
    try:
        if doc.docstatus == 1:  # If submitted
            doc.cancel()
        doc.delete()
        if not silent:
            frappe.msgprint(_("Transaction cancelled and cleaned up"))
    except Exception as e:
        frappe.log_error(
            message=f"Failed to cleanup {doc.doctype} {doc.name}: {str(e)}",
            title="Transaction Cleanup Error"
        )
        if not silent:
            raise

def cleanup_failed_documents(days=1):
    """Cleanup failed draft documents"""
    doctypes = ["POS Order", "KOT", "Sales Invoice"]
    
    for dt in doctypes:
        docs = frappe.get_all(
            dt,
            filters={
                "docstatus": 0,
                "modified": ["<", f"DATE_SUB(NOW(), INTERVAL {days} DAY)"]
            }
        )
        
        for doc in docs:
            try:
                frappe.delete_doc(dt, doc.name, force=1)
            except:
                continue