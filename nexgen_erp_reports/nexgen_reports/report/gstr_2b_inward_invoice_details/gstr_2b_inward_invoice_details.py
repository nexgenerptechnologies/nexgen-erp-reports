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
            "options": "Purchase Invoice",
            "width": 160
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 105
        },
        {
            "label": _("Supplier Name"),
            "fieldname": "supplier_name",
            "fieldtype": "Data",
            "width": 220
        },
        {
            "label": _("Supplier GSTIN"),
            "fieldname": "supplier_gstin",
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
            "label": _("Supply Type"),
            "fieldname": "supply_type",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("GSTR-2B Section"),
            "fieldname": "section_name",
            "fieldtype": "Data",
            "width": 160
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
            "label": _("Net ITC"),
            "fieldname": "itc_available",
            "fieldtype": "Currency",
            "width": 130
        }
    ]


SECTION_LABELS = {
    "3_4A": "B2B Invoices - 3, 4A",
    "4B": "B2BUR Invoices - 4B",
    "6C": "Credit/Debit Notes - 6C",
    "6C_UR": "Credit/Debit Notes UnRegister - 6C",
    "5A_5B": "Import of Goods - 5A, 5B",
    "4C": "Import of Services - 4C",
    "7A_7B": "Nil Rated Invoices - 7A, 7B",
    "ITC_REV": "ITC Reversal"
}


def classify_invoice(inv):
    is_return = flt(inv.get("is_return", 0)) == 1
    gst_category = (inv.get("gst_category") or "").strip()
    supplier_gstin = (inv.get("supplier_gstin") or "").strip()
    is_registered = bool(supplier_gstin) or gst_category in ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]
    eligibility = (inv.get("eligibility_for_itc") or "").lower()

    if "ineligible" in eligibility:
        return "ITC_REV"

    if gst_category == "Overseas":
        if inv.get("is_service_import"):
            return "4C"
        return "5A_5B"

    if is_return:
        if is_registered:
            return "6C"
        return "6C_UR"

    # Purchases from Unregistered suppliers are B2BUR (Table 4B)
    if gst_category == "Unregistered" or not is_registered:
        return "4B"

    total_tax = flt(inv.get("cgst", 0)) + flt(inv.get("sgst", 0)) + flt(inv.get("igst", 0)) + flt(inv.get("cess", 0))
    if flt(inv.get("base_net_total", 0)) > 0 and total_tax == 0:
        return "7A_7B"

    if is_registered:
        return "3_4A"
    else:
        return "4B"


def get_data(filters):
    conditions = ["pi.docstatus = 1"]
    if filters.get("company"):
        conditions.append("pi.company = %(company)s")
    if filters.get("from_date"):
        conditions.append("pi.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("pi.posting_date <= %(to_date)s")

    cond_str = " AND ".join(conditions)

    # Dynamic column checks
    has_gst_category = frappe.db.has_column("Purchase Invoice", "gst_category")
    has_supplier_gstin = frappe.db.has_column("Purchase Invoice", "supplier_gstin")
    has_eligibility = frappe.db.has_column("Purchase Invoice", "eligibility_for_itc")
    has_exp_flag = frappe.db.has_column("Purchase Invoice", "is_expense_invoice")

    gst_cat_expr = "pi.gst_category" if has_gst_category else "'' as gst_category"
    supplier_gstin_expr = "pi.supplier_gstin" if has_supplier_gstin else "'' as supplier_gstin"
    eligibility_expr = "pi.eligibility_for_itc" if has_eligibility else "'' as eligibility_for_itc"
    exp_flag_expr = "COALESCE(pi.is_expense_invoice, 0) as is_expense_invoice" if has_exp_flag else "0 as is_expense_invoice"

    has_base_tax = frappe.db.has_column("Purchase Taxes and Charges", "base_tax_amount_after_discount_amount")
    tax_col = "base_tax_amount_after_discount_amount" if has_base_tax else "tax_amount"

    query = f"""
        SELECT
            pi.name,
            pi.posting_date,
            pi.supplier,
            pi.supplier_name,
            {supplier_gstin_expr},
            {gst_cat_expr},
            pi.is_return,
            {exp_flag_expr},
            {eligibility_expr},
            pi.base_net_total,
            pi.base_grand_total,
            COALESCE(taxes.cgst, 0) as cgst,
            COALESCE(taxes.sgst, 0) as sgst,
            COALESCE(taxes.igst, 0) as igst,
            COALESCE(taxes.cess, 0) as cess
        FROM
            `tabPurchase Invoice` pi
        LEFT JOIN (
            SELECT
                parent,
                SUM(CASE WHEN LOWER(account_head) LIKE '%%cgst%%' OR LOWER(account_head) LIKE '%%central tax%%' OR LOWER(account_head) LIKE '%%central gst%%' THEN {tax_col} ELSE 0 END) as cgst,
                SUM(CASE WHEN LOWER(account_head) LIKE '%%sgst%%' OR LOWER(account_head) LIKE '%%state tax%%' OR LOWER(account_head) LIKE '%%state gst%%' OR LOWER(account_head) LIKE '%%utgst%%' THEN {tax_col} ELSE 0 END) as sgst,
                SUM(CASE WHEN LOWER(account_head) LIKE '%%igst%%' OR LOWER(account_head) LIKE '%%integrated tax%%' OR LOWER(account_head) LIKE '%%integrated gst%%' THEN {tax_col} ELSE 0 END) as igst,
                SUM(CASE WHEN LOWER(account_head) LIKE '%%cess%%' THEN {tax_col} ELSE 0 END) as cess
            FROM `tabPurchase Taxes and Charges`
            GROUP BY parent
        ) taxes ON taxes.parent = pi.name
        WHERE {cond_str}
        ORDER BY pi.posting_date DESC, pi.name DESC
    """
    invoices = frappe.db.sql(query, filters, as_dict=True)

    filter_section = filters.get("section_code")
    filter_supply_type = filters.get("supply_type")

    rows = []
    for inv in invoices:
        sec = classify_invoice(inv)

        if filter_section and filter_section != "All Sections" and sec != filter_section:
            continue

        is_exp = flt(inv.get("is_expense_invoice", 0)) == 1 or (inv.get("name") or "").startswith("EXP-")
        supply_type = "Expense Invoice" if is_exp else "Stock Purchase"

        if filter_supply_type and filter_supply_type != "All":
            if filter_supply_type != supply_type:
                continue

        taxable = flt(inv.get("base_net_total", 0.0))
        cgst = flt(inv.get("cgst", 0.0))
        sgst = flt(inv.get("sgst", 0.0))
        igst = flt(inv.get("igst", 0.0))
        cess = flt(inv.get("cess", 0.0))
        tot_tax = cgst + sgst + igst + cess

        is_ineligible = (inv.get("eligibility_for_itc") or "").lower() in [
            "ineligible", "ineligible as per section 17(5)", "no", "none"
        ]
        net_itc = 0.0 if (is_ineligible or sec == "ITC_REV") else tot_tax

        rows.append({
            "invoice_no": inv.name,
            "posting_date": inv.posting_date,
            "supplier_name": inv.supplier_name or inv.supplier,
            "supplier_gstin": inv.supplier_gstin or "-",
            "gst_category": inv.gst_category or "Unregistered",
            "supply_type": supply_type,
            "section_name": SECTION_LABELS.get(sec, sec),
            "taxable_value": taxable,
            "cgst_amount": cgst,
            "sgst_amount": sgst,
            "igst_amount": igst,
            "cess_amount": cess,
            "total_tax": tot_tax,
            "itc_available": net_itc
        })

    return rows
