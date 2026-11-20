frappe.query_reports["GSTR-2B Inward Summary"] = {
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
		// Custom Action Button for Formatted Excel Download
		report.page.add_inner_button(__("Download GSTR-2 Excel"), function() {
			const filters = report.get_values();
			if (!filters.company) {
				frappe.msgprint(__("Please select Company first."));
				return;
			}
			const query_string = encodeURIComponent(JSON.stringify(filters));
			const download_url = `/api/method/nexgen_erp_reports.nexgen_reports.report.gstr_2b_inward_summary.gstr_2b_inward_summary.download_custom_excel?filters=${query_string}`;
			window.open(download_url, "_blank");
		});

		// Attach click listener for section drill-down
		$(report.page.wrapper).on("click", ".gstr-section-drilldown", function(e) {
			e.preventDefault();
			const sectionCode = $(this).attr("data-section");
			const filters = report.get_values();

			const route_params = {
				company: filters.company,
				docstatus: 1
			};

			if (filters.from_date && filters.to_date) {
				route_params["posting_date"] = ["between", [filters.from_date, filters.to_date]];
			}

			if (sectionCode === "3_4A") {
				route_params["gst_category"] = ["in", ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]];
				route_params["is_return"] = 0;
			} else if (sectionCode === "4B") {
				route_params["gst_category"] = "Unregistered";
				route_params["is_return"] = 0;
			} else if (sectionCode === "6C") {
				route_params["gst_category"] = ["in", ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]];
				route_params["is_return"] = 1;
			} else if (sectionCode === "6C_UR") {
				route_params["gst_category"] = "Unregistered";
				route_params["is_return"] = 1;
			} else if (sectionCode === "5A_5B" || sectionCode === "4C") {
				route_params["gst_category"] = "Overseas";
				route_params["is_return"] = 0;
			} else if (sectionCode === "7A_7B") {
				route_params["is_return"] = 0;
			} else if (sectionCode === "ITC_REV") {
				route_params["eligibility_for_itc"] = ["like", "%Ineligible%"];
			} else if (sectionCode === "HSN_13") {
				route_params["is_return"] = 0;
			}

			if (window.history && window.history.replaceState) {
				window.history.replaceState({}, document.title, window.location.pathname);
			}

			frappe.route_options = route_params;
			frappe.set_route("List", "Purchase Invoice");
		});
	},

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		// Section header styling (Total Input Tax Credit)
		if (data.is_header) {
			return `<strong style="color: #172b4d; font-size: 13px; text-transform: uppercase;">${value}</strong>`;
		}

		// Total / Summary rows styling
		if (data.is_total_row) {
			return `<strong style="color: #2b6cb0;">${value}</strong>`;
		}

		// Make Section Name clickable with drill-down link
		if (column.fieldname === "section_name" && data.section_code) {
			return `<a href="javascript:void(0);" 
			           class="gstr-section-drilldown" 
			           data-section="${data.section_code}" 
			           title="Click to view invoices in List View" 
			           style="color: #1a56db; font-weight: 600; text-decoration: underline; cursor: pointer;">
			           ${value}
			        </a>`;
		}

		// Make record count clickable as well
		if (column.fieldname === "record_count" && data.section_code && parseInt(data.record_count) > 0) {
			return `<a href="javascript:void(0);" 
			           class="gstr-section-drilldown badge badge-primary" 
			           data-section="${data.section_code}" 
			           style="cursor: pointer; padding: 4px 8px; font-size: 12px;">
			           ${value}
			        </a>`;
		}

		return value;
	}
};
