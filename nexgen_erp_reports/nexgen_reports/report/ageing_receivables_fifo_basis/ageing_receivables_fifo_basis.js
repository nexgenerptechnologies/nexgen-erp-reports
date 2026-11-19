frappe.query_reports["Ageing Receivables FIFO Basis"] = {
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
			fieldname: "report_date",
			label: __("Account Status as on"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group"
		}
	],

	onload: function(report) {
		// Custom Action Button for Formatted Excel Download
		report.page.add_inner_button(__("Download Ageing Excel"), function() {
			const filters = report.get_values();
			if (!filters.company) {
				frappe.msgprint(__("Please select Company first."));
				return;
			}
			const query_string = encodeURIComponent(JSON.stringify(filters));
			const download_url = `/api/method/nexgen_erp_reports.nexgen_reports.report.ageing_receivables_fifo_basis.ageing_receivables_fifo_basis.download_custom_excel?filters=${query_string}`;
			window.open(download_url, "_blank");
		});

		// Clickable Party Name -> Open General Ledger
		$(report.page.wrapper).on("click", ".party-gl-drilldown", function(e) {
			e.preventDefault();
			const party = $(this).attr("data-party");
			const filters = report.get_values();

			frappe.set_route("query-report", "General Ledger", {
				company: filters.company,
				party_type: "Customer",
				party: [party],
				from_date: frappe.datetime.year_start(),
				to_date: filters.report_date
			});
		});
	},

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		// Make Party Details clickable link
		if (column.fieldname === "party_name" && data.party) {
			return `<a href="javascript:void(0);" 
			           class="party-gl-drilldown" 
			           data-party="${data.party}" 
			           title="Click to view Customer Ledger in General Ledger" 
			           style="color: #1a56db; font-weight: 600; text-decoration: underline; cursor: pointer;">
			           ${value}
			        </a>`;
		}

		// Highlight long pending aging (>= 151 Days)
		if (column.fieldname === "range6" && data.range6 > 0) {
			return `<span style="color: #b91c1c; font-weight: 600;">${value}</span>`;
		}

		// Bold Closing Amount
		if (column.fieldname === "closing_amt") {
			return `<strong style="color: #1e3a8a;">${value}</strong>`;
		}

		return value;
	}
};
