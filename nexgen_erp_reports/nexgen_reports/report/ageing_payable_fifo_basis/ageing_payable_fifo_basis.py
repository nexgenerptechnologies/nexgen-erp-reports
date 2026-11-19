import json
import io
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, today

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data, totals = get_data(filters)
    chart = get_chart_data(totals)
    report_summary = get_report_summary(totals)

    return columns, data, None, chart, report_summary


def get_columns():
    return [
        {
            "label": _("Party Details"),
            "fieldname": "party_name",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 300
        },
        {
            "label": _("Closing Amt"),
            "fieldname": "closing_amt",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("( 0 - 30 ) Days"),
            "fieldname": "range1",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("( 31 - 60 ) Days"),
            "fieldname": "range2",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("( 61 - 90 ) Days"),
            "fieldname": "range3",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("( 91 - 120 ) Days"),
            "fieldname": "range4",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("( 121 - 150 ) Days"),
            "fieldname": "range5",
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "label": _("( >= 151 ) Days"),
            "fieldname": "range6",
            "fieldtype": "Currency",
            "width": 140
        }
    ]


def get_data(filters):
    as_on_date = getdate(filters.get("report_date") or filters.get("as_on_date") or today())
    company = filters.get("company") or frappe.defaults.get_user_default("Company")

    conditions = ["gle.company = %(company)s", "gle.party_type = 'Supplier'", "gle.posting_date <= %(as_on_date)s", "gle.is_cancelled = 0"]
    query_params = {"company": company, "as_on_date": as_on_date}

    if filters.get("supplier"):
        conditions.append("gle.party = %(supplier)s")
        query_params["supplier"] = filters.get("supplier")

    if filters.get("supplier_group"):
        supp_list = frappe.get_all("Supplier", filters={"supplier_group": filters.get("supplier_group")}, pluck="name")
        if supp_list:
            conditions.append("gle.party IN %(supp_list)s")
            query_params["supp_list"] = supp_list
        else:
            return [], {}

    cond_sql = " AND ".join(conditions)

    # 1. Fetch closing balances for all suppliers (credit - debit)
    balance_query = f"""
        SELECT
            gle.party,
            SUM(gle.credit) - SUM(gle.debit) as closing_balance
        FROM `tabGL Entry` gle
        WHERE {cond_sql}
        GROUP BY gle.party
        HAVING closing_balance > 0.005
        ORDER BY gle.party ASC
    """
    party_balances = frappe.db.sql(balance_query, query_params, as_dict=True)

    if not party_balances:
        return [], {}

    # Map party names
    parties = [p.party for p in party_balances]
    supp_records = frappe.get_all(
        "Supplier",
        filters={"name": ["in", parties]},
        fields=["name", "supplier_name"]
    )
    supp_name_map = {s.name: (s.supplier_name or s.name) for s in supp_records}

    # 2. Fetch all credit entries for these suppliers up to as_on_date (newest to oldest for FIFO)
    query_params["parties"] = parties
    credit_query = f"""
        SELECT
            gle.party,
            gle.posting_date,
            gle.credit
        FROM `tabGL Entry` gle
        WHERE gle.company = %(company)s
          AND gle.party_type = 'Supplier'
          AND gle.party IN %(parties)s
          AND gle.posting_date <= %(as_on_date)s
          AND gle.is_cancelled = 0
          AND gle.credit > 0
        ORDER BY gle.party, gle.posting_date DESC, gle.creation DESC
    """
    credit_entries = frappe.db.sql(credit_query, query_params, as_dict=True)

    # Group credit entries by party
    party_credits = {}
    for c in credit_entries:
        party_credits.setdefault(c.party, []).append(c)

    data = []
    totals = {
        "closing_amt": 0.0,
        "range1": 0.0,
        "range2": 0.0,
        "range3": 0.0,
        "range4": 0.0,
        "range5": 0.0,
        "range6": 0.0
    }

    # 3. Apply FIFO Allocation
    for row in party_balances:
        party = row.party
        balance = flt(row.closing_balance)
        rem = balance

        r1 = r2 = r3 = r4 = r5 = r6 = 0.0

        for entry in party_credits.get(party, []):
            cred_amt = flt(entry.credit)
            if cred_amt <= 0:
                continue

            alloc = min(cred_amt, rem)
            entry_date = getdate(entry.posting_date)
            days = (as_on_date - entry_date).days

            if days <= 30:
                r1 += alloc
            elif days <= 60:
                r2 += alloc
            elif days <= 90:
                r3 += alloc
            elif days <= 120:
                r4 += alloc
            elif days <= 150:
                r5 += alloc
            else:
                r6 += alloc

            rem -= alloc
            if rem <= 0.0001:
                break

        # If any remaining balance exists (e.g. legacy opening balances), put in >=151 days
        if rem > 0.0001:
            r6 += rem

        party_display_name = supp_name_map.get(party, party)

        row_data = {
            "party": party,
            "party_name": party_display_name,
            "closing_amt": balance,
            "range1": r1,
            "range2": r2,
            "range3": r3,
            "range4": r4,
            "range5": r5,
            "range6": r6,
        }
        data.append(row_data)

        totals["closing_amt"] += balance
        totals["range1"] += r1
        totals["range2"] += r2
        totals["range3"] += r3
        totals["range4"] += r4
        totals["range5"] += r5
        totals["range6"] += r6

    return data, totals


def get_chart_data(totals):
    if not totals or not totals.get("closing_amt"):
        return None

    return {
        "data": {
            "labels": [
                _("0 - 30 Days"),
                _("31 - 60 Days"),
                _("61 - 90 Days"),
                _("91 - 120 Days"),
                _("121 - 150 Days"),
                _(">= 151 Days"),
            ],
            "datasets": [
                {
                    "name": _("Payables"),
                    "values": [
                        totals.get("range1", 0.0),
                        totals.get("range2", 0.0),
                        totals.get("range3", 0.0),
                        totals.get("range4", 0.0),
                        totals.get("range5", 0.0),
                        totals.get("range6", 0.0),
                    ]
                }
            ]
        },
        "type": "donut",
        "colors": ["#10b981", "#3b82f6", "#f59e0b", "#f97316", "#ef4444", "#7f1d1d"]
    }


def get_report_summary(totals):
    if not totals:
        return []

    return [
        {"value": totals.get("closing_amt", 0.0), "indicator": "Blue", "label": _("Total Outstanding Payable"), "datatype": "Currency"},
        {"value": totals.get("range1", 0.0), "indicator": "Green", "label": _("0 - 30 Days"), "datatype": "Currency"},
        {"value": totals.get("range2", 0.0), "indicator": "Blue", "label": _("31 - 60 Days"), "datatype": "Currency"},
        {"value": totals.get("range3", 0.0), "indicator": "Orange", "label": _("61 - 90 Days"), "datatype": "Currency"},
        {"value": totals.get("range4", 0.0) + totals.get("range5", 0.0) + totals.get("range6", 0.0), "indicator": "Red", "label": _("> 90 Days"), "datatype": "Currency"}
    ]


@frappe.whitelist()
def download_custom_excel(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    if not filters:
        filters = {}

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    as_on_date = getdate(filters.get("report_date") or filters.get("as_on_date") or today())

    company_doc = frappe.get_doc("Company", company) if company else None
    company_name = company_doc.name if company_doc else "NexGen Enterprises"

    # Registered address
    address_lines = []
    if company:
        address_name = None
        try:
            from frappe.contacts.doctype.address.address import get_default_address
            address_name = get_default_address("Company", company)
        except Exception:
            pass

        if not address_name:
            address_name = frappe.db.get_value(
                "Dynamic Link",
                {"link_doctype": "Company", "link_name": company, "parenttype": "Address"},
                "parent"
            )

        if address_name:
            addr = frappe.get_doc("Address", address_name)
            if addr.address_line1:
                address_lines.append(addr.address_line1)
            if addr.address_line2:
                address_lines.append(addr.address_line2)
            city_pin = f"{addr.city or ''}, {addr.state or ''} {addr.pincode or ''}".strip()
            if city_pin:
                address_lines.append(city_pin)

    if not address_lines:
        address_lines = [
            "505, Tower CS-1, 5th Floor, Supertech, Capetown, Sector 74, Plot No-GH-01/A",
            "Noida, Gautambuddha Nagar, Uttar Pradesh, 201301"
        ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ageing Payables"
    ws.views.sheetView[0].showGridLines = True

    # Styles
    title_font = Font(name="Calibri", size=11, bold=True)
    header_fill = PatternFill(start_color="336699", end_color="336699", fill_type="solid")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=10, bold=True)
    normal_font = Font(name="Calibri", size=10)
    thin_border_side = Side(style="thin", color="D3D3D3")
    grid_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    # 1. Company Name
    ws.cell(row=1, column=1, value=company_name).font = title_font

    # 2. Address Lines
    row_idx = 2
    for line in address_lines:
        ws.cell(row=row_idx, column=1, value=line).font = normal_font
        row_idx += 1

    # 3. Report Title
    ws.cell(row=row_idx, column=1, value="Ageing Payables (FIFO Basis)").font = title_font
    row_idx += 1

    # 4. Status Date line
    as_on_str = formatdate(as_on_date, "dd-mm-yyyy")
    ws.cell(row=row_idx, column=1, value="All Accounts").font = title_font
    status_cell = ws.cell(row=row_idx, column=5, value=f"Account Status as on : {as_on_str}")
    status_cell.font = title_font
    row_idx += 1

    # 5. Table Headers
    headers = [
        "Party Details",
        "Closing Amt",
        "( 0 - 30 ) Days",
        "( 31 - 60 ) Days",
        "( 61 - 90 ) Days",
        "( 91 - 120 ) Days",
        "( 121 - 150 ) Days",
        "( >= 151 ) Days"
    ]

    header_row = row_idx
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left", vertical="center")
        cell.border = grid_border

    row_idx += 1

    # Fetch data
    data, totals = get_data(filters)

    for r in data:
        c1 = ws.cell(row=row_idx, column=1, value=r.get("party_name", ""))
        c1.font = normal_font
        c1.border = grid_border

        for c_idx, key in enumerate(["closing_amt", "range1", "range2", "range3", "range4", "range5", "range6"], start=2):
            val = flt(r.get(key, 0.0))
            c = ws.cell(row=row_idx, column=c_idx, value=val if val > 0 else "")
            c.font = normal_font
            c.number_format = "#,##0.00"
            c.alignment = Alignment(horizontal="right")
            c.border = grid_border

        row_idx += 1

    # Total Row
    ws.cell(row=row_idx, column=1, value="Total").font = bold_font
    ws.cell(row=row_idx, column=1).border = grid_border

    for c_idx, key in enumerate(["closing_amt", "range1", "range2", "range3", "range4", "range5", "range6"], start=2):
        val = flt(totals.get(key, 0.0))
        c = ws.cell(row=row_idx, column=c_idx, value=val)
        c.font = bold_font
        c.number_format = "#,##0.00"
        c.alignment = Alignment(horizontal="right")
        c.border = grid_border

    # Column Widths
    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 16
    ws.column_dimensions["F"].width = 16
    ws.column_dimensions["G"].width = 16
    ws.column_dimensions["H"].width = 16

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.response["filename"] = f"Ageing_Payables_FIFO_{company_name.replace(' ', '_')}_{as_on_str}.xlsx"
    frappe.response["filecontent"] = output.getvalue()
    frappe.response["type"] = "binary"
