import frappe
from frappe import _
from hrms.hr.doctype.employee_advance import employee_advance

class EmployeeAdvanceOverride(employee_advance.EmployeeAdvance):
    def validate_advance_account_type(self):
        """Custom validation to allow Receivable or other allowed types"""
        account_type = frappe.db.get_value("Account", self.advance_account, "account_type")
        
        allowed_types = ["Receivable", "Payable"]
        
        if account_type not in allowed_types:
            frappe.throw(
                _("Employee advance account {0} should be of type {1}.").format(
                    frappe.utils.get_link_to_form("Account", self.advance_account),
                    frappe.bold(", ".join(allowed_types))
                )
            )

