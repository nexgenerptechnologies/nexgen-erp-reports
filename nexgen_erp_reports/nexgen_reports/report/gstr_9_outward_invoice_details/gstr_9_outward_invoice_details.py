# Copyright (c) 2026, NexGen ERP Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, formatdate


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": _("Invoice No"),
            "fieldname": "invoice_no",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 160
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 105
        },
        {
            "label": _("Customer Name"),
            "fieldname": "customer_name",
            "fieldtype": "Data",
            "width": 220
        },
        {
            "label": _("Customer GSTIN"),
            "fieldname": "customer_gstin",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("GST Category"),
            "fieldname": "gst_category",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": _("GSTR-9 Section"),
            "fieldname": "section_name",
            "fieldtype": "Data",
            "width": 240
        },
        {
            "label": _("Taxable Value"),
            "fieldname": "taxable_value",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Central Tax"),
            "fieldname": "cgst_amount",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("State/UT Tax"),
            "fieldname": "sgst_amount",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Integrated Tax"),
            "fieldname": "igst_amount",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Cess"),
            "fieldname": "cess_amount",
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "label": _("Total Tax"),
            "fieldname": "total_tax",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Grand Total"),
            "fieldname": "grand_total",
            "fieldtype": "Currency",
            "width": 130
        }
    ]


SECTION_LABELS = {
    "4A": "4A. Supplies to Un-registered persons (B2C)",
    "4B": "4B. Supplies to Registered persons (B2B)",
    "4C": "4C. Zero rated supply (Export) with tax",
    "4D": "4D. Supply to SEZs with tax",
    "4E": "4E. Deemed Exports",
    "4I": "4I. Credit Notes (with tax)",
    "4J": "4J. Debit Notes (with tax)",
    "5A": "5A. Zero rated supply (Export) without tax",
    "5B": "5B. Supply to SEZs without tax",
    "5C": "5C. Supplies liable to reverse charge",
    "5D": "5D. Exempted Supplies",
    "5E": "5E. Nil Rated Supplies",
    "5F": "5F. Non-GST Supply",
    "5H": "5H. Credit Notes (without tax)",
    "5I": "5I. Debit Notes (without tax)"
}


def classify_invoice(inv):
    is_return = flt(inv.get("is_return", 0)) == 1
    gst_category = (inv.get("gst_category") or "").strip()
    customer_gstin = (inv.get("customer_gstin") or "").strip()
    is_registered = bool(customer_gstin) or gst_category in ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]
    reverse_charge = (inv.get("reverse_charge") or "N").upper() in ["Y", "YES"]

    cgst = flt(inv.get("cgst", 0.0))
    sgst = flt(inv.get("sgst", 0.0))
    igst = flt(inv.get("igst", 0.0))
    cess = flt(inv.get("cess", 0.0))
    total_tax = cgst + sgst + igst + cess

    if is_return:
        if total_tax > 0:
            return "4I"
        return "5H"
    else:
        if total_tax > 0:
            if gst_category == "Overseas":
                return "4C"
            elif gst_category == "SEZ":
                return "4D"
            elif gst_category == "Deemed Export":
                return "4E"
            elif is_registered:
                return "4B"
            else:
                return "4A"
        else:
            if gst_category == "Overseas":
                return "5A"
            elif gst_category == "SEZ":
                return "5B"
            elif reverse_charge:
                return "5C"
            elif gst_category == "Exempt":
                return "5D"
            elif gst_category == "Nil Rated":
                return "5E"
            else:
                return "5A" if gst_category == "Overseas" else "5D"


def get_data(filters):
    conditions = ["si.docstatus = 1"]
    if filters.get("company"):
        conditions.append("si.company = %(company)s")
    if filters.get("from_date"):
        conditions.append("si.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("si.posting_date <= %(to_date)s")

    cond_str = " AND ".join(conditions)

    has_gst_category = frappe.db.has_column("Sales Invoice", "gst_category")
    has_customer_gstin = frappe.db.has_column("Sales Invoice", "customer_gstin")
    has_reverse_charge = frappe.db.has_column("Sales Invoice", "reverse_charge")

    gst_cat_col = "si.gst_category" if has_gst_category else "'' as gst_category"
    gstin_col = "si.customer_gstin" if has_customer_gstin else "'' as customer_gstin"
    rcm_col = "si.reverse_charge" if has_reverse_charge else "'N' as reverse_charge"

    has_base_tax = frappe.db.has_column("Sales Taxes and Charges", "base_tax_amount_after_discount_amount")
    tax_col = "base_tax_amount_after_discount_amount" if has_base_tax else "tax_amount"

    query = f"""
        SELECT
            si.name,
            si.posting_date,
            si.customer,
            si.customer_name,
            si.is_return,
            si.base_net_total,
            si.base_grand_total,
            {gst_cat_col},
            {gstin_col},
            {rcm_col},
            COALESCE(taxes.cgst, 0) as cgst,
            COALESCE(taxes.sgst, 0) as sgst,
            COALESCE(taxes.igst, 0) as igst,
            COALESCE(taxes.cess, 0) as cess
        FROM `tabSales Invoice` si
        LEFT JOIN (
            SELECT
                parent,
                SUM(CASE WHEN LOWER(account_head) LIKE '%%cgst%%' OR LOWER(account_head) LIKE '%%central tax%%' OR LOWER(account_head) LIKE '%%central gst%%' THEN {tax_col} ELSE 0 END) as cgst,
                SUM(CASE WHEN LOWER(account_head) LIKE '%%sgst%%' OR LOWER(account_head) LIKE '%%state tax%%' OR LOWER(account_head) LIKE '%%state gst%%' OR LOWER(account_head) LIKE '%%utgst%%' THEN {tax_col} ELSE 0 END) as sgst,
                SUM(CASE WHEN LOWER(account_head) LIKE '%%igst%%' OR LOWER(account_head) LIKE '%%integrated tax%%' OR LOWER(account_head) LIKE '%%integrated gst%%' THEN {tax_col} ELSE 0 END) as igst,
                SUM(CASE WHEN LOWER(account_head) LIKE '%%cess%%' THEN {tax_col} ELSE 0 END) as cess
            FROM `tabSales Taxes and Charges`
            GROUP BY parent
        ) taxes ON taxes.parent = si.name
        WHERE {cond_str}
        ORDER BY si.posting_date DESC, si.name DESC
    """
    invoices = frappe.db.sql(query, filters, as_dict=True)

    filter_section = filters.get("section_code")

    rows = []
    for inv in invoices:
        sec = classify_invoice(inv)

        if filter_section and filter_section != "All Sections" and sec != filter_section:
            continue

        taxable = flt(inv.get("base_net_total", 0.0))
        cgst = flt(inv.get("cgst", 0.0))
        sgst = flt(inv.get("sgst", 0.0))
        igst = flt(inv.get("igst", 0.0))
        cess = flt(inv.get("cess", 0.0))
        tot_tax = cgst + sgst + igst + cess
        grand_total = flt(inv.get("base_grand_total", 0.0)) or (taxable + tot_tax)

        rows.append({
            "invoice_no": inv.name,
            "posting_date": inv.posting_date,
            "customer_name": inv.customer_name or inv.customer,
            "customer_gstin": inv.customer_gstin or "-",
            "gst_category": inv.gst_category or "Unregistered",
            "section_name": SECTION_LABELS.get(sec, sec),
            "taxable_value": taxable,
            "cgst_amount": cgst,
            "sgst_amount": sgst,
            "igst_amount": igst,
            "cess_amount": cess,
            "total_tax": tot_tax,
            "grand_total": grand_total
        })

    return rows
