# Copyright (c) 2024, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

__created_date__ = '2025-04-06 10:10:50'
__author__ = 'dannyaudian'
__owner__ = 'PT. Innovasi Terbaik Bangsa'

import frappe
from frappe import _
from typing import Optional, Dict, List, Union, Set
from .error_handlers import ValidationError
from .constants import (
    CacheKeys,
    CacheExpiration,
    ErrorMessages,
    OPERATION_ROLES
)

class SecurityManager:
    """Manages security and permission checks for POS operations"""
    
    def __init__(self, user: Optional[str] = None):
        self.user = user or frappe.session.user
        self._roles = None
        self._employee = None
        self._branches = None
        
    @property
    def roles(self) -> Set[str]:
        """Get cached user roles"""
        if self._roles is None:
            self._roles = set(frappe.get_roles(self.user))
        return self._roles
        
    @property
    def is_system_manager(self) -> bool:
        """Check if user is System Manager"""
        return "System Manager" in self.roles
        
    @property
    def employee(self) -> Optional[Dict]:
        """Get cached employee details"""
        if self._employee is None:
            self._employee = frappe.db.get_value(
                "Employee",
                {"user_id": self.user},
                ["name", "branch", "designation"],
                as_dict=True,
                cache=True
            )
        return self._employee
        
    @property
    def branches(self) -> Set[str]:
        """Get cached user branches"""
        if self._branches is None:
            self._branches = self._get_user_branches()
        return self._branches
        
    def _get_user_branches(self) -> Set[str]:
        """Get all branches user has access to"""
        cache_key = CacheKeys.get_key(
            CacheKeys.USER_BRANCHES,
            user=self.user
        )
        
        # Try cache first
        cached = frappe.cache().get_value(cache_key)
        if cached is not None:
            return set(cached)
            
        branches = set()
        
        # System Manager gets all active branches
        if self.is_system_manager:
            branches = {
                b.name for b in frappe.get_all(
                    "Branch",
                    filters={"is_active": 1},
                    fields=["name"],
                    cache=True
                )
            }
        else:
            # Get from employee record
            if self.employee and self.employee.branch:
                branches.add(self.employee.branch)
                
            # Get from branch permissions
            branch_perms = frappe.get_all(
                "User Permission",
                filters={
                    "user": self.user,
                    "allow": "Branch"
                },
                fields=["for_value"],
                cache=True
            )
            branches.update(p.for_value for p in branch_perms)
        
        # Cache result
        frappe.cache().set_value(
            cache_key,
            list(branches),
            expires_in_sec=CacheExpiration.MEDIUM
        )
        
        return branches
        
    def check_branch_access(self, branch: str) -> bool:
        """
        Check if user has access to specific branch
        
        Args:
            branch (str): Branch to check access for
            
        Returns:
            bool: True if user has access
        """
        if not branch:
            return False
            
        if self.is_system_manager:
            return True
            
        return branch in self.branches
        
    def validate_branch_operation(
        self,
        branch: str,
        operation: str
    ) -> None:
        """
        Validate if user can perform operation in branch
        
        Args:
            branch (str): Branch to check
            operation (str): Operation to validate
            
        Raises:
            ValidationError: If operation is not allowed
        """
        # First check branch access
        if not self.check_branch_access(branch):
            raise ValidationError(
                message=ErrorMessages.format(
                    ErrorMessages.BRANCH_ACCESS_DENIED,
                    user=self.user,
                    branch=branch
                ),
                title="Access Denied"
            )
        
        # Then check operation permissions
        allowed_roles = OPERATION_ROLES.get(operation, ["System Manager"])
        
        if not any(role in self.roles for role in allowed_roles):
            raise ValidationError(
                message=ErrorMessages.format(
                    ErrorMessages.OPERATION_DENIED,
                    operation=operation,
                    roles=", ".join(allowed_roles)
                ),
                title="Permission Denied"
            )
            
    def validate_pos_permission(
        self,
        doc_type: str,
        doc: Union[str, Dict],
        ptype: Optional[str] = None
    ) -> bool:
        """
        Validate POS related permissions
        
        Args:
            doc_type (str): Document type
            doc (Union[str, Dict]): Document name or dict
            ptype (str, optional): Permission type
            
        Returns:
            bool: True if permitted
        """
        if self.is_system_manager:
            return True
            
        # Get document if name provided
        if isinstance(doc, str):
            doc = frappe.get_doc(doc_type, doc)
            
        if not self.employee:
            return False
            
        # Branch level check
        if hasattr(doc, 'branch'):
            if not self.check_branch_access(doc.branch):
                return False
                
        # Role based permissions
        if "Outlet Manager" in self.roles:
            return True
            
        elif "Waiter" in self.roles:
            if doc_type == "POS Order":
                return doc.created_by == self.user
            return True
            
        elif "Cashier" in self.roles:
            if doc_type == "POS Order":
                return doc.status in ["Ready for Billing", "Completed"]
            return True
            
        return False

# Module level functions that use SecurityManager
def check_branch_access(user: str, branch: str) -> bool:
    """Wrapper for SecurityManager.check_branch_access"""
    return SecurityManager(user).check_branch_access(branch)

def validate_branch_operation(
    branch: str,
    operation: str,
    user: Optional[str] = None
) -> None:
    """Wrapper for SecurityManager.validate_branch_operation"""
    SecurityManager(user).validate_branch_operation(branch, operation)

def validate_pos_permission(
    doc_type: str,
    doc: Union[str, Dict],
    user: Optional[str] = None,
    ptype: Optional[str] = None
) -> bool:
    """Wrapper for SecurityManager.validate_pos_permission"""
    return SecurityManager(user).validate_pos_permission(doc_type, doc, ptype)

def get_user_branch_list(user: Optional[str] = None) -> List[str]:
    """Get list of branches user has access to"""
    return list(SecurityManager(user).branches)

def clear_security_cache(user: Optional[str] = None) -> None:
    """Clear security related caches"""
    user = user or frappe.session.user
    frappe.cache().delete_value(
        CacheKeys.get_key(CacheKeys.USER_BRANCHES, user=user)
    )