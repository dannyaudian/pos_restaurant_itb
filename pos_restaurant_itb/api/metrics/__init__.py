# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-07 13:50:00'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

"""
POS Restaurant ITB - Metrics API Package
----------------------------------------
This module provides restaurant-specific operational metrics
and configuration loading APIs for dashboards and performance tracking.

Modules:
- load_pos_restaurant_config: POS config loader per POS Profile
- operational_metrics: Dashboard metrics and performance trends
"""

# Configuration Loader
from .load_pos_restaurant_config import (
    load_pos_restaurant_config
)

# Operational Metrics
from .operational_metrics import (
    get_operational_dashboard,
    get_performance_trends
)
