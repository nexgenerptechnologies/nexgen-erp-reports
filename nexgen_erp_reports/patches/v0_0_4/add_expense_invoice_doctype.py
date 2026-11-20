import os
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.modules.import_file import import_file_by_path

def execute():
    # 1. Create custom fields on Purchase Invoice
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
        ]
    }
    create_custom_fields(custom_fields, ignore_validate=True)

    # 2. Import Child Table: Expense Invoice Item
    item_json = frappe.get_app_path("nexgen_erp_reports", "nexgen_reports", "doctype", "expense_invoice_item", "expense_invoice_item.json")
    if os.path.exists(item_json):
        import_file_by_path(item_json, force=True)

    # 3. Import Main DocType: Expense Invoice
    exp_json = frappe.get_app_path("nexgen_erp_reports", "nexgen_reports", "doctype", "expense_invoice", "expense_invoice.json")
    if os.path.exists(exp_json):
        import_file_by_path(exp_json, force=True)

    # 4. Run historical sync for existing expense/service purchase invoices
    try:
        from nexgen_erp_reports.nexgen_reports.doctype.expense_invoice.expense_invoice import sync_past_expense_invoices
        sync_past_expense_invoices()
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Sync past expense invoices patch notice")
