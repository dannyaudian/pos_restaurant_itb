# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

"""
Realtime Utilities for POS Restaurant ITB
-----------------------------------------
This module handles broadcasting realtime updates via Redis (Socket.IO pubsub)
for QR Order Sessions, Tables, Kitchen Stations, and other interactive components.
"""

import frappe
import json

CHANNEL_PREFIX = "pos_restaurant_itb"


def notify_session_update(session_id: str, payload: dict):
    """
    Broadcast realtime update for a specific QR Session.

    Args:
        session_id (str): Unique session ID (e.g., "QR-SESSION-001").
        payload (dict): Data to send to frontend.
    """
    if not session_id or not isinstance(payload, dict):
        return

    message = {
        "type": "session_update",
        "session_id": session_id,
        "payload": payload,
    }

    _publish_realtime(f"session:{session_id}", message)


def notify_table_status(table_id: str, payload: dict):
    """
    Broadcast update for a specific Table (e.g., occupied, merged, etc).

    Args:
        table_id (str): Table name / ID (e.g., "T01__JKT").
        payload (dict): Update data to broadcast.
    """
    if not table_id or not isinstance(payload, dict):
        return

    message = {
        "type": "table_update",
        "table_id": table_id,
        "payload": payload,
    }

    _publish_realtime(f"table:{table_id}", message)


def notify_order_update(order_id: str, payload: dict):
    """
    Broadcast POS/QR Order update.

    Args:
        order_id (str): POS Order / QR Order name (e.g., "POS-001").
        payload (dict): Payload containing update data.
    """
    if not order_id or not isinstance(payload, dict):
        return

    message = {
        "type": "order_update",
        "order_id": order_id,
        "payload": payload,
    }

    _publish_realtime(f"order:{order_id}", message)


def notify_kitchen_status(station_id: str, payload: dict):
    """
    Notify Kitchen Station about item status changes.

    Args:
        station_id (str): Kitchen Station name.
        payload (dict): Payload to send.
    """
    if not station_id or not isinstance(payload, dict):
        return

    message = {
        "type": "kitchen_status",
        "station_id": station_id,
        "payload": payload,
    }

    _publish_realtime(f"kitchen:{station_id}", message)


def broadcast_to_kitchen(branch: str, payload: dict):
    """
    Broadcast message to all kitchen listeners in a specific branch.

    Args:
        branch (str): Branch code (e.g., "JKT").
        payload (dict): General update (e.g., KOT created).
    """
    if not branch or not isinstance(payload, dict):
        return

    message = {
        "type": "broadcast_kitchen",
        "branch": branch,
        "payload": payload,
    }

    _publish_realtime(f"broadcast:kitchen:{branch}", message)


def _publish_realtime(channel: str, message: dict):
    """
    Internal helper to publish message to Redis channel.

    Args:
        channel (str): The Redis pubsub channel (suffix only).
        message (dict): Message content.
    """
    try:
        redis = frappe.cache()
        full_channel = f"{CHANNEL_PREFIX}:{channel}"
        redis.publish(full_channel, json.dumps(message))
        frappe.logger("realtime").info(f"[Realtime] Published to {full_channel}: {json.dumps(message)}")
    except Exception as e:
        frappe.logger("realtime").error(f"[Realtime] Failed to publish to {channel}: {e}")
