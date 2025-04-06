# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 08:33:29'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
import unittest

def setup_test_data():
    """Setup test data for POS Restaurant tests"""
    create_test_branch()
    create_test_tables()
    create_test_items()
    create_test_users()

def create_test_branch():
    """Create test branch"""
    if not frappe.db.exists("Branch", "Test Branch"):
        doc = frappe.get_doc({
            "doctype": "Branch",
            "branch": "Test Branch",
            "branch_code": "TEST",
            "company": "_Test Company"
        })
        doc.insert()

def create_test_tables():
    """Create test tables"""
    if not frappe.db.exists("POS Table", "T-001"):
        doc = frappe.get_doc({
            "doctype": "POS Table",
            "table_number": "T-001",
            "branch": "Test Branch",
            "capacity": 4,
            "is_active": 1
        })
        doc.insert()

def create_test_items():
    """Create test items"""
    items = [
        {
            "item_code": "TEST-ITEM-001",
            "item_name": "Test Food Item",
            "item_group": "Food",
            "is_stock_item": 0,
            "standard_rate": 100
        }
    ]
    
    for item in items:
        if not frappe.db.exists("Item", item["item_code"]):
            doc = frappe.get_doc({
                "doctype": "Item",
                **item
            })
            doc.insert()

def create_test_users():
    """Create test users"""
    users = [
        {
            "email": "testwaiter@test.com",
            "first_name": "Test",
            "last_name": "Waiter",
            "role": "Waiter"
        }
    ]
    
    for user in users:
        if not frappe.db.exists("User", user["email"]):
            doc = frappe.get_doc({
                "doctype": "User",
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "roles": [{"role": user["role"]}]
            })
            doc.insert()

class TestPOSRestaurant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup_test_data()