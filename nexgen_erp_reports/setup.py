# Copyright (c) 2026, NexGen ERP Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():
    setup_custom_fields()


def setup_custom_fields():
    custom_fields = {
        "Purchase Invoice": [
            {
                "fieldname": "is_expense_invoice",
                "label": "Is Expense Invoice",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "is_subcontracted",
                "in_standard_filter": 1
            },
            {
                "fieldname": "expense_invoice",
                "label": "Expense Invoice Reference",
                "fieldtype": "Link",
                "options": "Expense Invoice",
                "insert_after": "is_expense_invoice",
                "read_only": 1
            }
        ],
        "Supplier": [
            {
                "fieldname": "msme_section",
                "label": "MSME Details",
                "fieldtype": "Section Break",
                "insert_after": "tax_id",
                "collapsible": 1
            },
            {
                "fieldname": "msme_status",
                "label": "MSME Status",
                "fieldtype": "Select",
                "options": "\nMicro\nSmall\nMedium\nNot Applicable",
                "default": "",
                "insert_after": "msme_section",
                "in_standard_filter": 1
            },
            {
                "fieldname": "udyam_no",
                "label": "Udyam Registration No.",
                "fieldtype": "Data",
                "insert_after": "msme_status"
            },
            {
                "fieldname": "msme_registration_date",
                "label": "MSME Registration Date",
                "fieldtype": "Date",
                "insert_after": "udyam_no"
            }
        ]
    }
    create_custom_fields(custom_fields, ignore_validate=True)
