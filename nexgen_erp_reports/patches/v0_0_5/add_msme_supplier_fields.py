import os
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.modules.import_file import import_file_by_path

def execute():
    # 1. Add MSME custom fields to Supplier Master
    custom_fields = {
        "Supplier": [
            {
                "fieldname": "msme_section",
                "label": "MSME Details",
                "fieldtype": "Section Break",
                "insert_after": "pan" if frappe.db.has_column("Supplier", "pan") else "tax_id"
            },
            {
                "fieldname": "msme_status",
                "label": "MSME Status",
                "fieldtype": "Select",
                "options": "\nMicro\nSmall\nMedium\nNot Applicable",
                "default": "",
                "in_standard_filter": 1,
                "in_list_view": 1,
                "insert_after": "msme_section"
            },
            {
                "fieldname": "udyam_no",
                "label": "Udyam Registration No.",
                "fieldtype": "Data",
                "description": "e.g. UDYAM-XX-00-0000000",
                "in_standard_filter": 1,
                "in_list_view": 1,
                "insert_after": "msme_status"
            },
            {
                "fieldname": "col_break_msme",
                "fieldtype": "Column Break",
                "insert_after": "udyam_no"
            },
            {
                "fieldname": "msme_registration_date",
                "label": "MSME Registration Date",
                "fieldtype": "Date",
                "insert_after": "col_break_msme"
            }
        ]
    }
    create_custom_fields(custom_fields, ignore_validate=True)

    # 2. Auto-import MSME Audit Info report definition
    report_json = frappe.get_app_path("nexgen_erp_reports", "nexgen_reports", "report", "msme_audit_info", "msme_audit_info.json")
    if os.path.exists(report_json):
        import_file_by_path(report_json, force=True)

    # 3. Ensure add_total_row is 0 to avoid Datatable summing running balances
    if frappe.db.exists("Report", "MSME Audit Info"):
        frappe.db.set_value("Report", "MSME Audit Info", "add_total_row", 0)
