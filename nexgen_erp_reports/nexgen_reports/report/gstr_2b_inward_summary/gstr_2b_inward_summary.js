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
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
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

			const listFilters = {
				company: filters.company,
				posting_date: ["between", [filters.from_date, filters.to_date]],
				docstatus: 1
			};

			if (sectionCode === "3_4A") {
				listFilters["gst_category"] = ["in", ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]];
				listFilters["is_return"] = 0;
			} else if (sectionCode === "4B") {
				listFilters["gst_category"] = "Unregistered";
				listFilters["is_return"] = 0;
			} else if (sectionCode === "6C") {
				listFilters["gst_category"] = ["in", ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]];
				listFilters["is_return"] = 1;
			} else if (sectionCode === "6C_UR") {
				listFilters["gst_category"] = "Unregistered";
				listFilters["is_return"] = 1;
			} else if (sectionCode === "5A_5B") {
				listFilters["gst_category"] = "Overseas";
			} else if (sectionCode === "4C") {
				listFilters["gst_category"] = "Overseas";
			} else if (sectionCode === "ITC_REV") {
				listFilters["eligibility_for_itc"] = ["like", "%Ineligible%"];
			}

			frappe.set_route("List", "Purchase Invoice", listFilters);
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
			           style="color: #1a56db; font-weight: 600; text-decoration: underline;">
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
