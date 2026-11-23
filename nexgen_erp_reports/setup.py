# Copyright (c) 2026, NexGen ERP Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():
    setup_custom_fields()
    tag_expense_invoices()


def tag_expense_invoices():
    """
    Tags all expense purchase invoices and their returns as is_expense_invoice = 1
    so they can be filtered out of regular stock purchase invoice lists.
    """
    if not frappe.db.has_column("Purchase Invoice", "is_expense_invoice"):
        return

    # 1. Tag by line item expense accounts
    frappe.db.sql("""
        UPDATE `tabPurchase Invoice` pi
        JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
        JOIN `tabAccount` acc ON acc.name = pii.expense_account
        SET pi.is_expense_invoice = 1
        WHERE pi.docstatus = 1
          AND acc.root_type = 'Expense'
    """)

    # 2. Tag debit notes / returns whose original invoice is an expense invoice
    frappe.db.sql("""
        UPDATE `tabPurchase Invoice` ret
        JOIN `tabPurchase Invoice` orig ON orig.name = ret.return_against
        SET ret.is_expense_invoice = 1
        WHERE ret.docstatus = 1
          AND ret.is_return = 1
          AND orig.is_expense_invoice = 1
    """)

    # 3. Tag any invoice that already has a linked Expense Invoice document
    if frappe.db.has_column("Purchase Invoice", "expense_invoice"):
        frappe.db.sql("""
            UPDATE `tabPurchase Invoice` pi
            JOIN `tabExpense Invoice` exp ON exp.purchase_invoice = pi.name
            SET pi.is_expense_invoice = 1
        """)

    frappe.db.commit()


def setup_custom_fields():
    custom_fields = {
        "Purchase Invoice": [
            {
                "fieldname": "is_expense_invoice",
                "label": "Is Expense Invoice",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "is_subcontracted",
                "in_standard_filter": 0
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
