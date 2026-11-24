// Copyright (c) 2026, NexGen ERP Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Expense Invoice", {
	setup: function(frm) {
		// Filter Expense Accounts in Items table
		frm.set_query("expense_account", "items", function() {
			return {
				filters: {
					company: frm.doc.company,
					root_type: "Expense",
					is_group: 0
				}
			};
		});
	},

	refresh: function(frm) {
		if (frm.doc.docstatus === 1) {
			// Override Cancel action to smoothly cancel both Expense Invoice and background Purchase Invoice without circular dependency deadlock
			setTimeout(function() {
				frm.page.set_secondary_action(__("Cancel"), function() {
					frappe.confirm(
						__("Are you sure you want to cancel Expense Invoice <b>{0}</b> and its linked Purchase Invoice?", [frm.doc.name]),
						function() {
							frappe.call({
								method: "nexgen_erp_reports.nexgen_reports.doctype.expense_invoice.expense_invoice.cancel_expense_invoice",
								args: { expense_invoice_name: frm.doc.name },
								freeze: true,
								freeze_message: __("Cancelling Expense Invoice and linked transactions..."),
								callback: function(r) {
									if (r.message) {
										frappe.show_alert({
											message: __("Expense Invoice {0} cancelled successfully", [frm.doc.name]),
											indicator: "green"
										});
										frm.reload_doc();
									}
								}
							});
						}
					);
				});
			}, 200);
		}

		if (frm.doc.docstatus === 1 && frm.doc.purchase_invoice) {
			// Button: View Purchase Invoice
			frm.add_custom_button(__("View Purchase Invoice"), function() {
				frappe.set_route("Form", "Purchase Invoice", frm.doc.purchase_invoice);
			}, __("Actions"));

			// Button: Make Payment
			frm.add_custom_button(__("Make Payment"), function() {
				frappe.call({
					method: "nexgen_erp_reports.nexgen_reports.doctype.expense_invoice.expense_invoice.make_payment_entry",
					args: { expense_invoice_name: frm.doc.name },
					callback: function(r) {
						if (r.message) {
							var doc = frappe.model.sync(r.message)[0];
							frappe.set_route("Form", doc.doctype, doc.name);
						}
					}
				});
			}, __("Actions"));

			// Button: View General Ledger
			frm.add_custom_button(__("Accounting Ledger"), function() {
				frappe.route_options = {
					company: frm.doc.company,
					voucher_no: frm.doc.purchase_invoice,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("Actions"));
		}
	},

	supplier: function(frm) {
		if (frm.doc.supplier) {
			frappe.db.get_value("Supplier", frm.doc.supplier, ["gstin", "supplier_name"], function(val) {
				if (val) {
					frm.set_value("supplier_name", val.supplier_name);
					frm.set_value("supplier_gstin", val.gstin);

					// Auto-detect In-State vs Out-of-State tax type
					if (val.gstin && frm.doc.company) {
						frappe.db.get_value("Company", frm.doc.company, "gstin", function(c_val) {
							if (c_val && c_val.gstin) {
								var supp_state = val.gstin.substring(0, 2);
								var comp_state = c_val.gstin.substring(0, 2);
								if (supp_state === comp_state) {
									frm.set_value("tax_type", "In-State (CGST + SGST)");
								} else {
									frm.set_value("tax_type", "Out-of-State (IGST)");
								}
							}
						});
					}
				}
			});
		}
	},

	tax_type: function(frm) {
		calculate_doc_totals(frm);
	},

	gst_rate: function(frm) {
		calculate_doc_totals(frm);
	},

	apply_tds: function(frm) {
		calculate_doc_totals(frm);
	},

	tds_rate: function(frm) {
		calculate_doc_totals(frm);
	}
});

frappe.ui.form.on("Expense Invoice Item", {
	amount: function(frm, cdt, cdn) {
		calculate_doc_totals(frm);
	},
	gst_rate: function(frm, cdt, cdn) {
		calculate_doc_totals(frm);
	},
	items_remove: function(frm) {
		calculate_doc_totals(frm);
	}
});

function calculate_doc_totals(frm) {
	var gst_rate = flt(frm.doc.gst_rate) || 18.0;
	var tax_type = frm.doc.tax_type || "In-State (CGST + SGST)";

	var net_total = 0.0;
	var cgst_total = 0.0;
	var sgst_total = 0.0;
	var igst_total = 0.0;

	(frm.doc.items || []).forEach(function(item) {
		var amt = flt(item.amount);
		var item_rate = flt(item.gst_rate) || gst_rate;
		item.gst_rate = item_rate;

		var item_cgst = 0.0;
		var item_sgst = 0.0;
		var item_igst = 0.0;

		if (tax_type === "In-State (CGST + SGST)") {
			item_cgst = flt(amt * (item_rate / 2.0) / 100.0, 2);
			item_sgst = flt(amt * (item_rate / 2.0) / 100.0, 2);
		} else if (tax_type === "Out-of-State (IGST)") {
			item_igst = flt(amt * (item_rate / 100.0), 2);
		}

		item.cgst = item_cgst;
		item.sgst = item_sgst;
		item.igst = item_igst;
		item.total_amount = amt + item_cgst + item_sgst + item_igst;

		net_total += amt;
		cgst_total += item_cgst;
		sgst_total += item_sgst;
		igst_total += item_igst;
	});

	var total_tax = cgst_total + sgst_total + igst_total;
	var grand_total = net_total + total_tax;

	var tds_amount = 0.0;
	if (frm.doc.apply_tds && flt(frm.doc.tds_rate) > 0) {
		tds_amount = flt(net_total * flt(frm.doc.tds_rate) / 100.0, 2);
	}

	var net_payable = grand_total - tds_amount;

	frm.set_value("net_total", net_total);
	frm.set_value("cgst_amount", cgst_total);
	frm.set_value("sgst_amount", sgst_total);
	frm.set_value("igst_amount", igst_total);
	frm.set_value("total_tax", total_tax);
	frm.set_value("grand_total", grand_total);
	frm.set_value("tds_amount", tds_amount);
	frm.set_value("net_payable", net_payable);

	frm.refresh_field("items");
}
