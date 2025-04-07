# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 17:30:00'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

"""
POS Restaurant ITB - Table Management API Package
-------------------------------------------------
Provides APIs for handling table availability, status updates,
analytics, and reservations.

Modules:
- get_available_tables: Table availability and metadata per branch
- table_status: Table status update, status log, analytics
"""

# Table Availability
from .get_available_tables import (
    get_available_tables,
    get_table_status as get_table_status_detail
)

# Table Status Management
from .table_status import (
    update_table_status,
    get_table_status,
    get_table_analytics
)
