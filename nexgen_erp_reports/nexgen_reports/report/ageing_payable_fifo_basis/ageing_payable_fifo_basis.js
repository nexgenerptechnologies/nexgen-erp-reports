frappe.query_reports["Ageing Payable FIFO Basis"] = {
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
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier"
		},
		{
			fieldname: "supplier_group",
			label: __("Supplier Group"),
			fieldtype: "Link",
			options: "Supplier Group"
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
			const download_url = `/api/method/nexgen_erp_reports.nexgen_reports.report.ageing_payable_fifo_basis.ageing_payable_fifo_basis.download_custom_excel?filters=${query_string}`;
			window.open(download_url, "_blank");
		});

		// Click Party Name -> Open General Ledger
		$(report.page.wrapper).on("click", ".party-gl-drilldown", function(e) {
			e.preventDefault();
			const party = $(this).attr("data-party");
			const filters = report.get_values();

			const report_date = filters.report_date || frappe.datetime.get_today();
			const parts = report_date.split("-");
			const year = parseInt(parts[0], 10);
			const month = parseInt(parts[1], 10);
			const fy_year = month >= 4 ? year : year - 1;
			const from_date = fy_year + "-04-01";

			const gl_filters = {
				company: filters.company,
				party_type: "Supplier",
				party: [party],
				from_date: from_date,
				to_date: report_date
			};
			if (window.history && window.history.replaceState) {
				window.history.replaceState({}, document.title, window.location.pathname);
			}
			frappe.route_options = gl_filters;
			frappe.set_route("query-report", "General Ledger");
		});

		// Click Closing Amount or Slab -> Open Purchase Invoices
		$(report.page.wrapper).on("click", ".party-invoices-drilldown", function(e) {
			e.preventDefault();
			const party = $(this).attr("data-party");
			const filters = report.get_values();

			const route_params = {
				company: filters.company,
				supplier: party,
				docstatus: 1
			};
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

		// Make Party Details clickable link to General Ledger
		if (column.fieldname === "party_name" && data.party) {
			return `<a href="javascript:void(0);" 
			           class="party-gl-drilldown" 
			           data-party="${data.party}" 
			           title="Click to view Supplier Ledger in General Ledger" 
			           style="color: #1a56db; font-weight: 600; text-decoration: underline; cursor: pointer;">
			           ${data.party_name || data.party}
			        </a>`;
		}

		// Make Closing Amount clickable link to Purchase Invoices
		if (column.fieldname === "closing_amt" && data.party && data.closing_amt > 0) {
			return `<a href="javascript:void(0);" 
			           class="party-invoices-drilldown" 
			           data-party="${data.party}" 
			           title="Click to view Purchase Invoices" 
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
			           title="Click to view Purchase Invoices" 
			           style="color: ${color}; text-decoration: underline; cursor: pointer; font-weight: 500;">
			           ${value}
			        </a>`;
		}

		return value;
	}
};
