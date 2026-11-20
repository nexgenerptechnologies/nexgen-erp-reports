frappe.query_reports["Combined Party Ledger"] = {
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
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			on_change: function(report) {
				const cust = report.get_filter_value("customer");
				const supp = report.get_filter_value("supplier");
				if (cust && !supp) {
					frappe.call({
						method: "nexgen_erp_reports.nexgen_reports.report.combined_party_ledger.combined_party_ledger.find_matching_supplier",
						args: { customer: cust },
						callback: function(r) {
							if (r.message) {
								report.set_filter_value("supplier", r.message);
							}
						}
					});
				}
			}
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
			on_change: function(report) {
				const supp = report.get_filter_value("supplier");
				const cust = report.get_filter_value("customer");
				if (supp && !cust) {
					frappe.call({
						method: "nexgen_erp_reports.nexgen_reports.report.combined_party_ledger.combined_party_ledger.find_matching_customer",
						args: { supplier: supp },
						callback: function(r) {
							if (r.message) {
								report.set_filter_value("customer", r.message);
							}
						}
					});
				}
			}
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
		// 1. Download Excel Action
		report.page.add_inner_button(__("Download Combined Ledger Excel"), function() {
			const filters = report.get_values();
			if (!filters.company) {
				frappe.msgprint(__("Please select Company first."));
				return;
			}
			if (!filters.customer && !filters.supplier) {
				frappe.msgprint(__("Please select at least Customer or Supplier."));
				return;
			}
			const query_string = encodeURIComponent(JSON.stringify(filters));
			const download_url = `/api/method/nexgen_erp_reports.nexgen_reports.report.combined_party_ledger.combined_party_ledger.download_custom_excel?filters=${query_string}`;
			window.open(download_url, "_blank");
		});

		// 2. FIFO Contra Settlement Automation Dialog
		report.page.add_inner_button(__("FIFO Contra Settlement"), function() {
			const filters = report.get_values();
			if (!filters.company) {
				frappe.msgprint(__("Please select Company first."));
				return;
			}
			if (!filters.customer || !filters.supplier) {
				frappe.msgprint(__("Please select both <b>Customer</b> and <b>Supplier</b> to perform mutual Contra Settlement."));
				return;
			}

			frappe.call({
				method: "nexgen_erp_reports.nexgen_reports.report.combined_party_ledger.combined_party_ledger.get_contra_preview",
				args: {
					company: filters.company,
					customer: filters.customer,
					supplier: filters.supplier
				},
				freeze: true,
				freeze_message: __("Fetching open invoices for FIFO calculation..."),
				callback: function(r) {
					if (!r.message) return;
					const res = r.message;

					if (res.max_contra_amount <= 0.001) {
						frappe.msgprint({
							title: __("No Settleable Invoices"),
							indicator: "orange",
							message: __("There are no mutual outstanding invoices between Customer <b>{0}</b> and Supplier <b>{1}</b> to settle.", [res.customer_name, res.supplier_name])
						});
						return;
					}

					show_contra_dialog(report, filters, res);
				}
			});
		});
	},

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		// Total / Closing Balance row highlight
		if (data.is_total_row) {
			if (column.fieldname === "against_account") {
				return `<strong style="color: #1e3a8a; font-size: 13px;">${value}</strong>`;
			}
			return `<strong style="color: #1e3a8a;">${value}</strong>`;
		}

		// Opening Balance row highlight
		if (data.is_opening) {
			if (column.fieldname === "against_account") {
				return `<strong style="color: #1e3a8a;">${value}</strong>`;
			}
			return `<span style="font-weight: 600; color: #475569;">${value}</span>`;
		}

		// Debit in green/dark, Credit in red/dark
		if (column.fieldname === "debit" && flt(data.debit) > 0) {
			return `<span style="color: #047857; font-weight: 500;">${value}</span>`;
		}
		if (column.fieldname === "credit" && flt(data.credit) > 0) {
			return `<span style="color: #b91c1c; font-weight: 500;">${value}</span>`;
		}

		// Dr / Cr Badge
		if (column.fieldname === "balance_type" && data.balance_type) {
			if (data.balance_type === "Dr") {
				return `<span style="background-color: #d1fae5; color: #065f46; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;">Dr (Recv)</span>`;
			} else {
				return `<span style="background-color: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;">Cr (Pay)</span>`;
			}
		}

		return value;
	}
};


function show_contra_dialog(report, filters, res) {
	const cur_format = (amt) => format_currency(amt, "INR");

	const d = new frappe.ui.Dialog({
		title: __("FIFO Contra Settlement (Party Netting)"),
		size: "large",
		fields: [
			{
				fieldname: "summary_html",
				fieldtype: "HTML"
			},
			{
				fieldname: "settlement_amount",
				label: __("Contra Settlement Amount (₹)"),
				fieldtype: "Currency",
				default: res.max_contra_amount,
				reqd: 1,
				description: __("Maximum possible mutual contra amount based on open invoices is <b>{0}</b>.", [cur_format(res.max_contra_amount)])
			},
			{
				fieldname: "posting_date",
				label: __("Settlement Date"),
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1
			},
			{
				fieldname: "user_remark",
				label: __("Remarks / Narration"),
				fieldtype: "Small Text",
				default: `Mutual FIFO Contra Settlement between Customer ${res.customer} and Supplier ${res.supplier}`
			},
			{
				fieldname: "preview_html",
				fieldtype: "HTML"
			}
		],
		primary_action_label: __("Execute Contra Settlement"),
		primary_action: function(values) {
			const settle_amt = flt(values.settlement_amount);
			if (settle_amt <= 0.001) {
				frappe.msgprint(__("Settlement amount must be greater than zero."));
				return;
			}
			if (settle_amt > res.max_contra_amount + 0.01) {
				frappe.msgprint(__("Settlement amount cannot exceed maximum available contra of {0}.", [cur_format(res.max_contra_amount)]));
				return;
			}

			frappe.confirm(
				__("Are you sure you want to create and submit a Contra Journal Entry of <b>{0}</b> between Customer <b>{1}</b> and Supplier <b>{2}</b> on FIFO basis?", [
					cur_format(settle_amt),
					res.customer_name,
					res.supplier_name
				]),
				function() {
					frappe.call({
						method: "nexgen_erp_reports.nexgen_reports.report.combined_party_ledger.combined_party_ledger.execute_fifo_contra_settlement",
						args: {
							company: filters.company,
							customer: res.customer,
							supplier: res.supplier,
							settlement_amount: settle_amt,
							posting_date: values.posting_date,
							user_remark: values.user_remark
						},
						freeze: true,
						freeze_message: __("Creating Contra Journal Entry and knocking off invoices..."),
						callback: function(r) {
							if (r.message && r.message.success) {
								d.hide();
								frappe.msgprint({
									title: __("Contra Settlement Successful!"),
									indicator: "green",
									message: __(`Journal Entry <a href="/app/journal-entry/${r.message.journal_entry}" target="_blank" style="font-weight: bold; text-decoration: underline;">${r.message.journal_entry}</a> has been created and submitted successfully.<br/><br/><b>${cur_format(settle_amt)}</b> has been adjusted across open Sales and Purchase Invoices on FIFO basis.`)
								});
								report.refresh();
							}
						}
					});
				}
			);
		}
	});

	// Render Summary Cards
	const summary_html = `
		<div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 12px;">
			<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 10px;">
				<div>
					<span style="font-size: 13px; color: #64748b; font-weight: 500;">Party Relationship</span><br/>
					<strong style="font-size: 14px; color: #1e293b;">Customer: ${res.customer_name} &nbsp;⇄&nbsp; Supplier: ${res.supplier_name}</strong>
				</div>
				<div style="text-align: right;">
					<span style="font-size: 12px; color: #64748b;">Max Settleable Contra</span><br/>
					<span style="font-size: 16px; font-weight: bold; color: #047857; background: #d1fae5; padding: 3px 10px; border-radius: 6px;">
						${cur_format(res.max_contra_amount)}
					</span>
				</div>
			</div>
			<div style="display: flex; gap: 20px;">
				<div style="flex: 1; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px;">
					<div style="font-size: 12px; color: #64748b;">Open Sales Invoices (${res.open_sales.length})</div>
					<div style="font-size: 16px; font-weight: bold; color: #2563eb;">${cur_format(res.total_sales_outstanding)}</div>
				</div>
				<div style="flex: 1; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px;">
					<div style="font-size: 12px; color: #64748b;">Open Purchase Invoices (${res.open_purchases.length})</div>
					<div style="font-size: 16px; font-weight: bold; color: #ea580c;">${cur_format(res.total_purchases_outstanding)}</div>
				</div>
			</div>
		</div>
	`;
	d.fields_dict.summary_html.$wrapper.html(summary_html);

	function update_allocation_preview(settle_amt) {
		settle_amt = flt(settle_amt) || res.max_contra_amount;

		// FIFO for Sales
		let rem_s = settle_amt;
		const sales_rows = res.open_sales.map(si => {
			const out = flt(si.outstanding_amount);
			const alloc = Math.min(out, rem_s);
			rem_s = Math.max(0, rem_s - alloc);
			const new_out = out - alloc;
			return `<tr>
				<td style="padding: 6px 8px; border-bottom: 1px solid #e2e8f0;"><a href="/app/sales-invoice/${si.name}" target="_blank">${si.name}</a></td>
				<td style="padding: 6px 8px; border-bottom: 1px solid #e2e8f0;">${si.posting_date}</td>
				<td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #e2e8f0;">${cur_format(out)}</td>
				<td style="padding: 6px 8px; text-align: right; font-weight: bold; color: #047857; border-bottom: 1px solid #e2e8f0;">${cur_format(alloc)}</td>
				<td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #e2e8f0;">${cur_format(new_out)}</td>
			</tr>`;
		}).join("");

		// FIFO for Purchases
		let rem_p = settle_amt;
		const purchase_rows = res.open_purchases.map(pi => {
			const out = flt(pi.outstanding_amount);
			const alloc = Math.min(out, rem_p);
			rem_p = Math.max(0, rem_p - alloc);
			const new_out = out - alloc;
			return `<tr>
				<td style="padding: 6px 8px; border-bottom: 1px solid #e2e8f0;"><a href="/app/purchase-invoice/${pi.name}" target="_blank">${pi.name}</a></td>
				<td style="padding: 6px 8px; border-bottom: 1px solid #e2e8f0;">${pi.bill_no || "-"}</td>
				<td style="padding: 6px 8px; border-bottom: 1px solid #e2e8f0;">${pi.posting_date}</td>
				<td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #e2e8f0;">${cur_format(out)}</td>
				<td style="padding: 6px 8px; text-align: right; font-weight: bold; color: #047857; border-bottom: 1px solid #e2e8f0;">${cur_format(alloc)}</td>
				<td style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #e2e8f0;">${cur_format(new_out)}</td>
			</tr>`;
		}).join("");

		const preview_html = `
			<div style="margin-top: 10px;">
				<div style="font-weight: 600; font-size: 12px; color: #1e3a8a; margin-bottom: 4px;">
					1. Oldest Sales Invoices to be knocked off (Receivables - Credit)
				</div>
				<div style="max-height: 140px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 6px; margin-bottom: 12px;">
					<table style="width: 100%; font-size: 12px; border-collapse: collapse;">
						<thead style="background: #f1f5f9; position: sticky; top: 0;">
							<tr>
								<th style="padding: 6px 8px; text-align: left;">Invoice</th>
								<th style="padding: 6px 8px; text-align: left;">Date</th>
								<th style="padding: 6px 8px; text-align: right;">Outstanding</th>
								<th style="padding: 6px 8px; text-align: right; color: #047857;">Contra Deducted</th>
								<th style="padding: 6px 8px; text-align: right;">New Balance</th>
							</tr>
						</thead>
						<tbody>${sales_rows}</tbody>
					</table>
				</div>

				<div style="font-weight: 600; font-size: 12px; color: #ea580c; margin-bottom: 4px;">
					2. Oldest Purchase Invoices to be knocked off (Payables - Debit)
				</div>
				<div style="max-height: 140px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 6px;">
					<table style="width: 100%; font-size: 12px; border-collapse: collapse;">
						<thead style="background: #f1f5f9; position: sticky; top: 0;">
							<tr>
								<th style="padding: 6px 8px; text-align: left;">Invoice</th>
								<th style="padding: 6px 8px; text-align: left;">Bill No</th>
								<th style="padding: 6px 8px; text-align: left;">Date</th>
								<th style="padding: 6px 8px; text-align: right;">Outstanding</th>
								<th style="padding: 6px 8px; text-align: right; color: #047857;">Contra Deducted</th>
								<th style="padding: 6px 8px; text-align: right;">New Balance</th>
							</tr>
						</thead>
						<tbody>${purchase_rows}</tbody>
					</table>
				</div>
			</div>
		`;
		d.fields_dict.preview_html.$wrapper.html(preview_html);
	}

	update_allocation_preview(res.max_contra_amount);

	d.fields_dict.settlement_amount.$input.on("input change", function() {
		update_allocation_preview($(this).val());
	});

	d.show();
}
