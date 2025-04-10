import frappe
from frappe import _
from frappe.model.document import Document

class KitchenStationSetup(Document):
    def autoname(self):
        """
        Sets the name based on the station_name field
        """
        # This is already configured in the JSON schema
        # This method is here for any additional processing if needed
        pass

    def validate(self):
        """
        Validates the Kitchen Station Setup configuration
        """
        # Ensure the branch is active
        branch_is_active = frappe.db.get_value("Branch", self.branch, "is_active")
        if not branch_is_active:
            frappe.throw(_("Selected branch is not active."))
        
        # Validate that at least one item group is specified
        if not self.allow_all_item_groups and not self.item_group:
            frappe.throw(_("Please specify at least one item group for routing."))
        
        # Check for duplicate item groups in additional_item_groups
        if self.additional_item_groups:
            groups = [row.item_group for row in self.additional_item_groups]
            if len(groups) != len(set(groups)):
                frappe.throw(_("Duplicate item groups found in additional item groups."))
            
            # Check if primary item group is also in additional groups
            if self.item_group in groups:
                frappe.throw(_("Primary item group should not be included in additional item groups."))
        
        # Validate printer mappings
        self.validate_printer_mappings()
        
        # Set display name if not provided
        if not self.station_display_name:
            self.station_display_name = self.station_name
    
    def validate_printer_mappings(self):
        """
        Validates printer mappings
        """
        # Check if at least one printer is specified if print_format is selected
        if self.print_format and not self.default_printer and not self.assigned_printers:
            frappe.throw(_("Please specify at least one printer when a print format is selected."))
        
        # Check for default printer conflicts
        if self.assigned_printers:
            default_printers = [p for p in self.assigned_printers if p.is_default]
            if len(default_printers) > 1:
                frappe.throw(_("Only one printer can be set as default."))
            
            # If we have a default printer in assigned_printers, ensure it matches default_printer
            if default_printers and self.default_printer:
                if default_printers[0].printer != self.default_printer:
                    frappe.msgprint(
                        _("Default printer in assigned printers doesn't match the main default printer. Using {0} as default.").format(
                            default_printers[0].printer
                        )
                    )
                    self.default_printer = default_printers[0].printer
    
    def is_valid_ip(self, ip):
        """
        Validates an IP address format
        """
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False