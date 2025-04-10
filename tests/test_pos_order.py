# tests/test_pos_order.py

import pytest
import json
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime
from pos_restaurant_itb.utils.kot_helpers import get_attribute_summary

class TestPOSOrder(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test data and dependencies."""
        super().setUpClass()
        # Create test branch
        if not frappe.db.exists("Branch", "Test Branch"):
            branch = frappe.get_doc({
                "doctype": "Branch",
                "branch": "Test Branch",
                "branch_code": "TEST",
                "company": "_Test Company",
                "is_active": 1
            })
            branch.insert(ignore_if_duplicate=True)
        
        # Create test table
        if not frappe.db.exists("POS Table", "Test Table-1"):
            table = frappe.get_doc({
                "doctype": "POS Table",
                "table_id": "Test Table-1",
                "branch": "Test Branch",
                "is_active": 1
            })
            table.insert(ignore_if_duplicate=True)
        
        # Create test item template
        if not frappe.db.exists("Item", "Test Food Template"):
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": "Test Food Template",
                "item_name": "Test Food Template",
                "item_group": "Products", 
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "has_variants": 1,
                "variant_based_on": "Item Attribute",
                "attributes": [
                    {
                        "attribute": "Spice Level",
                        "attribute_values": "Mild\nMedium\nHot"
                    },
                    {
                        "attribute": "Toppings",
                        "attribute_values": "Plain\nCheese\nExtra Cheese"
                    }
                ],
                "standard_rate": 100
            })
            item.insert(ignore_if_duplicate=True)
        
        # Create test item variant
        if not frappe.db.exists("Item", "Test Food Variant-M-C"):
            variant = frappe.get_doc({
                "doctype": "Item",
                "item_code": "Test Food Variant-M-C",
                "item_name": "Test Food Variant Medium Cheese",
                "item_group": "Products",
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "variant_of": "Test Food Template",
                "attributes": [
                    {
                        "attribute": "Spice Level",
                        "attribute_value": "Medium"
                    },
                    {
                        "attribute": "Toppings",
                        "attribute_value": "Cheese"
                    }
                ],
                "standard_rate": 120
            })
            variant.insert(ignore_if_duplicate=True)
    
    def tearDown(self):
        """Clean up test data after each test."""
        # Delete any POS Orders created for testing
        for order in frappe.get_all("POS Order", filters={"order_id": ["like", "TEST-%"]}, pluck="name"):
            try:
                frappe.delete_doc("POS Order", order, force=True)
            except Exception:
                pass
        
        # Delete any KOTs created for testing
        for kot in frappe.get_all("Kitchen Order Ticket", filters={"pos_order": ["like", "TEST-%"]}, pluck="name"):
            try:
                frappe.delete_doc("Kitchen Order Ticket", kot, force=True)
            except Exception:
                pass
    
    def test_pos_order_validation(self):
        """Test basic validation for POS Order."""
        # Test missing required fields
        pos_order = frappe.new_doc("POS Order")
        pos_order.order_id = "TEST-MANUAL-ID"
        
        # Should raise ValidationError for missing required fields
        with self.assertRaises(frappe.exceptions.ValidationError):
            pos_order.insert()
        
        # Test inactive branch validation
        frappe.db.set_value("Branch", "Test Branch", "is_active", 0)
        
        pos_order = frappe.new_doc("POS Order")
        pos_order.order_id = "TEST-MANUAL-ID"
        pos_order.branch = "Test Branch"
        pos_order.order_type = "Dine In"
        pos_order.table = "Test Table-1"
        pos_order.append("items", {
            "item_code": "Test Food Variant-M-C",
            "item_name": "Test Food Variant Medium Cheese",
            "qty": 1,
            "rate": 120,
            "amount": 120
        })
        pos_order.total_amount = 120
        
        # Should raise ValidationError for inactive branch
        with self.assertRaises(frappe.exceptions.ValidationError):
            pos_order.insert()
        
        # Reset branch to active
        frappe.db.set_value("Branch", "Test Branch", "is_active", 1)
    
    def test_pos_order_auto_order_id(self):
        """Test auto-generation of order_id based on branch code and date."""
        # Create a POS Order without specifying order_id
        pos_order = frappe.new_doc("POS Order")
        pos_order.branch = "Test Branch"
        pos_order.order_type = "Dine In"
        pos_order.table = "Test Table-1"
        pos_order.append("items", {
            "item_code": "Test Food Variant-M-C",
            "item_name": "Test Food Variant Medium Cheese",
            "qty": 1,
            "rate": 120,
            "amount": 120
        })
        pos_order.total_amount = 120
        pos_order.insert()
        
        # Verify order_id format: ORD-{branch_code}-{YYYYMMDD}-{####}
        date_str = now_datetime().strftime("%Y%m%d")
        self.assertTrue(pos_order.order_id.startswith(f"ORD-TEST-{date_str}-"))
        
        # Verify sequence number
        sequence_number = int(pos_order.order_id.split("-")[-1])
        self.assertGreaterEqual(sequence_number, 1)
        
        # Create another order and check sequence increments
        pos_order2 = frappe.new_doc("POS Order")
        pos_order2.branch = "Test Branch"
        pos_order2.order_type = "Dine In"
        pos_order2.table = "Test Table-1"
        pos_order2.append("items", {
            "item_code": "Test Food Variant-M-C",
            "item_name": "Test Food Variant Medium Cheese",
            "qty": 1,
            "rate": 120,
            "amount": 120
        })
        pos_order2.total_amount = 120
        pos_order2.insert()
        
        sequence_number2 = int(pos_order2.order_id.split("-")[-1])
        self.assertEqual(sequence_number2, sequence_number + 1)
    
    def test_total_calculation(self):
        """Test automatic calculation of total amount."""
        pos_order = frappe.new_doc("POS Order")
        pos_order.branch = "Test Branch"
        pos_order.order_type = "Dine In"
        pos_order.table = "Test Table-1"
        
        # Add multiple items
        pos_order.append("items", {
            "item_code": "Test Food Variant-M-C",
            "item_name": "Test Food Variant Medium Cheese",
            "qty": 2,
            "rate": 120,
            "amount": 240
        })
        
        pos_order.append("items", {
            "item_code": "Test Food Variant-M-C",
            "item_name": "Test Food Variant Medium Cheese",
            "qty": 1,
            "rate": 120,
            "amount": 120
        })
        
        # Calculate expected total
        expected_total = 240 + 120  # 360
        
        pos_order.total_amount = expected_total
        pos_order.insert()
        
        # Verify total amount is calculated correctly
        self.assertEqual(pos_order.total_amount, expected_total)
    
    def test_dynamic_attributes_storage(self):
        """Test storage of dynamic attributes for variant items."""
        dynamic_attrs = [
            {"attribute_name": "Spice Level", "attribute_value": "Medium"},
            {"attribute_name": "Toppings", "attribute_value": "Cheese"}
        ]
        
        pos_order = frappe.new_doc("POS Order")
        pos_order.branch = "Test Branch"
        pos_order.order_type = "Dine In"
        pos_order.table = "Test Table-1"
        
        # Add item with dynamic attributes
        pos_order.append("items", {
            "item_code": "Test Food Variant-M-C",
            "item_name": "Test Food Variant Medium Cheese",
            "qty": 1,
            "rate": 120,
            "amount": 120,
            "template_item": "Test Food Template",
            "dynamic_attributes": json.dumps(dynamic_attrs)
        })
        
        pos_order.total_amount = 120
        pos_order.insert()
        
        # Verify dynamic attributes are stored correctly
        item = pos_order.items[0]
        self.assertTrue(item.dynamic_attributes)
        
        # Parse and verify attributes
        stored_attrs = json.loads(item.dynamic_attributes)
        self.assertEqual(len(stored_attrs), 2)
        self.assertEqual(stored_attrs[0]["attribute_name"], "Spice Level")
        self.assertEqual(stored_attrs[0]["attribute_value"], "Medium")
        self.assertEqual(stored_attrs[1]["attribute_name"], "Toppings")
        self.assertEqual(stored_attrs[1]["attribute_value"], "Cheese")


class TestKOTCreation(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test data and dependencies."""
        super().setUpClass()
        # Create test branch
        if not frappe.db.exists("Branch", "Test Branch"):
            branch = frappe.get_doc({
                "doctype": "Branch",
                "branch": "Test Branch",
                "branch_code": "TEST",
                "company": "_Test Company",
                "is_active": 1
            })
            branch.insert(ignore_if_duplicate=True)
        
        # Create test table
        if not frappe.db.exists("POS Table", "Test Table-1"):
            table = frappe.get_doc({
                "doctype": "POS Table",
                "table_id": "Test Table-1",
                "branch": "Test Branch",
                "is_active": 1
            })
            table.insert(ignore_if_duplicate=True)
        
        # Create test item
        if not frappe.db.exists("Item", "Test Food Item"):
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": "Test Food Item",
                "item_name": "Test Food Item",
                "item_group": "Products",
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "standard_rate": 100
            })
            item.insert(ignore_if_duplicate=True)
    
    def tearDown(self):
        """Clean up test data after each test."""
        # Delete any POS Orders created for testing
        for order in frappe.get_all("POS Order", filters={"order_id": ["like", "TEST-%"]}, pluck="name"):
            try:
                frappe.delete_doc("POS Order", order, force=True)
            except Exception:
                pass
        
        # Delete any KOTs created for testing
        for kot in frappe.get_all("Kitchen Order Ticket", filters={"pos_order": ["like", "TEST-%"]}, pluck="name"):
            try:
                frappe.delete_doc("Kitchen Order Ticket", kot, force=True)
            except Exception:
                pass
    
    def test_kot_creation_from_pos_order(self):
        """Test creation of KOT from POS Order."""
        # Import the function to create KOT
        from pos_restaurant_itb.api.create_kot import create_kot_from_pos_order
        
        # Create a test POS Order
        pos_order = frappe.new_doc("POS Order")
        pos_order.branch = "Test Branch"
        pos_order.order_type = "Dine In"
        pos_order.table = "Test Table-1"
        pos_order.append("items", {
            "item_code": "Test Food Item",
            "item_name": "Test Food Item",
            "qty": 1,
            "rate": 100,
            "amount": 100,
            "sent_to_kitchen": 0
        })
        pos_order.total_amount = 100
        pos_order.insert()
        
        # Create KOT from the POS Order
        result = create_kot_from_pos_order(pos_order.name)
        
        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["kot_id"])
        
        # Verify KOT was created correctly
        kot = frappe.get_doc("Kitchen Order Ticket", result["kot_id"])
        self.assertEqual(kot.pos_order, pos_order.name)
        self.assertEqual(kot.branch, pos_order.branch)
        self.assertEqual(kot.table, pos_order.table)
        self.assertEqual(kot.status, "New")
        
        # Verify KOT Items
        self.assertEqual(len(kot.kot_items), 1)
        kot_item = kot.kot_items[0]
        self.assertEqual(kot_item.item_code, "Test Food Item")
        self.assertEqual(kot_item.qty, 1)
        self.assertEqual(kot_item.kot_status, "Queued")
        
        # Verify POS Order Item was updated
        pos_order.reload()
        self.assertEqual(pos_order.items[0].sent_to_kitchen, 1)
        self.assertEqual(pos_order.items[0].kot_id, kot.name)
    
    def test_kot_creation_with_dynamic_attributes(self):
        """Test creation of KOT with dynamic attributes from POS Order."""
        # Import the function to create KOT
        from pos_restaurant_itb.api.create_kot import create_kot_from_pos_order
        
        dynamic_attrs = [
            {"attribute_name": "Spice Level", "attribute_value": "Medium"},
            {"attribute_name": "Toppings", "attribute_value": "Cheese"}
        ]
        
        # Create a test POS Order with dynamic attributes
        pos_order = frappe.new_doc("POS Order")
        pos_order.branch = "Test Branch"
        pos_order.order_type = "Dine In"
        pos_order.table = "Test Table-1"
        pos_order.append("items", {
            "item_code": "Test Food Item",
            "item_name": "Test Food Item",
            "qty": 1,
            "rate": 100,
            "amount": 100,
            "dynamic_attributes": json.dumps(dynamic_attrs),
            "sent_to_kitchen": 0
        })
        pos_order.total_amount = 100
        pos_order.insert()
        
        # Create KOT from the POS Order
        result = create_kot_from_pos_order(pos_order.name)
        
        # Verify KOT was created with dynamic attributes
        kot = frappe.get_doc("Kitchen Order Ticket", result["kot_id"])
        kot_item = kot.kot_items[0]
        
        # Verify dynamic attributes were copied correctly
        self.assertTrue(kot_item.dynamic_attributes)
        copied_attrs = json.loads(kot_item.dynamic_attributes)
        self.assertEqual(len(copied_attrs), 2)
        self.assertEqual(copied_attrs[0]["attribute_name"], "Spice Level")
        self.assertEqual(copied_attrs[0]["attribute_value"], "Medium")
        
        # Verify attribute summary is generated correctly
        if hasattr(kot_item, "attribute_summary"):
            summary = kot_item.attribute_summary
            self.assertIn("Spice Level: Medium", summary)
            self.assertIn("Toppings: Cheese", summary)
    
    def test_multiple_kot_creations(self):
        """Test creating multiple KOTs from a single POS Order."""
        # Import the function to create KOT
        from pos_restaurant_itb.api.create_kot import create_kot_from_pos_order
        
        # Create a test POS Order
        pos_order = frappe.new_doc("POS Order")
        pos_order.branch = "Test Branch"
        pos_order.order_type = "Dine In"
        pos_order.table = "Test Table-1"
        
        # Add two items
        pos_order.append("items", {
            "item_code": "Test Food Item",
            "item_name": "Test Food Item",
            "qty": 1,
            "rate": 100,
            "amount": 100,
            "sent_to_kitchen": 0
        })
        
        pos_order.append("items", {
            "item_code": "Test Food Item",
            "item_name": "Test Food Item",
            "qty": 2,
            "rate": 100,
            "amount": 200,
            "sent_to_kitchen": 0
        })
        
        pos_order.total_amount = 300
        pos_order.insert()
        
        # Create first KOT
        result1 = create_kot_from_pos_order(pos_order.name)
        self.assertEqual(result1["status"], "success")
        
        # Reload POS Order to get updated values
        pos_order.reload()
        
        # Add a new item to the POS Order
        pos_order.append("items", {
            "item_code": "Test Food Item",
            "item_name": "Test Food Item",
            "qty": 1,
            "rate": 100,
            "amount": 100,
            "sent_to_kitchen": 0
        })
        pos_order.total_amount = 400
        pos_order.save()
        
        # Create second KOT for the new item
        result2 = create_kot_from_pos_order(pos_order.name)
        self.assertEqual(result2["status"], "success")
        
        # Verify we have two different KOTs
        self.assertNotEqual(result1["kot_id"], result2["kot_id"])
        
        # Verify the second KOT only has the new item
        kot2 = frappe.get_doc("Kitchen Order Ticket", result2["kot_id"])
        self.assertEqual(len(kot2.kot_items), 1)
        
        # Verify all items are now marked as sent to kitchen
        pos_order.reload()
        for item in pos_order.items:
            self.assertEqual(item.sent_to_kitchen, 1)
            self.assertTrue(item.kot_id)


class TestAttributeSummary(FrappeTestCase):
    def test_attribute_summary_valid_input(self):
        """Test get_attribute_summary with valid input."""
        # Test with list of dictionaries
        valid_attrs = [
            {"attribute_name": "Spice Level", "attribute_value": "Medium"},
            {"attribute_name": "Toppings", "attribute_value": "Cheese"}
        ]
        
        summary = get_attribute_summary(valid_attrs)
        self.assertEqual(summary, "Spice Level: Medium, Toppings: Cheese")
        
        # Test with JSON string
        json_attrs = json.dumps(valid_attrs)
        summary = get_attribute_summary(json_attrs)
        self.assertEqual(summary, "Spice Level: Medium, Toppings: Cheese")
    
    def test_attribute_summary_empty_input(self):
        """Test get_attribute_summary with empty input."""
        # Test with empty list
        self.assertEqual(get_attribute_summary([]), "")
        
        # Test with empty JSON string
        self.assertEqual(get_attribute_summary("[]"), "")
        
        # Test with empty string
        self.assertEqual(get_attribute_summary(""), "")
    
    def test_attribute_summary_none_input(self):
        """Test get_attribute_summary with None input."""
        self.assertEqual(get_attribute_summary(None), "")
    
    def test_attribute_summary_malformed_input(self):
        """Test get_attribute_summary with malformed input."""
        # Test with missing attribute_name
        malformed1 = [
            {"wrong_key": "Spice Level", "attribute_value": "Medium"},
            {"attribute_name": "Toppings", "attribute_value": "Cheese"}
        ]
        self.assertEqual(get_attribute_summary(malformed1), "Toppings: Cheese")
        
        # Test with missing attribute_value
        malformed2 = [
            {"attribute_name": "Spice Level", "wrong_value_key": "Medium"},
            {"attribute_name": "Toppings", "attribute_value": "Cheese"}
        ]
        self.assertEqual(get_attribute_summary(malformed2), "Toppings: Cheese")
        
        # Test with completely wrong structure
        malformed3 = [
            {"key1": "value1"},
            {"key2": "value2"}
        ]
        self.assertEqual(get_attribute_summary(malformed3), "")
        
        # Test with invalid JSON string
        self.assertEqual(get_attribute_summary("{invalid json}"), "")
        
        # Test with non-list, non-string input
        self.assertEqual(get_attribute_summary(123), "")