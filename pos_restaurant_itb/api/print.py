# pos_restaurant_itb/api/print.py

import frappe
from pos_restaurant_itb.utils.print_templates import render_kot_template, render_thermal_receipt

@frappe.whitelist()
def print_kot(name):
    doc = frappe.get_doc("POS Order", name)
    return render_kot_template(doc)

@frappe.whitelist()
def print_receipt(name):
    doc = frappe.get_doc("POS Order", name)
    return render_thermal_receipt(doc)