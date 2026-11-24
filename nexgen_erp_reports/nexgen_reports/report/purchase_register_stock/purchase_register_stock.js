// Copyright (c) 2026, NexGen ERP Technologies and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Register Stock"] = {
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
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier"
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "status" && data && data.status) {
			if (data.status === "Paid") {
				return `<span class="indicator-pill green">${value}</span>`;
			} else if (data.status === "Overdue") {
				return `<span class="indicator-pill red">${value}</span>`;
			} else if (data.status === "Unpaid") {
				return `<span class="indicator-pill orange">${value}</span>`;
			}
		}

		return value;
	}
};
