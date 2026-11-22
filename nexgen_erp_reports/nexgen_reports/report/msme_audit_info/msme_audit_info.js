frappe.query_reports["MSME Audit Info"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: (function() {
				let today = frappe.datetime.get_today();
				let parts = today.split("-");
				let year = parseInt(parts[0], 10);
				let month = parseInt(parts[1], 10);
				let fy_year = month >= 4 ? year : year - 1;
				return fy_year + "-04-01";
			})(),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "date_basis",
			label: __("On Basis of"),
			fieldtype: "Select",
			options: "Bill Date\nPosting Date",
			default: "Bill Date",
			reqd: 1
		},
		{
			fieldname: "as_on_date",
			label: __("Bills Status as on"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "msme_filter",
			label: __("MSME Category"),
			fieldtype: "Select",
			options: "All MSME (Micro & Small & Medium)\nMicro & Small (Sec 43B(h))\nMicro\nSmall\nMedium\nAll Suppliers",
			default: "All MSME (Micro & Small & Medium)"
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier"
		}
	],

	onload: function(report) {
		// Disable built-in Datatable bottom total row to avoid duplicate summing
		if (report.raw_data) {
			report.raw_data.add_total_row = 0;
		}
		frappe.dom.set_style(`
			.query-report[data-report-name="MSME Audit Info"] .dt-footer,
			.query-report[data-report-name="MSME Audit Info"] .dt-row-total {
				display: none !important;
			}
		`);

		// Download Excel Action
		report.page.add_inner_button(__("Download MSME Excel"), function() {
			const filters = report.get_values();
			if (!filters.company) {
				frappe.msgprint(__("Please select Company first."));
				return;
			}
			const query_string = encodeURIComponent(JSON.stringify(filters));
			const download_url = `/api/method/nexgen_erp_reports.nexgen_reports.report.msme_audit_info.msme_audit_info.download_custom_excel?filters=${query_string}`;
			window.open(download_url, "_blank");
		});
	},

	get_datatable_options: function(options) {
		return Object.assign(options, {
			showTotalRow: false
		});
	},

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		// Total summary row highlight
		if (data.is_total_row) {
			return `<strong style="color: #1e3a8a; font-size: 12px;">${value}</strong>`;
		}

		// Highlight On-Time Paid amounts (<= 45 days) in green
		if ((column.fieldname === "other_amt" || column.fieldname === "treds_amt") && flt(data[column.fieldname]) > 0) {
			return `<span style="color: #059669; font-weight: 500;">${value}</span>`;
		}

		// Highlight Delayed Paid amounts (> 45 days) in orange
		if (column.fieldname === "delayed_amt" && flt(data.delayed_amt) > 0) {
			return `<span style="color: #d97706; font-weight: 500;">${value}</span>`;
		}

		// Highlight Critical Overdue Pending (> 45 days) in RED (43B(h) Disallowance Risk)
		if ((column.fieldname === "overdue_45_amt" || column.fieldname === "overdue_45_count") && flt(data.overdue_45_amt) > 0) {
			return `<strong style="color: #dc2626; background: #fee2e2; padding: 2px 6px; border-radius: 4px;">${value}</strong>`;
		}

		return value;
	}
};
