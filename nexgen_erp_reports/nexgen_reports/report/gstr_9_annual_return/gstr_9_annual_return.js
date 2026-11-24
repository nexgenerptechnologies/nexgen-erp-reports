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

			// Table 17: HSN Outward Supplies -> Item-wise Sales Register
			if (sectionCode === "17") {
				if (window.history && window.history.replaceState) {
					window.history.replaceState({}, document.title, window.location.pathname);
				}
				frappe.route_options = {
					company: filters.company,
					from_date: filters.from_date,
					to_date: filters.to_date
				};
				frappe.set_route("query-report", "Item-wise Sales Register");
				return;
			}

			// Table 18: HSN Inward Supplies -> Item-wise Purchase Register
			if (sectionCode === "18") {
				if (window.history && window.history.replaceState) {
					window.history.replaceState({}, document.title, window.location.pathname);
				}
				frappe.route_options = {
					company: filters.company,
					from_date: filters.from_date,
					to_date: filters.to_date
				};
				frappe.set_route("query-report", "Item-wise Purchase Register");
				return;
			}

			// Outward Sections -> Sales Invoice
			const salesSections = ["4A", "4B", "4C", "4D", "4E", "4I", "4J", "5A", "5B", "5C", "5D", "5E", "5F", "5H"];
			const purchaseSections = ["6B", "6C", "6D", "6E", "6F", "7E", "16A"];

			if (salesSections.includes(sectionCode)) {
				const route_params = {
					company: filters.company,
					docstatus: 1
				};

				if (filters.from_date && filters.to_date) {
					route_params["posting_date"] = ["between", [filters.from_date, filters.to_date]];
				}

				if (sectionCode === "4A") {
					route_params["gst_category"] = "Unregistered";
					route_params["is_return"] = 0;
				} else if (sectionCode === "4B") {
					route_params["gst_category"] = ["in", ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]];
					route_params["is_return"] = 0;
				} else if (sectionCode === "4C" || sectionCode === "5A") {
					route_params["gst_category"] = "Overseas";
					route_params["is_return"] = 0;
				} else if (sectionCode === "4D" || sectionCode === "5B") {
					route_params["gst_category"] = "SEZ";
					route_params["is_return"] = 0;
				} else if (sectionCode === "4E") {
					route_params["gst_category"] = "Deemed Export";
					route_params["is_return"] = 0;
				} else if (sectionCode === "4I" || sectionCode === "5H") {
					route_params["is_return"] = 1;
				} else if (sectionCode === "5D") {
					route_params["gst_category"] = "Exempt";
					route_params["is_return"] = 0;
				} else if (sectionCode === "5E") {
					route_params["gst_category"] = "Nil Rated";
					route_params["is_return"] = 0;
				}

				if (window.history && window.history.replaceState) {
					window.history.replaceState({}, document.title, window.location.pathname);
				}

				frappe.route_options = route_params;
				frappe.set_route("List", "Sales Invoice");
			} else if (purchaseSections.includes(sectionCode)) {
				const route_params = {
					company: filters.company,
					docstatus: 1
				};

				if (filters.from_date && filters.to_date) {
					route_params["posting_date"] = ["between", [filters.from_date, filters.to_date]];
				}

				if (sectionCode === "6B") {
					route_params["gst_category"] = ["in", ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]];
					route_params["is_return"] = 0;
				} else if (sectionCode === "6C") {
					route_params["gst_category"] = "Unregistered";
					route_params["reverse_charge"] = "Y";
				} else if (sectionCode === "6D") {
					route_params["reverse_charge"] = "Y";
				} else if (sectionCode === "6E" || sectionCode === "6F") {
					route_params["gst_category"] = "Overseas";
				} else if (sectionCode === "7E") {
					route_params["eligibility_for_itc"] = ["like", "%Ineligible%"];
				} else if (sectionCode === "16A") {
					route_params["gst_category"] = "Composition";
				}

				if (window.history && window.history.replaceState) {
					window.history.replaceState({}, document.title, window.location.pathname);
				}

				frappe.route_options = route_params;
				frappe.set_route("List", "Purchase Invoice");
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
