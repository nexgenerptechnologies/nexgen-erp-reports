// Copyright (c) 2026, NexGen ERP Technologies and contributors
// For license information, please see license.txt

frappe.query_reports["GSTR-9 Outward Invoice Details"] = {
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
			fieldname: "section_code",
			label: __("GSTR-9 Section"),
			fieldtype: "Select",
			options: "\nAll Sections\n4A\n4B\n4C\n4D\n4E\n4I\n4J\n5A\n5B\n5C\n5D\n5E\n5F\n5H\n5I",
			default: "All Sections"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "section_name" && data && data.section_name) {
			return `<span style="font-weight: 500; color: #1e3a8a;">${value}</span>`;
		}

		return value;
	}
};
