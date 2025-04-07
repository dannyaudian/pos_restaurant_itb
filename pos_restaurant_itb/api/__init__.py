# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 08:16:01'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _

"""
POS Restaurant ITB - API Module
-------------------------------
Collection of API endpoints and utilities for POS Restaurant ITB.

Submodules:
- kitchen: Kitchen display, station, and order integration
- pos: POS operations (order creation, billing, status updates)
- qr: QR ordering system (order, session, payment)
- table: Table management (availability, status)
- order: Attribute, splitting, analytics, voiding
- metrics: Operational and dashboard metrics
- queue: Kitchen queue manager
"""

# Core submodules (non-circular)
from . import pos, qr, table, order, metrics, queue

# Lazy-load circular modules
def get_kitchen_module():
    from . import kitchen
    return kitchen

# API Proxy Shortcuts
def create_kot_from_pos_order(*args, **kwargs):
    return get_kitchen_module().create_kot_from_pos_order(*args, **kwargs)

def update_kot_status(*args, **kwargs):
    return get_kitchen_module().kot_status_update.update_kds_status_from_kot(*args, **kwargs)

def get_kot_details(*args, **kwargs):
    # Misal fungsi ini tersedia dalam kitchen/kds.py (disesuaikan)
    return get_kitchen_module().kds.get_kds_dashboard(*args, **kwargs)

# Versioning
__version__ = '1.0.0'

# Public exports
__all__ = [
    'pos',
    'qr',
    'table',
    'order',
    'metrics',
    'queue',
    'create_kot_from_pos_order',
    'update_kot_status',
    'get_kot_details'
]
