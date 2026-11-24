app_name = "nexgen_erp_reports"
app_title = "NexGen ERP Reports"
app_publisher = "NexGen ERP Technologies"
app_description = "Custom statutory and business reports for ERPNext"
app_email = "info@nexgenerptechnologies.com"
app_license = "MIT"

required_apps = ["frappe", "erpnext"]

# App Setup & Migrations
after_migrate = "nexgen_erp_reports.setup.after_migrate"
after_install = "nexgen_erp_reports.setup.after_migrate"
