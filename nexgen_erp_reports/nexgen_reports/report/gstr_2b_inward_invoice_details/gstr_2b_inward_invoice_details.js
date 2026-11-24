// Copyright (c) 2026, NexGen ERP Technologies and contributors
// For license information, please see license.txt

frappe.query_reports["GSTR-2B Inward Invoice Details"] = {
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
			label: __("GSTR-2B Section"),
			fieldtype: "Select",
			options: "\nAll Sections\n3_4A\n4B\n6C\n6C_UR\n5A_5B\n4C\n7A_7B\nITC_REV",
			default: "All Sections"
		},
		{
			fieldname: "supply_type",
			label: __("Supply Type"),
			fieldtype: "Select",
			options: "All\nStock Purchase\nExpense Invoice",
			default: "All"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "supply_type" && data && data.supply_type) {
			if (data.supply_type === "Expense Invoice") {
				return `<span class="badge badge-warning" style="background-color: #fef3c7; color: #92400e; padding: 3px 6px; border-radius: 4px; font-weight: 500;">${value}</span>`;
			} else {
				return `<span class="badge badge-success" style="background-color: #d1fae5; color: #065f46; padding: 3px 6px; border-radius: 4px; font-weight: 500;">${value}</span>`;
			}
		}

		return value;
	}
};
