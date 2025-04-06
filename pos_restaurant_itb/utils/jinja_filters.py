# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 09:14:13'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.utils import fmt_money, format_datetime as fmt_datetime
from typing import Optional, Any

def format_currency(value: float, currency: Optional[str] = None) -> str:
    """
    Format currency value
    
    Args:
        value (float): Amount to format
        currency (str, optional): Currency code. Defaults to system currency.
        
    Returns:
        str: Formatted currency string
    """
    if not currency:
        currency = frappe.db.get_default("currency")
    return fmt_money(value, currency=currency)

def format_datetime(value: Any, format_string: Optional[str] = None) -> str:
    """
    Format datetime value
    
    Args:
        value (Any): Datetime value to format
        format_string (str, optional): Format string. Defaults to "dd-mm-yyyy hh:mm:ss"
        
    Returns:
        str: Formatted datetime string
    """
    if not format_string:
        format_string = "dd-mm-yyyy hh:mm:ss"
    return fmt_datetime(value, format_string)

def format_status(status: str, style: bool = False) -> str:
    """
    Format status with optional styling
    
    Args:
        status (str): Status to format
        style (bool, optional): Add HTML styling. Defaults to False.
        
    Returns:
        str: Formatted status string
    """
    status_styles = {
        "Draft": "gray",
        "In Progress": "blue",
        "Ready": "green",
        "Completed": "green",
        "Cancelled": "red",
        "Pending": "orange",
        "Served": "green"
    }
    
    if not style:
        return _(status)
        
    color = status_styles.get(status, "gray")
    return f'<span class="indicator {color}">{_(status)}</span>'