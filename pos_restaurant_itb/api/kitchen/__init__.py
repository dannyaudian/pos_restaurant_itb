# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 13:12:00'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

"""
POS Restaurant ITB - Kitchen API Package
----------------------------------------
This module exposes API functions for kitchen operations including:

- KOT (Kitchen Order Ticket) management
- Kitchen Display System (KDS) dashboard and updates
- Kitchen Station entries generation and updates
- Kitchen analytics and efficiency reports
- POS Order to Kitchen integration

Modules:
- create_kot: Generate KOT from POS Order
- kds: Manage Kitchen Display status and dashboard
- kitchen_station: Manage item-level kitchen execution
- kot_status_update: Sync KOT & KDS item statuses
- kitchen_analytics: Track kitchen performance & reports
- sendkitchenandcancel: Combined API for sending to kitchen & cancelling item
"""

# Create KOT
from .create_kot import (
    create_kot_from_pos_order,
    create_kot_items,
    get_kot_items
)

# Kitchen Display System (KDS)
from .kds import (
    get_kds_dashboard,
    update_order_status
)

# Kitchen Station
from .kitchen_station import (
    create_kitchen_station_items_from_kot
)

# KOT Status Updates
from .kot_status_update import (
    update_kds_status_from_kot,
    bulk_update_kot_status
)

# Kitchen Analytics
from .kitchen_analytics import (
    get_kitchen_performance,
    get_efficiency_report
)

# POS-Kitchen Integration
from .sendkitchenandcancel import (
    send_to_kitchen,
    cancel_pos_order_item,
    mark_all_served
)
