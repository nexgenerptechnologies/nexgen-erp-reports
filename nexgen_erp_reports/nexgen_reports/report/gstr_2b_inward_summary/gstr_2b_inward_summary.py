import json
import io
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data, itc_totals = get_data(filters)
    report_summary = get_report_summary(itc_totals)

    return columns, data, None, None, report_summary


def get_columns():
    return [
        {
            "label": _("Section Name"),
            "fieldname": "section_name",
            "fieldtype": "Data",
            "width": 270
        },
        {
            "label": _("No. of Records"),
            "fieldname": "record_count",
            "fieldtype": "Int",
            "width": 110
        },
        {
            "label": _("Total Taxable Amt."),
            "fieldname": "taxable_amount",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Total Central Tax Amt."),
            "fieldname": "cgst_amount",
            "fieldtype": "Currency",
            "width": 145
        },
        {
            "label": _("Total State/UT Tax Amt."),
            "fieldname": "sgst_amount",
            "fieldtype": "Currency",
            "width": 145
        },
        {
            "label": _("Total Integrated Tax Amt."),
            "fieldname": "igst_amount",
            "fieldtype": "Currency",
            "width": 155
        },
        {
            "label": _("Total CESS"),
            "fieldname": "cess_amount",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Total Central ITC Amt."),
            "fieldname": "cgst_itc",
            "fieldtype": "Currency",
            "width": 145
        },
        {
            "label": _("Total State/UT ITC Amt."),
            "fieldname": "sgst_itc",
            "fieldtype": "Currency",
            "width": 145
        },
        {
            "label": _("Total Integrated ITC Amt."),
            "fieldname": "igst_itc",
            "fieldtype": "Currency",
            "width": 155
        },
        {
            "label": _("Total Cess ITC"),
            "fieldname": "cess_itc",
            "fieldtype": "Currency",
            "width": 120
        }
    ]


def get_data(filters):
    conditions = get_conditions(filters)
    invoices = get_invoices_with_taxes(conditions, filters)

    sections_def = [
        {"code": "3_4A", "name": "B2B Invoices - 3 ,4A"},
        {"code": "4B", "name": "B2BUR Invoices - 4B"},
        {"code": "6C", "name": "Credit/Debit Notes - 6C"},
        {"code": "6C_UR", "name": "Credit/Debit Notes UnRegister - 6C"},
        {"code": "5A_5B", "name": "Import of Goods/ Capital Goods -  5A ,5B"},
        {"code": "4C", "name": "Import of Services - 4C"},
        {"code": "7A_7B", "name": "Nil Rated Invoices - 7A ,7B"},
        {"code": "ITC_REV", "name": "ITC Reversal"},
        {"code": "HSN_13", "name": "HSN Summary of Inward Supplies - 13"},
    ]

    section_buckets = {
        s["code"]: {
            "section_name": s["name"],
            "section_code": s["code"],
            "record_count": 0,
            "taxable_amount": 0.0,
            "cgst_amount": 0.0,
            "sgst_amount": 0.0,
            "igst_amount": 0.0,
            "cess_amount": 0.0,
            "cgst_itc": 0.0,
            "sgst_itc": 0.0,
            "igst_itc": 0.0,
            "cess_itc": 0.0,
        }
        for s in sections_def
    }

    for inv in invoices:
        sec = classify_invoice(inv)
        if sec and sec in section_buckets:
            bucket = section_buckets[sec]
            bucket["record_count"] += 1
            bucket["taxable_amount"] += flt(inv.get("base_net_total", 0.0))
            bucket["cgst_amount"] += flt(inv.get("cgst", 0.0))
            bucket["sgst_amount"] += flt(inv.get("sgst", 0.0))
            bucket["igst_amount"] += flt(inv.get("igst", 0.0))
            bucket["cess_amount"] += flt(inv.get("cess", 0.0))

            # ITC calculation based on eligibility
            is_ineligible = (inv.get("eligibility_for_itc") or "").lower() in ["ineligible", "ineligible as per section 17(5)"]
            if not is_ineligible and sec != "ITC_REV":
                bucket["cgst_itc"] += flt(inv.get("cgst", 0.0))
                bucket["sgst_itc"] += flt(inv.get("sgst", 0.0))
                bucket["igst_itc"] += flt(inv.get("igst", 0.0))
                bucket["cess_itc"] += flt(inv.get("cess", 0.0))
            elif sec == "ITC_REV":
                bucket["cgst_itc"] += flt(inv.get("cgst", 0.0))
                bucket["sgst_itc"] += flt(inv.get("sgst", 0.0))
                bucket["igst_itc"] += flt(inv.get("igst", 0.0))
                bucket["cess_itc"] += flt(inv.get("cess", 0.0))

    # HSN summary item count
    hsn_count = get_hsn_summary_count(conditions, filters)
    section_buckets["HSN_13"]["record_count"] = hsn_count

    # Calculate overall ITC totals
    itc_totals = {
        "cgst": sum(b["cgst_itc"] for k, b in section_buckets.items() if k != "ITC_REV") - section_buckets["ITC_REV"]["cgst_itc"],
        "sgst": sum(b["sgst_itc"] for k, b in section_buckets.items() if k != "ITC_REV") - section_buckets["ITC_REV"]["sgst_itc"],
        "igst": sum(b["igst_itc"] for k, b in section_buckets.items() if k != "ITC_REV") - section_buckets["ITC_REV"]["igst_itc"],
        "cess": sum(b["cess_itc"] for k, b in section_buckets.items() if k != "ITC_REV") - section_buckets["ITC_REV"]["cess_itc"],
    }
    itc_totals["total"] = itc_totals["cgst"] + itc_totals["sgst"] + itc_totals["igst"] + itc_totals["cess"]

    result = [section_buckets[s["code"]] for s in sections_def]

    # Append bottom ITC Summary rows matching UI layout
    result.append({
        "section_name": "Total Input Tax Credit",
        "record_count": None,
        "taxable_amount": None,
        "cgst_amount": None,
        "sgst_amount": None,
        "igst_amount": None,
        "cess_amount": None,
        "cgst_itc": None,
        "sgst_itc": None,
        "igst_itc": None,
        "cess_itc": None,
        "is_header": True
    })
    result.append({
        "section_name": "CGST",
        "record_count": "-",
        "taxable_amount": itc_totals["cgst"],
        "is_itc_row": True
    })
    result.append({
        "section_name": "SGST",
        "record_count": "-",
        "taxable_amount": itc_totals["sgst"],
        "is_itc_row": True
    })
    result.append({
        "section_name": "IGST",
        "record_count": "-",
        "taxable_amount": itc_totals["igst"],
        "is_itc_row": True
    })
    result.append({
        "section_name": "Cess",
        "record_count": "-",
        "taxable_amount": itc_totals["cess"],
        "is_itc_row": True
    })
    result.append({
        "section_name": "Total",
        "record_count": "-",
        "taxable_amount": itc_totals["total"],
        "is_total_row": True
    })

    return result, itc_totals


def classify_invoice(inv):
    is_return = flt(inv.get("is_return", 0)) == 1
    gst_category = (inv.get("gst_category") or "").strip()
    supplier_gstin = (inv.get("supplier_gstin") or "").strip()
    is_registered = bool(supplier_gstin) or gst_category in ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]
    eligibility = (inv.get("eligibility_for_itc") or "").lower()

    if "ineligible" in eligibility:
        return "ITC_REV"

    if gst_category == "Overseas":
        # Check if service import or goods import
        if inv.get("is_service_import"):
            return "4C"
        return "5A_5B"

    if is_return:
        if is_registered:
            return "6C"
        return "6C_UR"

    total_tax = flt(inv.get("cgst", 0)) + flt(inv.get("sgst", 0)) + flt(inv.get("igst", 0)) + flt(inv.get("cess", 0))
    if flt(inv.get("base_net_total", 0)) > 0 and total_tax == 0 and gst_category != "Overseas":
        return "7A_7B"

    if is_registered:
        return "3_4A"
    else:
        return "4B"


def get_conditions(filters):
    conditions = ["pi.docstatus = 1"]
    if filters.get("company"):
        conditions.append("pi.company = %(company)s")
    if filters.get("from_date"):
        conditions.append("pi.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("pi.posting_date <= %(to_date)s")
    return " AND ".join(conditions)


def get_invoices_with_taxes(conditions, filters):
    query = f"""
        SELECT
            pi.name,
            pi.posting_date,
            pi.bill_no,
            pi.bill_date,
            pi.supplier,
            pi.supplier_name,
            pi.supplier_gstin,
            pi.gst_category,
            pi.is_return,
            pi.eligibility_for_itc,
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
                SUM(CASE WHEN account_head LIKE '%%cgst%%' OR account_head LIKE '%%central tax%%' THEN base_tax_amount_after_discount_amount ELSE 0 END) as cgst,
                SUM(CASE WHEN account_head LIKE '%%sgst%%' OR account_head LIKE '%%state tax%%' OR account_head LIKE '%%utgst%%' THEN base_tax_amount_after_discount_amount ELSE 0 END) as sgst,
                SUM(CASE WHEN account_head LIKE '%%igst%%' OR account_head LIKE '%%integrated tax%%' THEN base_tax_amount_after_discount_amount ELSE 0 END) as igst,
                SUM(CASE WHEN account_head LIKE '%%cess%%' THEN base_tax_amount_after_discount_amount ELSE 0 END) as cess
            FROM `tabPurchase Taxes and Charges`
            GROUP BY parent
        ) taxes ON taxes.parent = pi.name
        WHERE {conditions}
    """
    return frappe.db.sql(query, filters, as_dict=True)


def get_hsn_summary_count(conditions, filters):
    query = f"""
        SELECT COUNT(DISTINCT pii.gst_hsn_code)
        FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE {conditions} AND COALESCE(pii.gst_hsn_code, '') != ''
    """
    res = frappe.db.sql(query, filters)
    return res[0][0] if res else 0


def get_report_summary(itc_totals):
    return [
        {"value": itc_totals["cgst"], "indicator": "Blue", "label": _("Total Central ITC"), "datatype": "Currency"},
        {"value": itc_totals["sgst"], "indicator": "Blue", "label": _("Total State/UT ITC"), "datatype": "Currency"},
        {"value": itc_totals["igst"], "indicator": "Blue", "label": _("Total Integrated ITC"), "datatype": "Currency"},
        {"value": itc_totals["cess"], "indicator": "Blue", "label": _("Total Cess ITC"), "datatype": "Currency"},
        {"value": itc_totals["total"], "indicator": "Green", "label": _("Net Total ITC Available"), "datatype": "Currency"}
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
    from_date = filters.get("from_date") or ""
    to_date = filters.get("to_date") or ""

    company_doc = frappe.get_doc("Company", company) if company else None
    company_name = company_doc.name if company_doc else "NexGen Enterprises"

    # Fetch registered address
    address_lines = []
    if company:
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
    ws.title = "GSTR-2"
    ws.views.sheetView[0].showGridLines = True

    # Styling definitions
    title_font = Font(name="Calibri", size=11, bold=True)
    header_fill = PatternFill(start_color="336699", end_color="336699", fill_type="solid")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=10, bold=True)
    normal_font = Font(name="Calibri", size=10)
    thin_border_side = Side(style="thin", color="D3D3D3")
    grid_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    # 1. Company Name
    ws.cell(row=1, column=1, value=company_name).font = title_font

    # 2. Company Address lines
    row_idx = 2
    for line in address_lines:
        ws.cell(row=row_idx, column=1, value=line).font = normal_font
        row_idx += 1

    # 3. Report Name
    ws.cell(row=row_idx, column=1, value="GSTR-2").font = title_font
    row_idx += 1

    # 4. Date Range
    from_str = formatdate(from_date, "dd-mm-yyyy") if from_date else ""
    to_str = formatdate(to_date, "dd-mm-yyyy") if to_date else ""
    date_label = f"From {from_str} To {to_str}"
    ws.cell(row=row_idx, column=1, value=date_label).font = title_font
    row_idx += 1

    # 5. Table Headers
    headers = [
        "Section Name",
        "No. of Records",
        "Total Taxable Amt.",
        "Total Central Tax Amt.",
        "Total State/UT Tax Amt.",
        "Total Integrated Tax Amt.",
        "Total CESS",
        "Total Central ITC Amt.",
        "Total State/UT ITC Amt.",
        "Total Integrated ITC Amt.",
        "Total Cess ITC"
    ]

    header_row = row_idx
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left", vertical="center", wrap_text=True)
        cell.border = grid_border

    row_idx += 1

    # Get data
    columns = get_columns()
    data, itc_totals = get_data(filters)

    # Section rows
    section_rows = [r for r in data if not r.get("is_header") and not r.get("is_itc_row") and not r.get("is_total_row")]

    for row_data in section_rows:
        ws.cell(row=row_idx, column=1, value=row_data.get("section_name")).font = normal_font
        ws.cell(row=row_idx, column=1).border = grid_border

        ws.cell(row=row_idx, column=2, value=row_data.get("record_count", 0)).font = normal_font
        ws.cell(row=row_idx, column=2).alignment = Alignment(horizontal="right")
        ws.cell(row=row_idx, column=2).border = grid_border

        for c_idx, key in enumerate([
            "taxable_amount", "cgst_amount", "sgst_amount", "igst_amount",
            "cess_amount", "cgst_itc", "sgst_itc", "igst_itc", "cess_itc"
        ], start=3):
            val = flt(row_data.get(key, 0.0))
            c = ws.cell(row=row_idx, column=c_idx, value=val)
            c.font = normal_font
            c.number_format = "#,##0.00"
            c.alignment = Alignment(horizontal="right")
            c.border = grid_border

        row_idx += 1

    # Empty rows as shown in template
    for _ in range(6):
        for c in range(1, 12):
            ws.cell(row=row_idx, column=c, value=0 if c > 1 else "").border = grid_border
        row_idx += 1

    # Total Input Tax Credit Section
    ws.cell(row=row_idx, column=1, value="Total Input Tax Credit").font = bold_font
    for c in range(2, 12):
        ws.cell(row=row_idx, column=c, value=0).border = grid_border
    row_idx += 1

    itc_labels = [
        ("CGST", itc_totals["cgst"]),
        ("SGST", itc_totals["sgst"]),
        ("IGST", itc_totals["igst"]),
        ("Cess", itc_totals["cess"]),
        ("Total", itc_totals["total"]),
    ]

    for label, val in itc_labels:
        ws.cell(row=row_idx, column=1, value=label).font = bold_font if label == "Total" else normal_font
        ws.cell(row=row_idx, column=1).border = grid_border
        ws.cell(row=row_idx, column=2, value="-").alignment = Alignment(horizontal="center")
        ws.cell(row=row_idx, column=2).border = grid_border

        for c in range(3, 12):
            cell = ws.cell(row=row_idx, column=c, value=flt(val) if c == 3 else 0.0)
            cell.font = bold_font if label == "Total" else normal_font
            cell.number_format = "#,##0.00"
            cell.alignment = Alignment(horizontal="right")
            cell.border = grid_border
        row_idx += 1

    # Adjust column widths
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 14
    for col_char in ["C", "D", "E", "F", "G", "H", "I", "J", "K"]:
        ws.column_dimensions[col_char].width = 22

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.response["filename"] = f"GSTR_2B_Summary_{company_name.replace(' ', '_')}_{from_str}_to_{to_str}.xlsx"
    frappe.response["filecontent"] = output.getvalue()
    frappe.response["type"] = "binary"
