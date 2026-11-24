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
            "label": _("Supplier"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 150
        },
        {
            "label": _("Supplier Name"),
            "fieldname": "supplier_name",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Supplier GSTIN"),
            "fieldname": "supplier_gstin",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": _("Supplier Bill No"),
            "fieldname": "bill_no",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("Bill Date"),
            "fieldname": "bill_date",
            "fieldtype": "Date",
            "width": 105
        },
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 140
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Qty"),
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 90
        },
        {
            "label": _("UOM"),
            "fieldname": "uom",
            "fieldtype": "Data",
            "width": 80
        },
        {
            "label": _("Rate"),
            "fieldname": "rate",
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "label": _("Taxable Amount"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 125
        },
        {
            "label": _("CGST"),
            "fieldname": "cgst",
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "label": _("SGST"),
            "fieldname": "sgst",
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "label": _("IGST"),
            "fieldname": "igst",
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "label": _("Total Tax"),
            "fieldname": "total_tax",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Grand Total"),
            "fieldname": "grand_total",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 140
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        }
    ]


def get_data(filters):
    conditions = ["pi.docstatus = 1"]

    # Strictly filter for Stock / Material Purchases (exclude Expense Invoices)
    if frappe.db.has_column("Purchase Invoice", "is_expense_invoice"):
        conditions.append("(pi.is_expense_invoice IS NULL OR pi.is_expense_invoice = 0)")

    conditions.append("pi.name NOT LIKE 'EXP-%%'")

    if filters.get("company"):
        conditions.append("pi.company = %(company)s")
    if filters.get("from_date"):
        conditions.append("pi.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("pi.posting_date <= %(to_date)s")
    if filters.get("supplier"):
        conditions.append("pi.supplier = %(supplier)s")
    if filters.get("item_code"):
        conditions.append("pii.item_code = %(item_code)s")

    cond_str = " AND ".join(conditions)

    # Dynamic column checks
    has_supplier_gstin = frappe.db.has_column("Purchase Invoice", "supplier_gstin")
    supplier_gstin_col = "pi.supplier_gstin" if has_supplier_gstin else "'' as supplier_gstin"

    has_item_cgst = frappe.db.has_column("Purchase Invoice Item", "cgst_amount")
    item_cgst_expr = "COALESCE(pii.cgst_amount, 0)" if has_item_cgst else "0"
    item_sgst_expr = "COALESCE(pii.sgst_amount, 0)" if has_item_cgst else "0"
    item_igst_expr = "COALESCE(pii.igst_amount, 0)" if has_item_cgst else "0"

    has_base_tax = frappe.db.has_column("Purchase Taxes and Charges", "base_tax_amount_after_discount_amount")
    tax_col = "base_tax_amount_after_discount_amount" if has_base_tax else "tax_amount"

    query = f"""
        SELECT
            pi.name as invoice_no,
            pi.posting_date,
            pi.supplier,
            pi.supplier_name,
            {supplier_gstin_col},
            pi.bill_no,
            pi.bill_date,
            pi.status,
            pi.net_total as invoice_net_total,
            pii.item_code,
            pii.item_name,
            pii.description,
            pii.qty,
            pii.uom,
            pii.rate,
            pii.amount,
            pii.warehouse,
            {item_cgst_expr} as direct_cgst,
            {item_sgst_expr} as direct_sgst,
            {item_igst_expr} as direct_igst,
            COALESCE(inv_taxes.cgst, 0) as inv_cgst,
            COALESCE(inv_taxes.sgst, 0) as inv_sgst,
            COALESCE(inv_taxes.igst, 0) as inv_igst
        FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        LEFT JOIN (
            SELECT
                parent,
                SUM(CASE WHEN LOWER(account_head) LIKE '%%cgst%%' OR LOWER(account_head) LIKE '%%central tax%%' OR LOWER(account_head) LIKE '%%central gst%%' THEN {tax_col} ELSE 0 END) as cgst,
                SUM(CASE WHEN LOWER(account_head) LIKE '%%sgst%%' OR LOWER(account_head) LIKE '%%state tax%%' OR LOWER(account_head) LIKE '%%state gst%%' OR LOWER(account_head) LIKE '%%utgst%%' THEN {tax_col} ELSE 0 END) as sgst,
                SUM(CASE WHEN LOWER(account_head) LIKE '%%igst%%' OR LOWER(account_head) LIKE '%%integrated tax%%' OR LOWER(account_head) LIKE '%%integrated gst%%' THEN {tax_col} ELSE 0 END) as igst
            FROM `tabPurchase Taxes and Charges`
            GROUP BY parent
        ) inv_taxes ON inv_taxes.parent = pi.name
        WHERE {cond_str}
        ORDER BY pi.posting_date DESC, pi.name DESC, pii.idx ASC
    """
    items = frappe.db.sql(query, filters, as_dict=True)

    rows = []
    for row in items:
        amt = flt(row.amount)
        net_tot = flt(row.invoice_net_total)
        ratio = (amt / net_tot) if net_tot > 0 else 0.0

        if row.direct_cgst or row.direct_sgst or row.direct_igst:
            cgst = flt(row.direct_cgst)
            sgst = flt(row.direct_sgst)
            igst = flt(row.direct_igst)
        else:
            cgst = flt(row.inv_cgst * ratio, 2)
            sgst = flt(row.inv_sgst * ratio, 2)
            igst = flt(row.inv_igst * ratio, 2)

        tot_tax = cgst + sgst + igst
        grand_total = amt + tot_tax

        rows.append({
            "invoice_no": row.invoice_no,
            "posting_date": row.posting_date,
            "supplier": row.supplier,
            "supplier_name": row.supplier_name or row.supplier,
            "supplier_gstin": row.supplier_gstin or "-",
            "bill_no": row.bill_no or "-",
            "bill_date": row.bill_date,
            "item_code": row.item_code,
            "item_name": row.item_name or row.item_code,
            "qty": flt(row.qty),
            "uom": row.uom or "-",
            "rate": flt(row.rate),
            "amount": amt,
            "cgst": cgst,
            "sgst": sgst,
            "igst": igst,
            "total_tax": tot_tax,
            "grand_total": grand_total,
            "warehouse": row.warehouse or "-",
            "status": row.status
        })

    return rows
