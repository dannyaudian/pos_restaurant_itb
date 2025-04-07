# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 17:04:00'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

"""
POS Restaurant ITB - Queue Management API Package
-------------------------------------------------
API interface for managing real-time kitchen queues including:

- Fetching kitchen queue list
- Updating order priority
- Queue analytics and performance tracking
"""

from .queue_manager import (
    get_kitchen_queue,
    update_order_priority,
    get_queue_analytics
)
