import os
import frappe

def execute():
    try:
        from frappe.modules.import_file import import_file_by_path
        report_json = frappe.get_app_path("nexgen_erp_reports", "nexgen_reports", "report", "combined_party_ledger", "combined_party_ledger.json")
        if os.path.exists(report_json):
            import_file_by_path(report_json, force=True)
        frappe.db.set_value("Report", "Combined Party Ledger", "add_total_row", 0)
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Auto-import Combined Party Ledger failed")
