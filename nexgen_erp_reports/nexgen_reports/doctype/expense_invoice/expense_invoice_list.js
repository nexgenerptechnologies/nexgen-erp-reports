// Copyright (c) 2026, NexGen ERP Technologies and contributors
// For license information, please see license.txt

frappe.listview_settings["Expense Invoice"] = {
	add_fields: ["status", "grand_total", "net_payable", "purchase_invoice"],
	get_indicator: function(doc) {
		if (doc.status === "Paid") {
			return [__("Paid"), "green", "status,=,Paid"];
		} else if (doc.status === "Partly Paid") {
			return [__("Partly Paid"), "yellow", "status,=,Partly Paid"];
		} else if (doc.status === "Unpaid") {
			return [__("Unpaid"), "orange", "status,=,Unpaid"];
		} else if (doc.status === "Overdue") {
			return [__("Overdue"), "red", "status,=,Overdue"];
		} else if (doc.status === "Submitted") {
			return [__("Submitted"), "blue", "status,=,Submitted"];
		} else if (doc.status === "Draft") {
			return [__("Draft"), "red", "status,=,Draft"];
		} else if (doc.status === "Cancelled") {
			return [__("Cancelled"), "darkgrey", "status,=,Cancelled"];
		}
	},
	onload: function(listview) {
		// Custom Action Button in List View Menu to sync past expense invoices
		listview.page.add_inner_button(__("Sync Past Expense Invoices"), function() {
			frappe.confirm(
				__("Scan past Purchase Invoices that represent expenses/services and import them into Expense Invoices?"),
				function() {
					frappe.call({
						method: "nexgen_erp_reports.nexgen_reports.doctype.expense_invoice.expense_invoice.sync_past_expense_invoices",
						freeze: true,
						freeze_message: __("Syncing past expense invoices..."),
						callback: function(r) {
							if (r.message) {
								frappe.msgprint({
									title: __("Sync Complete"),
									indicator: "green",
									message: __("Successfully synced <b>{0}</b> past expense invoices into Expense Invoices list view.", [r.message.synced])
								});
								listview.refresh();
							}
						}
					});
				}
			);
		});
	}
};
