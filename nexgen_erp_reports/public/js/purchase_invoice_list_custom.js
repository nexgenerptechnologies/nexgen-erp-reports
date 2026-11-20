// Copyright (c) 2026, NexGen ERP Technologies and contributors
// For license information, please see license.txt

frappe.provide("frappe.listview_settings");

const orig_pi_onload = frappe.listview_settings["Purchase Invoice"] ? frappe.listview_settings["Purchase Invoice"].onload : null;

frappe.listview_settings["Purchase Invoice"] = Object.assign(frappe.listview_settings["Purchase Invoice"] || {}, {
	onload: function(listview) {
		if (orig_pi_onload) {
			orig_pi_onload(listview);
		}

		// Filter out expense invoices by default so only trade/inventory purchases are shown
		if (listview.filter_area) {
			const filters = listview.filter_area.get();
			const has_filter = filters.some(function(f) { return f[1] === "is_expense_invoice"; });
			if (!has_filter && !frappe.route_options) {
				listview.filter_area.add([["Purchase Invoice", "is_expense_invoice", "=", 0]]);
			}
		}
	}
});
