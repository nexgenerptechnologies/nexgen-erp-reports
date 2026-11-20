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

		// Click Party Name -> Open General Ledger
		$(report.page.wrapper).on("click", ".party-gl-drilldown", function(e) {
			e.preventDefault();
			const party = $(this).attr("data-party");
			const filters = report.get_values();

			const gl_filters = {
				company: filters.company,
				party_type: "Customer",
				party: party,
				from_date: frappe.datetime.year_start(),
				to_date: filters.report_date
			};
			if (window.history && window.history.replaceState) {
				window.history.replaceState({}, document.title, window.location.pathname);
			}
			frappe.route_options = gl_filters;
			frappe.set_route("query-report", "General Ledger");
		});

		// Click Closing Amount or Slab -> Open Sales Invoices
		$(report.page.wrapper).on("click", ".party-invoices-drilldown", function(e) {
			e.preventDefault();
			const party = $(this).attr("data-party");
			const filters = report.get_values();

			const route_params = {
				company: filters.company,
				customer: party,
				docstatus: 1
			};
			if (window.history && window.history.replaceState) {
				window.history.replaceState({}, document.title, window.location.pathname);
			}
			frappe.route_options = route_params;
			frappe.set_route("List", "Sales Invoice");
		});
	},

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		// Make Party Details clickable link to General Ledger
		if (column.fieldname === "party_name" && data.party) {
			return `<a href="javascript:void(0);" 
			           class="party-gl-drilldown" 
			           data-party="${data.party}" 
			           title="Click to view Customer Ledger in General Ledger" 
			           style="color: #1a56db; font-weight: 600; text-decoration: underline; cursor: pointer;">
			           ${data.party_name || data.party}
			        </a>`;
		}

		// Make Closing Amount clickable link to Sales Invoices
		if (column.fieldname === "closing_amt" && data.party && data.closing_amt > 0) {
			return `<a href="javascript:void(0);" 
			           class="party-invoices-drilldown" 
			           data-party="${data.party}" 
			           title="Click to view Sales Invoices" 
			           style="color: #1e3a8a; font-weight: bold; text-decoration: underline; cursor: pointer;">
			           ${value}
			        </a>`;
		}

		// Make aging slabs clickable as well
		if (column.fieldname && column.fieldname.startsWith("range") && data.party && data[column.fieldname] > 0) {
			const color = column.fieldname === "range6" ? "#b91c1c" : "#2563eb";
			return `<a href="javascript:void(0);" 
			           class="party-invoices-drilldown" 
			           data-party="${data.party}" 
			           title="Click to view Sales Invoices" 
			           style="color: ${color}; text-decoration: underline; cursor: pointer; font-weight: 500;">
			           ${value}
			        </a>`;
		}

		return value;
	}
};
