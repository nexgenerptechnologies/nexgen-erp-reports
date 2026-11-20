app_name = "nexgen_erp_reports"
app_title = "NexGen ERP Reports"
app_publisher = "NexGen ERP Technologies"
app_description = "Custom statutory and business reports for ERPNext"
app_email = "info@nexgenerptechnologies.com"
app_license = "MIT"

required_apps = ["frappe", "erpnext"]

# Document Events & Client Hooks
doctype_list_js = {
	"Purchase Invoice": "public/js/purchase_invoice_list_custom.js"
}
