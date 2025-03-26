import frappe
from frappe.utils import now_datetime

def log_kitchen_sla(kot_item):
    now = now_datetime()
    sla_log = frappe.new_doc("Kitchen SLA Log")
    sla_log.item_code = kot_item.item_code
    sla_log.kot_reference = kot_item.parent
    sla_log.status = kot_item.kot_status
    if kot_item.kot_status == "Cooking":
        sla_log.start_time = now
    elif kot_item.kot_status == "Ready":
        sla_log.end_time = now
    sla_log.insert()
