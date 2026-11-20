import json
import io
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, today

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data, totals, final_balance, final_balance_type = get_data(filters)
    report_summary = get_report_summary(totals, final_balance, final_balance_type)
    chart = get_chart_data(data)

    return columns, data, None, chart, report_summary


def get_columns():
    return [
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 180
        },
        {
            "label": _("Party Type"),
            "fieldname": "party_type",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Party"),
            "fieldname": "party",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": _("Ref / Bill No"),
            "fieldname": "bill_no",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": _("Against Account"),
            "fieldname": "against_account",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": _("Debit (₹)"),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Credit (₹)"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("Net Balance (₹)"),
            "fieldname": "balance",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Dr / Cr"),
            "fieldname": "balance_type",
            "fieldtype": "Data",
            "width": 70
        },
        {
            "label": _("Remarks"),
            "fieldname": "remarks",
            "fieldtype": "Data",
            "width": 220
        }
    ]


def get_data(filters):
    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    customer = filters.get("customer")
    supplier = filters.get("supplier")

    # Smart auto-matching if only one party is chosen
    if customer and not supplier:
        supplier = find_matching_supplier(customer)
    elif supplier and not customer:
        customer = find_matching_customer(supplier)

    if not customer and not supplier:
        return [], {}, 0.0, "Dr"

    from_date = filters.get("from_date")
    to_date = filters.get("to_date") or today()

    # Party condition clause
    party_conditions = []
    party_params = {"company": company, "from_date": from_date, "to_date": to_date}

    if customer and supplier:
        party_conditions.append("( (gle.party_type = 'Customer' AND gle.party = %(customer)s) OR (gle.party_type = 'Supplier' AND gle.party = %(supplier)s) )")
        party_params["customer"] = customer
        party_params["supplier"] = supplier
    elif customer:
        party_conditions.append("(gle.party_type = 'Customer' AND gle.party = %(customer)s)")
        party_params["customer"] = customer
    elif supplier:
        party_conditions.append("(gle.party_type = 'Supplier' AND gle.party = %(supplier)s)")
        party_params["supplier"] = supplier

    party_cond_sql = " AND ".join(party_conditions)

    # 1. Opening Balance Calculation
    op_debit = 0.0
    op_credit = 0.0
    if from_date:
        op_sql = f"""
            SELECT
                COALESCE(SUM(gle.debit), 0) as op_debit,
                COALESCE(SUM(gle.credit), 0) as op_credit
            FROM `tabGL Entry` gle
            WHERE gle.company = %(company)s
              AND gle.is_cancelled = 0
              AND gle.posting_date < %(from_date)s
              AND {party_cond_sql}
        """
        op_res = frappe.db.sql(op_sql, party_params, as_dict=True)
        if op_res:
            op_debit = flt(op_res[0].op_debit)
            op_credit = flt(op_res[0].op_credit)

    op_net = op_debit - op_credit
    running_balance = op_net

    data = []
    totals = {
        "debit": 0.0,
        "credit": 0.0,
        "sales_billed": 0.0,
        "purchases_billed": 0.0,
        "receipts": 0.0,
        "payments": 0.0
    }

    # Add Opening Row if from_date exists
    if from_date:
        data.append({
            "posting_date": from_date,
            "voucher_type": "",
            "voucher_no": "",
            "party_type": "",
            "party": "",
            "bill_no": "",
            "against_account": _("Opening Balance"),
            "debit": op_net if op_net > 0 else 0.0,
            "credit": abs(op_net) if op_net < 0 else 0.0,
            "balance": abs(op_net),
            "balance_type": "Dr" if op_net >= 0 else "Cr",
            "remarks": _("Opening balance brought forward"),
            "is_opening": 1
        })
        if op_net > 0:
            totals["debit"] += op_net
        elif op_net < 0:
            totals["credit"] += abs(op_net)

    # 2. Fetch Period Transactions
    date_filter = ""
    if from_date and to_date:
        date_filter = "AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s"
    elif to_date:
        date_filter = "AND gle.posting_date <= %(to_date)s"

    gl_sql = f"""
        SELECT
            gle.name as gl_name,
            gle.posting_date,
            gle.voucher_type,
            gle.voucher_no,
            gle.party_type,
            gle.party,
            gle.against as against_account,
            gle.remarks,
            gle.debit,
            gle.credit
        FROM `tabGL Entry` gle
        WHERE gle.company = %(company)s
          AND gle.is_cancelled = 0
          {date_filter}
          AND {party_cond_sql}
        ORDER BY gle.posting_date ASC, gle.creation ASC, gle.name ASC
    """
    gl_entries = frappe.db.sql(gl_sql, party_params, as_dict=True)

    # Pre-fetch Reference Bill Numbers for Sales and Purchase Invoices
    sales_vouchers = [e.voucher_no for e in gl_entries if e.voucher_type == "Sales Invoice"]
    purchase_vouchers = [e.voucher_no for e in gl_entries if e.voucher_type == "Purchase Invoice"]

    bill_map = {}
    if sales_vouchers:
        for row in frappe.db.sql("""SELECT name, po_no FROM `tabSales Invoice` WHERE name IN %s""", [sales_vouchers], as_dict=True):
            if row.po_no:
                bill_map[row.name] = row.po_no

    if purchase_vouchers:
        for row in frappe.db.sql("""SELECT name, bill_no FROM `tabPurchase Invoice` WHERE name IN %s""", [purchase_vouchers], as_dict=True):
            if row.bill_no:
                bill_map[row.name] = row.bill_no

    for e in gl_entries:
        dr = flt(e.debit)
        cr = flt(e.credit)
        running_balance += (dr - cr)

        totals["debit"] += dr
        totals["credit"] += cr

        # Track category statistics
        if e.voucher_type == "Sales Invoice":
            totals["sales_billed"] += dr
        elif e.voucher_type == "Purchase Invoice":
            totals["purchases_billed"] += cr
        elif e.voucher_type == "Payment Entry":
            if e.party_type == "Customer":
                totals["receipts"] += cr
            elif e.party_type == "Supplier":
                totals["payments"] += dr

        data.append({
            "posting_date": e.posting_date,
            "voucher_type": e.voucher_type,
            "voucher_no": e.voucher_no,
            "party_type": e.party_type,
            "party": e.party,
            "bill_no": bill_map.get(e.voucher_no, ""),
            "against_account": e.against_account or "",
            "debit": dr,
            "credit": cr,
            "balance": abs(running_balance),
            "balance_type": "Dr" if running_balance >= 0 else "Cr",
            "remarks": e.remarks or ""
        })

    final_balance = abs(running_balance)
    final_balance_type = "Dr" if running_balance >= 0 else "Cr"

    return data, totals, final_balance, final_balance_type


def get_report_summary(totals, final_balance, final_balance_type):
    if not totals:
        return []

    is_receivable = final_balance_type == "Dr"
    status_label = _("Net Balance (Receivable)") if is_receivable else _("Net Balance (Payable)")
    indicator = "Green" if is_receivable else "Orange"

    return [
        {
            "value": totals.get("sales_billed", 0.0),
            "label": _("Total Sales (Dr)"),
            "datatype": "Currency",
            "currency": "INR"
        },
        {
            "value": totals.get("purchases_billed", 0.0),
            "label": _("Total Purchases (Cr)"),
            "datatype": "Currency",
            "currency": "INR"
        },
        {
            "value": totals.get("receipts", 0.0),
            "label": _("Total Receipts (Cr)"),
            "datatype": "Currency",
            "currency": "INR"
        },
        {
            "value": totals.get("payments", 0.0),
            "label": _("Total Payments (Dr)"),
            "datatype": "Currency",
            "currency": "INR"
        },
        {
            "value": final_balance,
            "label": status_label,
            "datatype": "Currency",
            "currency": "INR",
            "indicator": indicator
        }
    ]


def get_chart_data(data):
    if not data:
        return None

    # Cumulative running balance trend chart (monthly or top entries)
    labels = []
    points = []

    # Sample up to 15 key points for clean rendering
    step = max(1, len(data) // 15)
    for i in range(0, len(data), step):
        row = data[i]
        date_str = str(row.get("posting_date"))
        val = row.get("balance", 0.0)
        if row.get("balance_type") == "Cr":
            val = -val
        labels.append(date_str)
        points.append(val)

    if len(data) - 1 not in range(0, len(data), step):
        last_row = data[-1]
        val = last_row.get("balance", 0.0)
        if last_row.get("balance_type") == "Cr":
            val = -val
        labels.append(str(last_row.get("posting_date")))
        points.append(val)

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Net Position (+Dr / -Cr)"),
                    "values": points
                }
            ]
        },
        "type": "line",
        "colors": ["#2563eb"]
    }


# =========================================================================
# FIFO CONTRA SETTLEMENT AUTOMATION BACKEND
# =========================================================================

@frappe.whitelist()
def find_matching_supplier(customer):
    if not customer:
        return None
    # 1. Same name
    if frappe.db.exists("Supplier", customer):
        return customer
    # 2. Matching GSTIN or PAN
    gstin = frappe.db.get_value("Customer", customer, "gstin")
    pan = frappe.db.get_value("Customer", customer, "pan")
    if gstin:
        match = frappe.db.get_value("Supplier", {"gstin": gstin}, "name")
        if match:
            return match
    if pan:
        match = frappe.db.get_value("Supplier", {"pan": pan}, "name")
        if match:
            return match
    return None


@frappe.whitelist()
def find_matching_customer(supplier):
    if not supplier:
        return None
    # 1. Same name
    if frappe.db.exists("Customer", supplier):
        return supplier
    # 2. Matching GSTIN or PAN
    gstin = frappe.db.get_value("Supplier", supplier, "gstin")
    pan = frappe.db.get_value("Supplier", supplier, "pan")
    if gstin:
        match = frappe.db.get_value("Customer", {"gstin": gstin}, "name")
        if match:
            return match
    if pan:
        match = frappe.db.get_value("Customer", {"pan": pan}, "name")
        if match:
            return match
    return None


@frappe.whitelist()
def get_contra_preview(company, customer, supplier):
    """
    Fetches open Sales Invoices and Purchase Invoices sorted FIFO (oldest first)
    and computes available contra settlement amount.
    """
    if not company:
        frappe.throw(_("Company is required."))
    if not customer:
        frappe.throw(_("Customer is required."))
    if not supplier:
        frappe.throw(_("Supplier is required."))

    # 1. Fetch Open Sales Invoices (FIFO: posting_date ASC, name ASC)
    open_sales = frappe.db.sql("""
        SELECT
            name,
            posting_date,
            due_date,
            grand_total,
            outstanding_amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND company = %s
          AND customer = %s
          AND outstanding_amount > 0.001
        ORDER BY posting_date ASC, name ASC
    """, (company, customer), as_dict=True)

    # 2. Fetch Open Purchase Invoices (FIFO: posting_date ASC, name ASC)
    open_purchases = frappe.db.sql("""
        SELECT
            name,
            posting_date,
            bill_no,
            due_date,
            grand_total,
            outstanding_amount
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1
          AND company = %s
          AND supplier = %s
          AND outstanding_amount > 0.001
        ORDER BY posting_date ASC, name ASC
    """, (company, supplier), as_dict=True)

    total_sales_out = sum(flt(si.outstanding_amount) for si in open_sales)
    total_purchases_out = sum(flt(pi.outstanding_amount) for pi in open_purchases)
    max_contra = min(total_sales_out, total_purchases_out)

    customer_title = frappe.db.get_value("Customer", customer, "customer_name") or customer
    supplier_title = frappe.db.get_value("Supplier", supplier, "supplier_name") or supplier

    return {
        "customer": customer,
        "customer_name": customer_title,
        "supplier": supplier,
        "supplier_name": supplier_title,
        "open_sales": open_sales,
        "open_purchases": open_purchases,
        "total_sales_outstanding": total_sales_out,
        "total_purchases_outstanding": total_purchases_out,
        "max_contra_amount": max_contra
    }


@frappe.whitelist()
def execute_fifo_contra_settlement(company, customer, supplier, settlement_amount=None, posting_date=None, user_remark=None):
    """
    Performs automated FIFO allocation across open Sales Invoices and Purchase Invoices,
    creates and submits a Contra Journal Entry, knocking off both sets of invoices.
    """
    if not company or not customer or not supplier:
        frappe.throw(_("Company, Customer, and Supplier are required for Contra Settlement."))

    preview = get_contra_preview(company, customer, supplier)
    open_sales = preview["open_sales"]
    open_purchases = preview["open_purchases"]
    max_contra = preview["max_contra_amount"]

    if max_contra <= 0.001:
        frappe.throw(_("No mutual outstanding balance found to settle."))

    settle_amt = flt(settlement_amount) if settlement_amount else max_contra
    if settle_amt <= 0.001:
        frappe.throw(_("Settlement amount must be greater than zero."))
    if settle_amt > max_contra + 0.01:
        frappe.throw(_("Settlement amount cannot exceed the maximum mutual contra amount of ₹{0}.").format(frappe.format(max_contra, "Currency")))

    posting_date = posting_date or today()

    # 1. FIFO Allocation for Sales Invoices (Customer Side - Credit to decrease receivable)
    sales_allocations = []
    rem_sales = settle_amt
    for si in open_sales:
        if rem_sales <= 0.001:
            break
        alloc = min(flt(si.outstanding_amount), rem_sales)
        sales_allocations.append({
            "invoice": si.name,
            "amount": alloc
        })
        rem_sales -= alloc

    # 2. FIFO Allocation for Purchase Invoices (Supplier Side - Debit to decrease payable)
    purchase_allocations = []
    rem_purchases = settle_amt
    for pi in open_purchases:
        if rem_purchases <= 0.001:
            break
        alloc = min(flt(pi.outstanding_amount), rem_purchases)
        purchase_allocations.append({
            "invoice": pi.name,
            "amount": alloc
        })
        rem_purchases -= alloc

    # 3. Determine Accounts
    receivable_account = None
    payable_account = None

    try:
        from erpnext.accounts.party import get_party_account
        receivable_account = get_party_account("Customer", customer, company)
        payable_account = get_party_account("Supplier", supplier, company)
    except Exception:
        pass

    if not receivable_account:
        receivable_account = frappe.db.get_value("Company", company, "default_receivable_account")
    if not payable_account:
        payable_account = frappe.db.get_value("Company", company, "default_payable_account")

    if not receivable_account or not payable_account:
        frappe.throw(_("Could not determine Receivable/Payable accounts for Company {0}.").format(company))

    # Cost Center
    cost_center = frappe.db.get_value("Company", company, "cost_center")
    if not cost_center:
        cost_center = frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")

    # 4. Create Journal Entry
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = company
    je.posting_date = posting_date
    je.user_remark = user_remark or _("Mutual FIFO Contra Settlement between Customer {0} and Supplier {1}").format(customer, supplier)

    # Debit Lines: Supplier / Purchase Invoices (reduces creditor balance)
    for p_alloc in purchase_allocations:
        je.append("accounts", {
            "account": payable_account,
            "party_type": "Supplier",
            "party": supplier,
            "cost_center": cost_center,
            "debit_in_account_currency": p_alloc["amount"],
            "reference_type": "Purchase Invoice",
            "reference_name": p_alloc["invoice"]
        })

    # Credit Lines: Customer / Sales Invoices (reduces debtor balance)
    for s_alloc in sales_allocations:
        je.append("accounts", {
            "account": receivable_account,
            "party_type": "Customer",
            "party": customer,
            "cost_center": cost_center,
            "credit_in_account_currency": s_alloc["amount"],
            "reference_type": "Sales Invoice",
            "reference_name": s_alloc["invoice"]
        })

    je.save(ignore_permissions=True)
    je.submit()

    return {
        "success": True,
        "journal_entry": je.name,
        "settled_amount": settle_amt,
        "sales_allocations": sales_allocations,
        "purchase_allocations": purchase_allocations
    }


# =========================================================================
# EXCEL DOWNLOAD
# =========================================================================

@frappe.whitelist()
def download_custom_excel(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    if not filters:
        filters = {}

    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    customer = filters.get("customer", "")
    supplier = filters.get("supplier", "")
    from_date = filters.get("from_date", "")
    to_date = filters.get("to_date", today())

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Combined Party Ledger"

    # Fonts & Styles
    title_font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
    sub_font = Font(name="Calibri", size=10, bold=True, color="374151")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    normal_font = Font(name="Calibri", size=10)
    bold_font = Font(name="Calibri", size=10, bold=True)
    thin_side = Side(style="thin", color="D1D5DB")
    grid_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    op_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    # Title
    ws.merge_cells("A1:L1")
    ws["A1"] = f"COMBINED PARTY LEDGER - {company}"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 25

    # Subtitle
    ws.merge_cells("A2:L2")
    party_str = f"Customer: {customer} | Supplier: {supplier}" if customer and supplier else f"Party: {customer or supplier}"
    ws["A2"] = f"Period: {from_date} to {to_date}   |   {party_str}"
    ws["A2"].font = sub_font
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 18

    row_idx = 4
    headers = [
        "Posting Date",
        "Voucher Type",
        "Voucher No",
        "Party Type",
        "Party",
        "Ref / Bill No",
        "Against Account",
        "Debit (₹)",
        "Credit (₹)",
        "Net Balance (₹)",
        "Dr/Cr",
        "Remarks"
    ]

    header_row = row_idx
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = grid_border

    row_idx += 1

    data, totals, final_bal, final_bal_type = get_data(filters)

    for r in data:
        is_op = r.get("is_opening")
        fill_to_apply = op_fill if is_op else None

        c1 = ws.cell(row=row_idx, column=1, value=str(r.get("posting_date", "")))
        c2 = ws.cell(row=row_idx, column=2, value=r.get("voucher_type", ""))
        c3 = ws.cell(row=row_idx, column=3, value=r.get("voucher_no", ""))
        c4 = ws.cell(row=row_idx, column=4, value=r.get("party_type", ""))
        c5 = ws.cell(row=row_idx, column=5, value=r.get("party", ""))
        c6 = ws.cell(row=row_idx, column=6, value=r.get("bill_no", ""))
        c7 = ws.cell(row=row_idx, column=7, value=r.get("against_account", ""))

        c8 = ws.cell(row=row_idx, column=8, value=flt(r.get("debit", 0.0)))
        c8.number_format = "#,##0.00"
        c8.alignment = Alignment(horizontal="right")

        c9 = ws.cell(row=row_idx, column=9, value=flt(r.get("credit", 0.0)))
        c9.number_format = "#,##0.00"
        c9.alignment = Alignment(horizontal="right")

        c10 = ws.cell(row=row_idx, column=10, value=flt(r.get("balance", 0.0)))
        c10.number_format = "#,##0.00"
        c10.alignment = Alignment(horizontal="right")

        c11 = ws.cell(row=row_idx, column=11, value=r.get("balance_type", ""))
        c11.alignment = Alignment(horizontal="center")

        c12 = ws.cell(row=row_idx, column=12, value=r.get("remarks", ""))

        for c in [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12]:
            c.font = bold_font if is_op else normal_font
            c.border = grid_border
            if fill_to_apply:
                c.fill = fill_to_apply

        row_idx += 1

    # Totals Row
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=7)
    tot_label = ws.cell(row=row_idx, column=1, value="Total Period Movement")
    tot_label.font = bold_font
    tot_label.alignment = Alignment(horizontal="right")

    for col in range(1, 8):
        ws.cell(row=row_idx, column=col).border = grid_border

    tot_dr = ws.cell(row=row_idx, column=8, value=flt(totals.get("debit", 0.0)))
    tot_dr.font = bold_font
    tot_dr.number_format = "#,##0.00"
    tot_dr.alignment = Alignment(horizontal="right")
    tot_dr.border = grid_border

    tot_cr = ws.cell(row=row_idx, column=9, value=flt(totals.get("credit", 0.0)))
    tot_cr.font = bold_font
    tot_cr.number_format = "#,##0.00"
    tot_cr.alignment = Alignment(horizontal="right")
    tot_cr.border = grid_border

    net_c = ws.cell(row=row_idx, column=10, value=final_bal)
    net_c.font = bold_font
    net_c.number_format = "#,##0.00"
    net_c.alignment = Alignment(horizontal="right")
    net_c.border = grid_border

    net_t = ws.cell(row=row_idx, column=11, value=final_bal_type)
    net_t.font = bold_font
    net_t.alignment = Alignment(horizontal="center")
    net_t.border = grid_border

    ws.cell(row=row_idx, column=12, value="").border = grid_border

    # Adjust column widths
    col_widths = {
        "A": 13, "B": 17, "C": 22, "D": 13, "E": 25, "F": 16,
        "G": 22, "H": 16, "I": 16, "J": 18, "K": 9, "L": 30
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.response["filename"] = f"Combined_Party_Ledger_{company}_{today()}.xlsx"
    frappe.response["filecontent"] = output.getvalue()
    frappe.response["type"] = "binary"
