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

		// Attach click listener for GSTR-9 drill-down
		$(report.page.wrapper).on("click", ".gstr9-section-drilldown", function(e) {
			e.preventDefault();
			const sectionCode = $(this).attr("data-section");
			const filters = report.get_values();

			// Outward Sections -> Sales Invoice
			const salesSections = ["4A", "4B", "4C", "4D", "4E", "4I", "4J", "5A", "5B", "5C", "5D", "5E", "5F", "5H", "17"];
			const purchaseSections = ["6B", "6C", "6D", "6E", "6F", "7E", "16A", "18"];

			if (salesSections.includes(sectionCode)) {
				const filterList = [
					["Sales Invoice", "company", "=", filters.company],
					["Sales Invoice", "docstatus", "=", 1]
				];

				if (filters.from_date && filters.to_date) {
					filterList.push(["Sales Invoice", "posting_date", "between", [filters.from_date, filters.to_date]]);
				}

				if (sectionCode === "4A") {
					filterList.push(["Sales Invoice", "gst_category", "=", "Unregistered"]);
					filterList.push(["Sales Invoice", "is_return", "=", 0]);
				} else if (sectionCode === "4B") {
					filterList.push(["Sales Invoice", "gst_category", "in", ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]]);
					filterList.push(["Sales Invoice", "is_return", "=", 0]);
				} else if (sectionCode === "4C" || sectionCode === "5A") {
					filterList.push(["Sales Invoice", "gst_category", "=", "Overseas"]);
				} else if (sectionCode === "4D" || sectionCode === "5B") {
					filterList.push(["Sales Invoice", "gst_category", "=", "SEZ"]);
				} else if (sectionCode === "4E") {
					filterList.push(["Sales Invoice", "gst_category", "=", "Deemed Export"]);
				} else if (sectionCode === "4I" || sectionCode === "5H") {
					filterList.push(["Sales Invoice", "is_return", "=", 1]);
				} else if (sectionCode === "5D") {
					filterList.push(["Sales Invoice", "gst_category", "=", "Exempt"]);
				} else if (sectionCode === "5E") {
					filterList.push(["Sales Invoice", "gst_category", "=", "Nil Rated"]);
				}

				frappe.route_options = null;
				frappe.set_route("List", "Sales Invoice", {
					filters: JSON.stringify(filterList)
				});
			} else if (purchaseSections.includes(sectionCode)) {
				const filterList = [
					["Purchase Invoice", "company", "=", filters.company],
					["Purchase Invoice", "docstatus", "=", 1]
				];

				if (filters.from_date && filters.to_date) {
					filterList.push(["Purchase Invoice", "posting_date", "between", [filters.from_date, filters.to_date]]);
				}

				if (sectionCode === "6B") {
					filterList.push(["Purchase Invoice", "gst_category", "in", ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]]);
					filterList.push(["Purchase Invoice", "is_return", "=", 0]);
				} else if (sectionCode === "6C") {
					filterList.push(["Purchase Invoice", "gst_category", "=", "Unregistered"]);
					filterList.push(["Purchase Invoice", "reverse_charge", "=", "Y"]);
				} else if (sectionCode === "6D") {
					filterList.push(["Purchase Invoice", "reverse_charge", "=", "Y"]);
				} else if (sectionCode === "6E" || sectionCode === "6F") {
					filterList.push(["Purchase Invoice", "gst_category", "=", "Overseas"]);
				} else if (sectionCode === "7E") {
					filterList.push(["Purchase Invoice", "eligibility_for_itc", "like", "%Ineligible%"]);
				} else if (sectionCode === "16A") {
					filterList.push(["Purchase Invoice", "gst_category", "=", "Composition"]);
				}

				frappe.route_options = null;
				frappe.set_route("List", "Purchase Invoice", {
					filters: JSON.stringify(filterList)
				});
			}
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

		// Clickable drilldown for section rows
		if (column.fieldname === "section_name" && data.section_code) {
			return `<a href="javascript:void(0);" 
			           class="gstr9-section-drilldown" 
			           data-section="${data.section_code}" 
			           title="Click to view vouchers in List View" 
			           style="color: #1a56db; font-weight: 500; text-decoration: underline; cursor: pointer;">
			           ${value}
			        </a>`;
		}

		// Grand Total rows
		if (data.is_grandtotal) {
			return `<strong style="color: #047857; font-weight: bold;">${value}</strong>`;
		}

		// Subtotal rows
		if (data.is_subtotal) {
			return `<strong style="color: #1f2937;">${value}</strong>`;
		}

		return value;
	}
};
