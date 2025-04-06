# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 08:48:49'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from frappe.utils import flt

def get_item_price(item_code, price_list=None, company=None):
    """
    Get item price from price list
    
    Args:
        item_code (str): Item code
        price_list (str, optional): Price list name. Defaults to None.
        company (str, optional): Company name. Defaults to None.
        
    Returns:
        float: Item price
    """
    if not price_list:
        price_list = (
            frappe.db.get_single_value("Selling Settings", "selling_price_list") or 
            "Standard Selling"
        )
        
    if not company:
        company = frappe.defaults.get_user_default("company")

    price = frappe.db.get_value(
        "Item Price",
        {
            "item_code": item_code,
            "price_list": price_list,
            "selling": 1,
            "company": company
        },
        "price_list_rate"
    )
    
    if price is None:
        price = frappe.db.get_value("Item", item_code, "standard_rate") or 0
        
    return flt(price)

def calculate_item_amount(rate, qty, extra_prices=None):
    """
    Calculate item amount with extra prices
    
    Args:
        rate (float): Base rate
        qty (float): Quantity
        extra_prices (list, optional): List of extra prices. Defaults to None.
        
    Returns:
        float: Total amount
    """
    amount = flt(rate) * flt(qty)
    
    if extra_prices:
        extra_total = sum(flt(price) for price in extra_prices if price)
        amount += (extra_total * flt(qty))
        
    return flt(amount)

def get_price_list_details(price_list):
    """
    Get price list currency and conversion rate
    
    Args:
        price_list (str): Price list name
        
    Returns:
        dict: Price list details
    """
    if not price_list:
        return {}
        
    return frappe.db.get_value(
        "Price List",
        price_list,
        ["currency", "price_not_uom_dependent"],
        as_dict=True
    ) or {}