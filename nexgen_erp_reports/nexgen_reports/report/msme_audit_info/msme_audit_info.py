import json
import io
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, today, date_diff

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data, totals = get_data(filters)
    report_summary = get_report_summary(totals)
    chart = get_chart_data(totals)

    return columns, data, None, chart, report_summary


def get_columns():
    return [
        {
            "label": _("Name of MSME Supplier"),
            "fieldname": "supplier_name",
            "fieldtype": "Data",
            "width": 240
        },
        {
            "label": _("PAN of the Supplier"),
            "fieldname": "pan",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("MSME Status"),
            "fieldname": "msme_status",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Udyam No."),
            "fieldname": "udyam_no",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": _("No. of Pymts via TReDS(<=45 Days)"),
            "fieldname": "treds_count",
            "fieldtype": "Int",
            "width": 130
        },
        {
            "label": _("Amt. Paid via TReDS(Rs.)"),
            "fieldname": "treds_amt",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("No. of Pymts via Other Pymt Modes (<=45 Days)"),
            "fieldname": "other_count",
            "fieldtype": "Int",
            "width": 140
        },
        {
            "label": _("Amt. Paid via Other Modes(Rs.)"),
            "fieldname": "other_amt",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Invoices paid (> 45 Days)"),
            "fieldname": "delayed_count",
            "fieldtype": "Int",
            "width": 130
        },
        {
            "label": _("Amt. Paid (> 45 Days)(Rs.)"),
            "fieldname": "delayed_amt",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Pending Invoices (<= 45 days)"),
            "fieldname": "pending_45_count",
            "fieldtype": "Int",
            "width": 130
        },
        {
            "label": _("Outstanding Amt. (<= 45 days)(Rs.)"),
            "fieldname": "pending_45_amt",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Pending Invoices (> 45 days)"),
            "fieldname": "overdue_45_count",
            "fieldtype": "Int",
            "width": 130
        },
        {
            "label": _("Outstanding Amt. (> 45 day)(Rs.)"),
            "fieldname": "overdue_45_amt",
            "fieldtype": "Currency",
            "width": 150
        }
    ]


def get_data(filters):
    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date") or today()
    as_on_date = getdate(filters.get("as_on_date") or today())
    date_basis = filters.get("date_basis") or "Bill Date"
    msme_filter = filters.get("msme_filter") or "All MSME (Micro & Small & Medium)"
    supplier_filter = filters.get("supplier")

    # 1. Fetch Suppliers matching MSME criteria
    has_msme_status = frappe.db.has_column("Supplier", "msme_status")
    has_udyam_no = frappe.db.has_column("Supplier", "udyam_no")

    supplier_conditions = ["1=1"]
    supplier_params = {}

    if supplier_filter:
        supplier_conditions.append("s.name = %(supplier)s")
        supplier_params["supplier"] = supplier_filter

    if has_msme_status:
        if msme_filter == "Micro & Small (Sec 43B(h))":
            supplier_conditions.append("s.msme_status IN ('Micro', 'Small')")
        elif msme_filter == "Micro":
            supplier_conditions.append("s.msme_status = 'Micro'")
        elif msme_filter == "Small":
            supplier_conditions.append("s.msme_status = 'Small'")
        elif msme_filter == "Medium":
            supplier_conditions.append("s.msme_status = 'Medium'")
        elif msme_filter == "All MSME (Micro & Small & Medium)":
            supplier_conditions.append("s.msme_status IN ('Micro', 'Small', 'Medium')")
        # 'All Suppliers' has no msme_status condition
    else:
        # If columns not yet created, don't restrict so user can preview data
        pass

    supp_cond_sql = " AND ".join(supplier_conditions)

    msme_expr = "s.msme_status" if has_msme_status else "'' as msme_status"
    udyam_expr = "s.udyam_no" if has_udyam_no else "'' as udyam_no"

    suppliers_query = f"""
        SELECT
            s.name,
            s.supplier_name,
            s.pan,
            {msme_expr},
            {udyam_expr}
        FROM `tabSupplier` s
        WHERE {supp_cond_sql}
    """
    suppliers_list = frappe.db.sql(suppliers_query, supplier_params, as_dict=True)

    # If MSME filter resulted in 0 suppliers (e.g. before user has marked them), fallback to suppliers with invoices
    if not suppliers_list and msme_filter in ["All MSME (Micro & Small & Medium)", "Micro & Small (Sec 43B(h))"]:
        fallback_query = f"""
            SELECT
                s.name,
                s.supplier_name,
                s.pan,
                {msme_expr},
                {udyam_expr}
            FROM `tabSupplier` s
            WHERE EXISTS (
                SELECT 1 FROM `tabPurchase Invoice` pi
                WHERE pi.supplier = s.name AND pi.company = %(company)s AND pi.docstatus = 1
            )
        """
        suppliers_list = frappe.db.sql(fallback_query, {"company": company}, as_dict=True)

    if not suppliers_list:
        return [], {}

    supplier_map = {s.name: s for s in suppliers_list}
    supplier_names = list(supplier_map.keys())

    # 2. Fetch Purchase Invoices within date range
    date_col = "COALESCE(pi.bill_date, pi.posting_date)" if date_basis == "Bill Date" else "pi.posting_date"

    inv_sql = f"""
        SELECT
            pi.name,
            pi.supplier,
            pi.bill_no,
            pi.bill_date,
            pi.posting_date,
            pi.due_date,
            pi.grand_total,
            pi.outstanding_amount,
            pi.is_paid,
            pi.paid_amount,
            {date_col} as invoice_date
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1
          AND pi.company = %(company)s
          AND pi.supplier IN %(suppliers)s
          AND {date_col} BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY {date_col} ASC, pi.name ASC
    """
    invoices = frappe.db.sql(inv_sql, {
        "company": company,
        "suppliers": supplier_names,
        "from_date": from_date or "1900-01-01",
        "to_date": to_date
    }, as_dict=True)

    invoice_names = [inv.name for inv in invoices]

    # Pre-fetch Payment Entry allocations
    pe_allocations = {}
    if invoice_names:
        pe_sql = """
            SELECT
                per.reference_name as invoice,
                pe.name as payment_entry,
                pe.posting_date as payment_date,
                pe.mode_of_payment,
                pe.remarks,
                per.allocated_amount
            FROM `tabPayment Entry Reference` per
            JOIN `tabPayment Entry` pe ON pe.name = per.parent
            WHERE per.reference_doctype = 'Purchase Invoice'
              AND per.reference_name IN %(invoices)s
              AND pe.docstatus = 1
              AND pe.posting_date <= %(as_on_date)s
            ORDER BY pe.posting_date ASC
        """
        for r in frappe.db.sql(pe_sql, {"invoices": invoice_names, "as_on_date": as_on_date}, as_dict=True):
            pe_allocations.setdefault(r.invoice, []).append(r)

    # Pre-fetch Journal Entry allocations (e.g. Contra entries, debit notes)
    je_allocations = {}
    if invoice_names:
        je_sql = """
            SELECT
                jea.reference_name as invoice,
                je.name as journal_entry,
                je.posting_date as payment_date,
                je.user_remark as remarks,
                jea.debit_in_account_currency as allocated_amount
            FROM `tabJournal Entry Account` jea
            JOIN `tabJournal Entry` je ON je.name = jea.parent
            WHERE jea.reference_type = 'Purchase Invoice'
              AND jea.reference_name IN %(invoices)s
              AND je.docstatus = 1
              AND je.posting_date <= %(as_on_date)s
              AND jea.debit_in_account_currency > 0
            ORDER BY je.posting_date ASC
        """
        for r in frappe.db.sql(je_sql, {"invoices": invoice_names, "as_on_date": as_on_date}, as_dict=True):
            je_allocations.setdefault(r.invoice, []).append(r)

    # 3. Process Invoices and aggregate per Supplier
    supplier_agg = {}

    for s_name in supplier_names:
        s_obj = supplier_map[s_name]
        supplier_agg[s_name] = {
            "supplier_name": s_obj.supplier_name or s_name,
            "pan": s_obj.pan or "",
            "msme_status": s_obj.msme_status or "Micro",
            "udyam_no": s_obj.udyam_no or "",
            "treds_count": 0,
            "treds_amt": 0.0,
            "other_count": 0,
            "other_amt": 0.0,
            "delayed_count": 0,
            "delayed_amt": 0.0,
            "pending_45_count": 0,
            "pending_45_amt": 0.0,
            "overdue_45_count": 0,
            "overdue_45_amt": 0.0,
            "has_activity": False
        }

    for inv in invoices:
        s_name = inv.supplier
        if s_name not in supplier_agg:
            continue

        agg = supplier_agg[s_name]
        agg["has_activity"] = True

        inv_date = getdate(inv.invoice_date)
        grand_total = flt(inv.grand_total)

        total_paid_as_on = 0.0
        matched_payments = pe_allocations.get(inv.name, [])
        matched_jes = je_allocations.get(inv.name, [])

        # Process Payment Entries
        for pe in matched_payments:
            pay_date = getdate(pe.payment_date)
            amt = flt(pe.allocated_amount)
            days = date_diff(pay_date, inv_date)

            is_treds = "treds" in (pe.mode_of_payment or "").lower() or "treds" in (pe.remarks or "").lower()

            if days <= 45:
                if is_treds:
                    agg["treds_count"] += 1
                    agg["treds_amt"] += amt
                else:
                    agg["other_count"] += 1
                    agg["other_amt"] += amt
            else:
                agg["delayed_count"] += 1
                agg["delayed_amt"] += amt

            total_paid_as_on += amt

        # Process Journal Entries
        for je in matched_jes:
            pay_date = getdate(je.payment_date)
            amt = flt(je.allocated_amount)
            days = date_diff(pay_date, inv_date)

            is_treds = "treds" in (je.remarks or "").lower()

            if days <= 45:
                if is_treds:
                    agg["treds_count"] += 1
                    agg["treds_amt"] += amt
                else:
                    agg["other_count"] += 1
                    agg["other_amt"] += amt
            else:
                agg["delayed_count"] += 1
                agg["delayed_amt"] += amt

            total_paid_as_on += amt

        # Fallback if marked is_paid directly on invoice without separate Payment Entry
        if not matched_payments and not matched_jes and (inv.is_paid == 1 or flt(inv.outstanding_amount) <= 0.01):
            pay_date = getdate(inv.posting_date)
            days = date_diff(pay_date, inv_date)
            amt = flt(inv.paid_amount) or grand_total

            if days <= 45:
                agg["other_count"] += 1
                agg["other_amt"] += amt
            else:
                agg["delayed_count"] += 1
                agg["delayed_amt"] += amt

            total_paid_as_on += amt

        # Outstanding calculation as of as_on_date
        rem_outstanding = max(0.0, grand_total - total_paid_as_on)
        if rem_outstanding > 0.01:
            days_pending = date_diff(as_on_date, inv_date)
            if days_pending <= 45:
                agg["pending_45_count"] += 1
                agg["pending_45_amt"] += rem_outstanding
            else:
                agg["overdue_45_count"] += 1
                agg["overdue_45_amt"] += rem_outstanding

    # Build final data array (only suppliers with transactions or filtered)
    data = []
    totals = {
        "treds_count": 0,
        "treds_amt": 0.0,
        "other_count": 0,
        "other_amt": 0.0,
        "delayed_count": 0,
        "delayed_amt": 0.0,
        "pending_45_count": 0,
        "pending_45_amt": 0.0,
        "overdue_45_count": 0,
        "overdue_45_amt": 0.0
    }

    for s_name in sorted(supplier_names, key=lambda x: supplier_agg[x]["supplier_name"]):
        agg = supplier_agg[s_name]
        if not agg["has_activity"] and not supplier_filter:
            continue

        data.append(agg)
        for key in totals:
            totals[key] += agg[key]

    # Add single Total row at the bottom
    if data:
        data.append({
            "supplier_name": _("Total"),
            "pan": "",
            "msme_status": "",
            "udyam_no": "",
            "treds_count": totals["treds_count"],
            "treds_amt": totals["treds_amt"],
            "other_count": totals["other_count"],
            "other_amt": totals["other_amt"],
            "delayed_count": totals["delayed_count"],
            "delayed_amt": totals["delayed_amt"],
            "pending_45_count": totals["pending_45_count"],
            "pending_45_amt": totals["pending_45_amt"],
            "overdue_45_count": totals["overdue_45_count"],
            "overdue_45_amt": totals["overdue_45_amt"],
            "is_total_row": 1
        })

    return data, totals


def get_report_summary(totals):
    if not totals:
        return []

    return [
        {
            "value": totals.get("other_amt", 0.0) + totals.get("treds_amt", 0.0),
            "label": _("Paid On Time (<= 45 Days)"),
            "datatype": "Currency",
            "currency": "INR",
            "indicator": "Green"
        },
        {
            "value": totals.get("delayed_amt", 0.0),
            "label": _("Paid with Delay (> 45 Days)"),
            "datatype": "Currency",
            "currency": "INR",
            "indicator": "Orange"
        },
        {
            "value": totals.get("pending_45_amt", 0.0),
            "label": _("Pending Dues (<= 45 Days)"),
            "datatype": "Currency",
            "currency": "INR",
            "indicator": "Blue"
        },
        {
            "value": totals.get("overdue_45_amt", 0.0),
            "label": _("Critical Overdue (> 45 Days) - 43B(h)"),
            "datatype": "Currency",
            "currency": "INR",
            "indicator": "Red"
        }
    ]


def get_chart_data(totals):
    if not totals:
        return None

    return {
        "data": {
            "labels": [
                _("Paid <= 45 Days"),
                _("Paid > 45 Days"),
                _("Pending <= 45 Days"),
                _("Overdue > 45 Days (43B(h))")
            ],
            "datasets": [
                {
                    "name": _("Amount (₹)"),
                    "values": [
                        totals.get("other_amt", 0.0) + totals.get("treds_amt", 0.0),
                        totals.get("delayed_amt", 0.0),
                        totals.get("pending_45_amt", 0.0),
                        totals.get("overdue_45_amt", 0.0)
                    ]
                }
            ]
        },
        "type": "percentage",
        "colors": ["#10b981", "#f59e0b", "#3b82f6", "#ef4444"]
    }


# =========================================================================
# EXCEL DOWNLOAD (Matches Busy Accounting CSV Format Exactly)
# =========================================================================

@frappe.whitelist()
def download_custom_excel(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    if not filters:
        filters = {}

    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    from_date = filters.get("from_date", "")
    to_date = filters.get("to_date", today())
    as_on_date = filters.get("as_on_date", today())
    date_basis = filters.get("date_basis", "Bill Date")

    comp_doc = frappe.get_doc("Company", company)
    address_str = ""
    city_str = ""
    if comp_doc.registered_address:
        addr = frappe.get_doc("Address", comp_doc.registered_address)
        address_str = f"{addr.address_line1 or ''}, {addr.address_line2 or ''}".strip(", ")
        city_str = f"{addr.city or ''} {addr.pincode or ''}".strip()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "MSME Audit Info"

    # Styles
    title_font = Font(name="Calibri", size=13, bold=True)
    sub_font = Font(name="Calibri", size=9, bold=False)
    bold_sub_font = Font(name="Calibri", size=9, bold=True)
    header_font = Font(name="Calibri", size=9, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=9)
    bold_font = Font(name="Calibri", size=9, bold=True)

    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    thin_side = Side(style="thin", color="D1D5DB")
    grid_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    # 1. Company Header (Busy Format)
    ws.merge_cells("A1:N1")
    ws["A1"] = company.upper()
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A2:N2")
    ws["A2"] = address_str or "(An ISO 9001:2015 Certified Company)"
    ws["A2"].font = sub_font
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A3:N3")
    ws["A3"] = city_str
    ws["A3"].font = sub_font
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A4:N4")
    ws["A4"] = "MSME Audit Info."
    ws["A4"].font = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
    ws["A4"].alignment = Alignment(horizontal="center", vertical="center")

    # Meta Info Row
    ws["A5"] = "All Accounts"
    ws["A5"].font = bold_sub_font
    ws["H5"] = f"On Basis of : {date_basis}"
    ws["H5"].font = bold_sub_font

    ws["A6"] = f"From {from_date} to {to_date}"
    ws["A6"].font = bold_sub_font
    ws["H6"] = f"Bills Status as on : {as_on_date}"
    ws["H6"].font = bold_sub_font

    # Column Headers (Row 8)
    row_idx = 8
    headers = [
        "Name of MSME Supplier",
        "PAN of the Supplier",
        "MSME Status",
        "Udyam No.",
        "No. of Pymts via TReDS(<=45 Days)",
        "Amt. Paid via TReDS(Rs.)",
        "No. of Pymts via Other Pymt Modes (<=45 Days)",
        "Amt. Paid via Other Modes(Rs.)",
        "Invoices paid (> 45 Days)",
        "Amt. Paid (> 45 Days)(Rs.)",
        "Pending Invoices (<= 45 days)",
        "Outstanding Amt. (<= 45 days)(Rs.)",
        "Pending Invoices (> 45 days)",
        "Outstanding Amt. (> 45 day)(Rs.)"
    ]

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=row_idx, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = grid_border

    ws.row_dimensions[row_idx].height = 35
    row_idx += 1

    data, totals = get_data(filters)

    for r in data:
        is_total = r.get("is_total_row", 0)

        c1 = ws.cell(row=row_idx, column=1, value=r.get("supplier_name", ""))
        c2 = ws.cell(row=row_idx, column=2, value=r.get("pan", ""))
        c3 = ws.cell(row=row_idx, column=3, value=r.get("msme_status", ""))
        c4 = ws.cell(row=row_idx, column=4, value=r.get("udyam_no", ""))

        c5 = ws.cell(row=row_idx, column=5, value=r.get("treds_count", 0))
        c6 = ws.cell(row=row_idx, column=6, value=flt(r.get("treds_amt", 0.0)))
        c7 = ws.cell(row=row_idx, column=7, value=r.get("other_count", 0))
        c8 = ws.cell(row=row_idx, column=8, value=flt(r.get("other_amt", 0.0)))
        c9 = ws.cell(row=row_idx, column=9, value=r.get("delayed_count", 0))
        c10 = ws.cell(row=row_idx, column=10, value=flt(r.get("delayed_amt", 0.0)))
        c11 = ws.cell(row=row_idx, column=11, value=r.get("pending_45_count", 0))
        c12 = ws.cell(row=row_idx, column=12, value=flt(r.get("pending_45_amt", 0.0)))
        c13 = ws.cell(row=row_idx, column=13, value=r.get("overdue_45_count", 0))
        c14 = ws.cell(row=row_idx, column=14, value=flt(r.get("overdue_45_amt", 0.0)))

        for c_idx, cell in enumerate([c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14], 1):
            cell.font = bold_font if is_total else data_font
            cell.border = grid_border
            if c_idx in [5, 7, 9, 11, 13]:
                cell.alignment = Alignment(horizontal="center")
                cell.number_format = "#,##0"
            elif c_idx in [6, 8, 10, 12, 14]:
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = "#,##0.00"

        row_idx += 1

    # Column widths
    col_widths = {
        "A": 28, "B": 15, "C": 13, "D": 22,
        "E": 14, "F": 16, "G": 14, "H": 16,
        "I": 14, "J": 16, "K": 14, "L": 18,
        "M": 14, "N": 18
    }
    for col_letter, w in col_widths.items():
        ws.column_dimensions[col_letter].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.response["filename"] = f"MSME_Audit_Info_{company}_{today()}.xlsx"
    frappe.response["filecontent"] = output.getvalue()
    frappe.response["type"] = "binary"
