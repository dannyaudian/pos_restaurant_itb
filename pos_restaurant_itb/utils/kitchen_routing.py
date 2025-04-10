# File: pos_restaurant_itb/utils/kitchen_routing.py

import frappe
from frappe import _

def get_kitchen_stations_for_item(item_code, branch):
    """
    Determines which kitchen stations should handle the specified item.
    
    Args:
        item_code: The item code to route
        branch: The branch where the order is placed
        
    Returns:
        List of kitchen station names that should handle this item
    """
    if not item_code or not branch:
        return []
    
    # Get the item group for this item
    item_group = frappe.db.get_value("Item", item_code, "item_group")
    if not item_group:
        return []
    
    # Find active kitchen stations for this branch
    stations = []
    
    # First find stations that handle all item groups
    all_item_stations = frappe.get_all(
        "Kitchen Station Setup",
        filters={
            "branch": branch,
            "is_active": 1,
            "allow_all_item_groups": 1
        },
        fields=["name", "station_name"]
    )
    stations.extend([s.name for s in all_item_stations])
    
    # Then find stations that specifically handle this item group
    primary_group_stations = frappe.get_all(
        "Kitchen Station Setup",
        filters={
            "branch": branch,
            "is_active": 1,
            "item_group": item_group
        },
        fields=["name", "station_name"]
    )
    stations.extend([s.name for s in primary_group_stations if s.name not in stations])
    
    # Finally, check stations that have this item group as an additional group
    additional_group_stations = frappe.db.sql("""
        SELECT p.name, p.station_name 
        FROM `tabKitchen Station Setup` p
        INNER JOIN `tabKitchen Station Item Group` c ON c.parent = p.name
        WHERE p.branch = %s
        AND p.is_active = 1
        AND c.item_group = %s
        AND p.name NOT IN %s
    """, (branch, item_group, stations or ["***"]), as_dict=1)
    
    stations.extend([s.name for s in additional_group_stations if s.name not in stations])
    
    return stations

def get_printers_for_kitchen_station(station_name):
    """
    Gets the list of printers assigned to a kitchen station
    
    Args:
        station_name: The name of the kitchen station
        
    Returns:
        List of printer configurations as dictionaries
    """
    if not station_name:
        return []
    
    station = frappe.get_doc("Kitchen Station Setup", station_name)
    printers = []
    
    # Add the default printer first, if specified
    if station.default_printer:
        printer_doc = frappe.get_doc("Printer Mapping POS Restaurant", station.default_printer)
        printers.append({
            "printer_name": printer_doc.name,
            "printer_type": printer_doc.printer_type,
            "ip_address": printer_doc.ip_address if printer_doc.printer_type == "Network" else None,
            "port": printer_doc.port if printer_doc.printer_type == "Network" else None,
            "print_format": station.print_format,
            "is_default": 1
        })
    
    # Add assigned printers
    if station.assigned_printers:
        for p in station.assigned_printers:
            # Skip if it's the same as default printer
            if station.default_printer and p.printer == station.default_printer:
                continue
                
            printer_doc = frappe.get_doc("Printer Mapping POS Restaurant", p.printer)
            printers.append({
                "printer_name": printer_doc.name,
                "printer_type": printer_doc.printer_type,
                "ip_address": printer_doc.ip_address if printer_doc.printer_type == "Network" else None,
                "port": printer_doc.port if printer_doc.printer_type == "Network" else None,
                "print_format": p.print_format or station.print_format,
                "is_default": p.is_default
            })
    
    return printers