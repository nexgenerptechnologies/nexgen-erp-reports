import frappe

def execute():
    # Remove the invalid report name with parentheses if it exists in the database
    old_report_name = "Ageing Receivables (FIFO Basis)"
    if frappe.db.exists("Report", old_report_name):
        frappe.delete_doc("Report", old_report_name, ignore_permissions=True, force=True)
