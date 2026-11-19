frappe.query_reports["GSTR-9 Annual Return"] = {
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
			default: frappe.datetime.year_start(),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		}
	],

	onload: function(report) {
		// Custom Action Button for Formatted GSTR-9 Excel Download
		report.page.add_inner_button(__("Download GSTR-9 Excel"), function() {
			const filters = report.get_values();
			if (!filters.company) {
				frappe.msgprint(__("Please select Company first."));
				return;
			}
			const query_string = encodeURIComponent(JSON.stringify(filters));
			const download_url = `/api/method/nexgen_erp_reports.nexgen_reports.report.gstr_9_annual_return.gstr_9_annual_return.download_custom_excel?filters=${query_string}`;
			window.open(download_url, "_blank");
		});
	},

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		// Blank separator rows
		if (data.is_blank) {
			return "";
		}

		// Table Header row (e.g., Table 4, 5, 6, 7, 8, 16)
		if (data.is_header) {
			if (column.fieldname === "section_name") {
				return `<strong style="color: #1e3a8a; font-size: 13px;">${value}</strong>`;
			}
			return "";
		}

		// Grand Total rows (e.g. 4N, 5N, 6O, 7J, 8K, Total Turnover, 17, 18)
		if (data.is_grandtotal) {
			return `<strong style="color: #047857; font-weight: bold;">${value}</strong>`;
		}

		// Subtotal rows (e.g. 4H, 4M, 5G, 5L, 5M, 6I, 6N, 7I)
		if (data.is_subtotal) {
			return `<strong style="color: #1f2937;">${value}</strong>`;
		}

		return value;
	}
};
