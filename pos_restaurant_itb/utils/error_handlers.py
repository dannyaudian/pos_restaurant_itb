# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 07:41:12'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from functools import wraps
from frappe.utils import get_traceback

def handle_api_error(fn):
    """
    Decorator to handle API errors consistently
    
    Args:
        fn: Function to decorate
        
    Returns:
        Wrapped function that handles errors
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except frappe.DoesNotExistError:
            frappe.local.response.http_status_code = 404
            return {
                "success": False,
                "message": _("Resource not found"),
                "error_code": "NOT_FOUND",
                "timestamp": frappe.utils.now()
            }
        except frappe.ValidationError as e:
            frappe.local.response.http_status_code = 400
            return {
                "success": False,
                "message": str(e),
                "error_code": "VALIDATION_ERROR",
                "timestamp": frappe.utils.now()
            }
        except frappe.AuthenticationError:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": _("Authentication failed"),
                "error_code": "AUTHENTICATION_ERROR",
                "timestamp": frappe.utils.now()
            }
        except frappe.PermissionError:
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": _("You don't have permission to access this resource"),
                "error_code": "PERMISSION_ERROR",
                "timestamp": frappe.utils.now()
            }
        except Exception as e:
            frappe.log_error(
                title="API Error",
                message=get_traceback()
            )
            frappe.local.response.http_status_code = 500
            return {
                "success": False,
                "message": _("Internal server error"),
                "error_code": "INTERNAL_ERROR",
                "timestamp": frappe.utils.now()
            }
    return wrapper

def handle_doc_error(fn):
    """
    Decorator to handle document operation errors
    
    Args:
        fn: Function to decorate
        
    Returns:
        Wrapped function that handles document errors
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except frappe.DoesNotExistError as e:
            frappe.throw(_("Document not found: {0}").format(str(e)))
        except frappe.ValidationError as e:
            frappe.throw(_("Validation failed: {0}").format(str(e)))
        except frappe.AuthenticationError:
            frappe.throw(_("Authentication failed"))
        except frappe.PermissionError:
            frappe.throw(_("You don't have permission to perform this action"))
        except Exception as e:
            frappe.log_error(
                title="Document Operation Error",
                message=get_traceback()
            )
            frappe.throw(_("An error occurred while processing the document"))
    return wrapper

class POSRestaurantError(Exception):
    """Base exception class for POS Restaurant"""
    pass

class TableError(POSRestaurantError):
    """Exception for table related errors"""
    pass

class OrderError(POSRestaurantError):
    """Exception for order related errors"""
    pass

class KitchenError(POSRestaurantError):
    """Exception for kitchen related errors"""
    pass

class ValidationError(POSRestaurantError):
    """Exception for validation errors"""
    pass

def handle_pos_errors(fn):
    """
    Decorator to handle POS specific errors
    
    Args:
        fn: Function to decorate
        
    Returns:
        Wrapped function that handles POS errors
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except POSRestaurantError as e:
            frappe.log_error(
                title="POS Error",
                message=get_traceback()
            )
            frappe.throw(str(e))
        except Exception as e:
            frappe.log_error(
                title="POS System Error",
                message=get_traceback()
            )
            frappe.throw(_("An error occurred in POS system"))
    return wrapper

def log_pos_activity(activity_type: str, data: dict = None) -> None:
    """
    Log POS activity for auditing
    
    Args:
        activity_type: Type of activity
        data: Additional data to log
    """
    if not data:
        data = {}
    
    log = frappe.get_doc({
        "doctype": "POS Activity Log",
        "activity_type": activity_type,
        "user": frappe.session.user,
        "data": frappe.as_json(data),
        "creation": frappe.utils.now()
    })
    log.insert(ignore_permissions=True)

def notify_error(title: str, message: str) -> None:
    """
    Send error notification to user
    
    Args:
        title: Error title
        message: Error message
    """
    frappe.publish_realtime(
        "pos_error_notification",
        {
            "title": title,
            "message": message,
            "timestamp": frappe.utils.now()
        },
        user=frappe.session.user
    )

def handle_transaction_error(fn):
    """
    Decorator to handle transaction errors
    
    Args:
        fn: Function to decorate
        
    Returns:
        Wrapped function that handles transaction errors
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            frappe.db.rollback()
            cleanup_failed_documents()
            frappe.log_error(
                title="Transaction Error",
                message=get_traceback()
            )
            raise
    return wrapper

def cleanup_failed_documents() -> None:
    """Clean up any failed document operations"""
    try:
        # Add specific cleanup logic here
        frappe.db.commit()
    except:
        frappe.db.rollback()