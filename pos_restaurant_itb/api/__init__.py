# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 08:16:01'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _

"""
POS Restaurant ITB - API Module
-----------------------------
Collection of API endpoints and utilities for POS Restaurant ITB.

Modules:
- kitchen: Kitchen display and order management APIs
- pos: POS operations and transaction APIs  
- qr: QR code order management APIs
- table: Table management APIs
"""

# Import submodules
from . import pos, qr, table

# Lazy load kitchen module to avoid circular imports
def get_kitchen_module():
    from . import kitchen
    return kitchen

def create_kot_from_pos_order(*args, **kwargs):
    kitchen = get_kitchen_module()
    return kitchen.create_kot.create_kot_from_pos_order(*args, **kwargs)

def update_kot_status(*args, **kwargs):
    kitchen = get_kitchen_module()
    return kitchen.update_kot.update_kot_status(*args, **kwargs)

def get_kot_details(*args, **kwargs):
    kitchen = get_kitchen_module()
    return kitchen.get_kot.get_kot_details(*args, **kwargs)

# Version and metadata
__version__ = '1.0.0'

# Module exports
__all__ = [
    'pos',
    'qr',
    'table',
    'create_kot_from_pos_order',
    'update_kot_status',
    'get_kot_details'
]