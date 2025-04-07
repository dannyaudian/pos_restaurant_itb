# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 15:14:00'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

"""
POS Restaurant ITB - Order API Package
--------------------------------------
This module contains API endpoints and logic for handling POS Orders:

- Attribute resolution
- Analytics and insights
- Order notes
- Order splitting
- Order voiding
- Variant selection and pricing
"""

# Attribute Access
from .get_attributes_for_item import get_attributes_for_item

# Analytics
from .order_analytics import (
    get_order_analytics,
    get_comparative_analytics
)

# Notes
from .order_notes import (
    add_order_note,
    get_order_notes,
    update_note,
    delete_note,
    get_note_templates
)

# Splitting
from .order_splitting import (
    split_order,
    get_split_preview
)

# Voiding
from .order_voiding import (
    void_order,
    get_void_report
)

# Variant Resolution
from .resolve_variant import resolve_variant
