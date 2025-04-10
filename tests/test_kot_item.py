import unittest
import json
import frappe
from pos_restaurant_itb.utils.kot_helpers import get_attribute_summary

class TestKOTItem(unittest.TestCase):
    """Test cases for KOT Item utility functions."""

    def setUp(self):
        """Set up test data."""
        self.valid_attributes = [
            {"attribute_name": "Spice Level", "attribute_value": "Hot"},
            {"attribute_name": "Toppings", "attribute_value": "Cheese"}
        ]
        
        self.valid_json_attributes = json.dumps(self.valid_attributes)
        
        self.valid_with_empty_values = [
            {"attribute_name": "Spice Level", "attribute_value": "Hot"},
            {"attribute_name": "", "attribute_value": "Cheese"},
            {"attribute_name": "Sauce", "attribute_value": ""}
        ]
        
        self.malformed_attributes = [
            {"attribute_wrong_key": "Spice Level", "attribute_value": "Hot"},
            {"attribute_name": "Toppings", "wrong_value_key": "Cheese"},
            {},  # Empty dict
            {"random_key": "random_value"}
        ]

    def test_valid_attributes(self):
        """Test with valid attributes in both list and JSON string formats."""
        # Test with list of dictionaries
        expected_output = "Spice Level: Hot, Toppings: Cheese"
        self.assertEqual(get_attribute_summary(self.valid_attributes), expected_output)
        
        # Test with JSON string
        self.assertEqual(get_attribute_summary(self.valid_json_attributes), expected_output)
        
        # Test with attributes that contain some empty values
        expected_partial = "Spice Level: Hot"
        self.assertEqual(get_attribute_summary(self.valid_with_empty_values), expected_partial)

    def test_empty_list(self):
        """Test with empty list and empty string inputs."""
        # Test with empty list
        self.assertEqual(get_attribute_summary([]), "")
        
        # Test with empty JSON array string
        self.assertEqual(get_attribute_summary("[]"), "")
        
        # Test with empty string
        self.assertEqual(get_attribute_summary(""), "")

    def test_none_input(self):
        """Test with None input."""
        self.assertEqual(get_attribute_summary(None), "")

    def test_malformed_input(self):
        """Test with malformed inputs to ensure function doesn't crash."""
        # Test with malformed attribute dictionary keys
        self.assertEqual(get_attribute_summary(self.malformed_attributes), "")
        
        # Test with non-JSON string
        self.assertEqual(get_attribute_summary("this is not json"), "")
        
        # Test with incomplete JSON
        self.assertEqual(get_attribute_summary("{incomplete json:"), "")
        
        # Test with integer input (completely wrong type)
        self.assertEqual(get_attribute_summary(123), "")
        
        # Test with mixed valid and invalid items
        mixed_attributes = self.valid_attributes + self.malformed_attributes
        expected_output = "Spice Level: Hot, Toppings: Cheese"
        self.assertEqual(get_attribute_summary(mixed_attributes), expected_output)

    def tearDown(self):
        """Clean up after tests."""
        pass


if __name__ == "__main__":
    # This allows running the tests directly from the command line
    unittest.main()