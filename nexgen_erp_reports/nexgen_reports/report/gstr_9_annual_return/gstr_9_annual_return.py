import json
import io
import frappe
from frappe import _
from frappe.utils import flt, formatdate

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data, None, None, None


def get_columns():
    return [
        {
            "label": _("Section Name"),
            "fieldname": "section_name",
            "fieldtype": "Data",
            "width": 380
        },
        {
            "label": _("Taxable Value"),
            "fieldname": "taxable_value",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Central Tax Amt."),
            "fieldname": "cgst_amount",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("State/UT Tax Amt."),
            "fieldname": "sgst_amount",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": _("Integrated Tax Amt."),
            "fieldname": "igst_amount",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Cess Amt."),
            "fieldname": "cess_amount",
            "fieldtype": "Currency",
            "width": 130
        }
    ]


def get_data(filters):
    outward_data = get_outward_data(filters)
    inward_data = get_inward_data(filters)
    hsn_outward = get_hsn_totals(filters, "Sales Invoice Item")
    hsn_inward = get_hsn_totals(filters, "Purchase Invoice Item")

    rows = []

    # Helper function to create formatted section row
    def add_row(name, data_dict=None, section_code=None, is_header=False, is_subtotal=False, is_grandtotal=False, indent=0):
        if not data_dict:
            data_dict = {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "cess": 0.0}

        prefix = "    " * indent
        display_name = prefix + name

        rows.append({
            "section_name": display_name,
            "raw_name": name,
            "section_code": section_code,
            "taxable_value": flt(data_dict.get("taxable", 0.0)),
            "cgst_amount": flt(data_dict.get("cgst", 0.0)),
            "sgst_amount": flt(data_dict.get("sgst", 0.0)),
            "igst_amount": flt(data_dict.get("igst", 0.0)),
            "cess_amount": flt(data_dict.get("cess", 0.0)),
            "is_header": is_header,
            "is_subtotal": is_subtotal,
            "is_grandtotal": is_grandtotal,
        })

    def add_blank():
        rows.append({
            "section_name": "",
            "taxable_value": 0.0,
            "cgst_amount": 0.0,
            "sgst_amount": 0.0,
            "igst_amount": 0.0,
            "cess_amount": 0.0,
            "is_blank": True
        })

    # ----------------------------------------------------
    # Table 4: Details of Advances, inward and outward supplies on which tax is payable
    # ----------------------------------------------------
    add_row("4. Details of Advances,inward and outward supplies on which tax is payable", is_header=True)
    add_row("A. Supplies made to Unregistered Persons (B2C)", outward_data["4A"], section_code="4A")
    add_row("B. Supplies made to Registered persons (B2B)", outward_data["4B"], section_code="4B")
    add_row("C. Zero Rated Supply (Export) on payment of tax (except supplies to SEZs)", outward_data["4C"], section_code="4C")
    add_row("D. Supplies to SEZ on payment of tax", outward_data["4D"], section_code="4D")
    add_row("E. Deemed Exports", outward_data["4E"], section_code="4E")
    add_row("F. Advance (Received) on which tax has been paid but invoice has not been issued", outward_data["4F"], section_code="4F")
    add_row("G. Inward supplies on which tax is to be paid on reverse charge basis", outward_data["4G"], section_code="4G")
    add_row("G1. Supplies on which e-commerce operator is required to pay tax as per section 9(5) (including amendments, if any)[E-commerce operator to report] ", outward_data["4G1"], section_code="4G1")

    # 4H: Sub Total (A to G1)
    tot_4H = sum_dicts([outward_data["4A"], outward_data["4B"], outward_data["4C"], outward_data["4D"], outward_data["4E"], outward_data["4F"], outward_data["4G"], outward_data["4G1"]])
    add_row("H. Sub Total (A to G1 above)", tot_4H, is_subtotal=True)

    add_row("I. Credit notes issued in respect of transactions specified in (B) to (E) above (-)", outward_data["4I"], section_code="4I")
    add_row("J. Debit notes issued in respect of transactions specified in (B) to (E) above (+)", outward_data["4J"], section_code="4J")
    add_row("K. Supplies /Tax declared through amendments(+)", outward_data["4K"], section_code="4K")
    add_row("L. Supplies /Tax declared through amendments(-)", outward_data["4L"], section_code="4L")

    # 4M: Sub Total (I to L)
    tot_4M = sum_dicts([outward_data["4I"], outward_data["4J"], outward_data["4K"], outward_data["4L"]])
    add_row("M. Sub Total (I to L above)", tot_4M, is_subtotal=True)

    # 4N: Supplies and advances on which tax is to be paid (H+M)
    tot_4N = sum_dicts([tot_4H, tot_4M])
    add_row("  N. Supplies and advances on which tax is to be paid (H+M) above", tot_4N, is_grandtotal=True)

    add_blank()

    # ----------------------------------------------------
    # Table 5: Details of Outward supplies on which tax is not payable
    # ----------------------------------------------------
    add_row("5. Details of Outward supplies on which tax is not payable", is_header=True)
    add_row("A. Zero Rated Supply (Export) without payment of tax", outward_data["5A"], section_code="5A")
    add_row("B. Supplies to SEZs without payment of tax", outward_data["5B"], section_code="5B")
    add_row("C. Supplies on which tax is to be paid by the recipient on reverse charge basis", outward_data["5C"], section_code="5C")
    add_row("C1. Supplies on which tax is to be paid by e-commerce operators as per section 9(5)[Supplier to report] ", outward_data["5C1"], section_code="5C1")
    add_row("D. Exempted", outward_data["5D"], section_code="5D")
    add_row("E. Nil Rated", outward_data["5E"], section_code="5E")
    add_row("F. Non-GST Supply", outward_data["5F"], section_code="5F")

    # 5G: Sub-Total (A to F)
    tot_5G = sum_dicts([outward_data["5A"], outward_data["5B"], outward_data["5C"], outward_data["5C1"], outward_data["5D"], outward_data["5E"], outward_data["5F"]])
    add_row("G. Sub-Total (A to F above)", tot_5G, is_subtotal=True)

    add_row("H. Credit Notes Issued in respect of transaction in (A to F above (-) )", outward_data["5H"], section_code="5H")
    add_row("I. Debit Notes Issued in respect of transaction in (A to F above (+) )", outward_data["5I"], section_code="5I")
    add_row("J. Supplies declared through Amendments (+)", outward_data["5J"], section_code="5J")
    add_row("K. Supplies declared through Amendments (-)", outward_data["5K"], section_code="5K")

    # 5L: Sub-Total (H to K)
    tot_5L = sum_dicts([outward_data["5H"], outward_data["5I"], outward_data["5J"], outward_data["5K"]])
    add_row("L. Sub-Total (H to K above)", tot_5L, is_subtotal=True)

    # 5M: Turnover on which tax is not to be paid (G + L)
    tot_5M = sum_dicts([tot_5G, tot_5L])
    add_row("M. Turnover on which tax is not to be paid (G + L above)", tot_5M, is_subtotal=True)

    # 5N: Total turnover (Including advances) ( 4N + 5M - 4G )
    tot_5N = {
        "taxable": tot_4N["taxable"] + tot_5M["taxable"] - outward_data["4G"]["taxable"],
        "cgst": tot_4N["cgst"] + tot_5M["cgst"] - outward_data["4G"]["cgst"],
        "sgst": tot_4N["sgst"] + tot_5M["sgst"] - outward_data["4G"]["sgst"],
        "igst": tot_4N["igst"] + tot_5M["igst"] - outward_data["4G"]["igst"],
        "cess": tot_4N["cess"] + tot_5M["cess"] - outward_data["4G"]["cess"],
    }
    add_row("  N. Total turnover (Including advances) ( 4N + 5M - 4G  above )", tot_5N, is_grandtotal=True)

    add_blank()

    # ----------------------------------------------------
    # Table 6: Details of ITC availed
    # ----------------------------------------------------
    add_row("6. Details of ITC availed", is_header=True)
    add_row("A. Total amount of input tax credit availed through FORM GSTR-3B(Sum total of Table 4A of GST3B) ", inward_data["6A"])
    add_row("B. Inward supplies received (other than imports and inward supplies liable to reverse charge but includes services received from SEZs)", inward_data["6B"], section_code="6B")
    add_row("Input Goods", inward_data["6B_goods"], indent=1)
    add_row("Capital Goods", inward_data["6B_capital"], indent=1)
    add_row("Input Services", inward_data["6B_services"], indent=1)

    add_row("C. Inward supplies received from unregistered persons liable to reverse charge (other than B above) on which tax is paid & ITC availed", inward_data["6C"], section_code="6C")
    add_row("Input Goods", inward_data["6C_goods"], indent=1)
    add_row("Capital Goods", inward_data["6C_capital"], indent=1)
    add_row("Input Services", inward_data["6C_services"], indent=1)

    add_row("D. Inward supplies received from registered persons liable to reverse charge (other than B above) on which tax is paid and ITC availed", inward_data["6D"], section_code="6D")
    add_row("Input Goods", inward_data["6D_goods"], indent=1)
    add_row("Capital Goods", inward_data["6D_capital"], indent=1)
    add_row("Input Services", inward_data["6D_services"], indent=1)

    add_row("E. Import of goods (including supplies from SEZs)", inward_data["6E"], section_code="6E")
    add_row("Input Goods", inward_data["6E_goods"], indent=1)
    add_row("Capital Goods", inward_data["6E_capital"], indent=1)

    add_row("F. Import of services (excluding inward supplies from SEZs)", inward_data["6F"], section_code="6F")
    add_row("G. Input Tax Credit received from ISD", inward_data["6G"])
    add_row("H. Amount of ITC reclaimed (other than B Above) under the provisions of the Act", inward_data["6H"])

    # 6I: Sub-Total (B to H)
    tot_6I = sum_dicts([inward_data["6B"], inward_data["6C"], inward_data["6D"], inward_data["6E"], inward_data["6F"], inward_data["6G"], inward_data["6H"]])
    add_row("I. Sub-Total (B to H above)", tot_6I, is_subtotal=True)

    # 6J: Difference (I - A)
    diff_6J = diff_dicts(tot_6I, inward_data["6A"])
    add_row("J. Difference (I-A above)", diff_6J)

    add_row("K. Transition credit through TRAN-I", inward_data["6K"])
    add_row("L. Transition credit through TRAN-II", inward_data["6L"])
    add_row("M. Any other ITC availed but not specified above", inward_data["6M"])

    tot_6N = sum_dicts([inward_data["6K"], inward_data["6L"], inward_data["6M"]])
    add_row("N. Sub-Total (K to M above)", tot_6N, is_subtotal=True)

    tot_6O = sum_dicts([tot_6I, tot_6N])
    add_row("  O. Total ITC availed (I+N above)", tot_6O, is_grandtotal=True)

    add_blank()

    # ----------------------------------------------------
    # Table 7: Details of ITC Reversal and Ineligible ITC
    # ----------------------------------------------------
    add_row("7. Details of ITC Reversal and Ineligible ITC ", is_header=True)
    add_row("A. As per Rule 37", inward_data["7A"])
    add_row("B. As per Rule 39", inward_data["7B"])
    add_row("C. As per Rule 42", inward_data["7C"])
    add_row("D. As per Rule 43", inward_data["7D"])
    add_row("E. As per Section 17(5)", inward_data["7E"], section_code="7E")
    add_row("F. Reversal Of TRAN-I credit", inward_data["7F"])
    add_row("G. Reversal Of TRAN-II credit", inward_data["7G"])
    add_row("H. Other reversals", inward_data["7H"])

    tot_7I = sum_dicts([inward_data["7A"], inward_data["7B"], inward_data["7C"], inward_data["7D"], inward_data["7E"], inward_data["7F"], inward_data["7G"], inward_data["7H"]])
    add_row("I. Total ITC Reversed (A to H above)", tot_7I, is_subtotal=True)

    net_7J = diff_dicts(tot_6O, tot_7I)
    add_row("J. Net ITC Available for Utilization (6O-7I)", net_7J, is_grandtotal=True)

    add_blank()

    # ----------------------------------------------------
    # Table 8: Other ITC
    # ----------------------------------------------------
    add_row("8. Other ITC ", is_header=True)
    add_row("A. ITC as per GSTR-2B [Table 3(I) thereof]", inward_data["8A"])
    tot_6B_6H = sum_dicts([inward_data["6B"], inward_data["6H"]])
    add_row("B. ITC as per sum total of 6(B) and 6(H) above", tot_6B_6H)
    add_row("C. ITC on inward supplies received during the financial year but availed in the next financial year upto specified period", inward_data["8C"])
    diff_8D = diff_dicts(inward_data["8A"], sum_dicts([tot_6B_6H, inward_data["8C"]]))
    add_row("D. Difference [A-(B+C)]", diff_8D)
    add_row("E. ITC available but not availed", inward_data["8E"])
    add_row("F. ITC available but ineligible", inward_data["8F"])
    add_row("G. IGST paid on import of goods (Including supplies from SEZ)", inward_data["8G"])
    add_row("H. IGST credit availed on import of goods( as per 6(E) above)", inward_data["8H"])
    diff_8I = diff_dicts(inward_data["8G"], inward_data["8H"])
    add_row("I. Difference (G-H)", diff_8I)
    add_row("J. ITC available but not availed on import of goods(Equal to I)", diff_8I)
    tot_8K = sum_dicts([inward_data["8E"], inward_data["8F"], diff_8I])
    add_row("  K. Total ITC to be lapsed in current financial year (E+F+J)", tot_8K, is_grandtotal=True)

    add_blank()

    # ----------------------------------------------------
    # Table 10-13: Amendments & Previous FY
    # ----------------------------------------------------
    add_row("10.  Supplies / tax declared through Amendments (+) (net of debit notes)", outward_data["T10"])
    add_row("11.  Supplies / tax reduced through Amendments (-) (net of credit notes)", outward_data["T11"])
    add_row("12. Reversal of ITC availed during previous financial year", inward_data["T12"])
    add_row("13. ITC availed for the previous financial year", inward_data["T13"])

    tot_turnover_final = {
        "taxable": tot_5N["taxable"] + outward_data["T10"]["taxable"] - outward_data["T11"]["taxable"],
        "cgst": tot_5N["cgst"] + outward_data["T10"]["cgst"] - outward_data["T11"]["cgst"],
        "sgst": tot_5N["sgst"] + outward_data["T10"]["sgst"] - outward_data["T11"]["sgst"],
        "igst": tot_5N["igst"] + outward_data["T10"]["igst"] - outward_data["T11"]["igst"],
        "cess": tot_5N["cess"] + outward_data["T10"]["cess"] - outward_data["T11"]["cess"],
    }
    add_row("  Total turnover (5N +10-11)", tot_turnover_final, is_grandtotal=True)

    add_blank()

    # ----------------------------------------------------
    # Table 16: Composition & Deemed
    # ----------------------------------------------------
    add_row("16. Information on supplies received from composition taxpayers, deemed supply under section 143 and goods sent on approval basis ", is_header=True)
    add_row("A. Supplies received from Composition taxpayers", inward_data["16A"], section_code="16A")
    add_row("B. Deemed supply under section 143", inward_data["16B"])
    add_row("C. Goods sent on approval basis but not returned", inward_data["16C"])

    add_blank()

    # ----------------------------------------------------
    # Table 17 & 18: HSN Summaries
    # ----------------------------------------------------
    add_row("17. HSN-Wise Summary of Outward Supplies", hsn_outward, section_code="17", is_grandtotal=True)
    add_row("18. HSN-Wise Summary of Inward Supplies", hsn_inward, section_code="18", is_grandtotal=True)

    return rows


def sum_dicts(dict_list):
    res = {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "cess": 0.0}
    for d in dict_list:
        for k in res:
            res[k] += flt(d.get(k, 0.0))
    return res


def diff_dicts(d1, d2):
    return {
        "taxable": flt(d1.get("taxable", 0.0)) - flt(d2.get("taxable", 0.0)),
        "cgst": flt(d1.get("cgst", 0.0)) - flt(d2.get("cgst", 0.0)),
        "sgst": flt(d1.get("sgst", 0.0)) - flt(d2.get("sgst", 0.0)),
        "igst": flt(d1.get("igst", 0.0)) - flt(d2.get("igst", 0.0)),
        "cess": flt(d1.get("cess", 0.0)) - flt(d2.get("cess", 0.0)),
    }


def get_empty_bucket():
    return {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "cess": 0.0}


def get_outward_data(filters):
    conditions = ["si.docstatus = 1"]
    if filters.get("company"):
        conditions.append("si.company = %(company)s")
    if filters.get("from_date"):
        conditions.append("si.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("si.posting_date <= %(to_date)s")

    cond_str = " AND ".join(conditions)

    # Dynamic schema handling
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
            si.is_return,
            si.base_net_total,
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
    """
    invoices = frappe.db.sql(query, filters, as_dict=True)

    buckets = {
        k: get_empty_bucket() for k in [
            "4A", "4B", "4C", "4D", "4E", "4F", "4G", "4G1", "4I", "4J", "4K", "4L",
            "5A", "5B", "5C", "5C1", "5D", "5E", "5F", "5H", "5I", "5J", "5K", "T10", "T11"
        ]
    }

    for inv in invoices:
        is_return = flt(inv.get("is_return", 0)) == 1
        gst_category = (inv.get("gst_category") or "").strip()
        customer_gstin = (inv.get("customer_gstin") or "").strip()
        is_registered = bool(customer_gstin) or gst_category in ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]
        reverse_charge = (inv.get("reverse_charge") or "N").upper() in ["Y", "YES"]

        taxable = flt(inv.get("base_net_total", 0.0))
        cgst = flt(inv.get("cgst", 0.0))
        sgst = flt(inv.get("sgst", 0.0))
        igst = flt(inv.get("igst", 0.0))
        cess = flt(inv.get("cess", 0.0))
        total_tax = cgst + sgst + igst + cess

        if is_return:
            if total_tax > 0:
                target = "4I"
            else:
                target = "5H"
        else:
            if total_tax > 0:
                if gst_category == "Overseas":
                    target = "4C"
                elif gst_category == "SEZ":
                    target = "4D"
                elif gst_category == "Deemed Export":
                    target = "4E"
                elif is_registered:
                    target = "4B"
                else:
                    target = "4A"
            else:
                # Tax is zero / non payable
                if gst_category == "Overseas":
                    target = "5A"
                elif gst_category == "SEZ":
                    target = "5B"
                elif reverse_charge:
                    target = "5C"
                elif gst_category == "Exempt":
                    target = "5D"
                elif gst_category == "Nil Rated":
                    target = "5E"
                else:
                    target = "5A" if gst_category == "Overseas" else "5D"

        b = buckets[target]
        b["taxable"] += taxable
        b["cgst"] += cgst
        b["sgst"] += sgst
        b["igst"] += igst
        b["cess"] += cess

    return buckets


def get_inward_data(filters):
    conditions = ["pi.docstatus = 1"]
    if filters.get("company"):
        conditions.append("pi.company = %(company)s")
    if filters.get("from_date"):
        conditions.append("pi.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("pi.posting_date <= %(to_date)s")

    cond_str = " AND ".join(conditions)

    has_gst_category = frappe.db.has_column("Purchase Invoice", "gst_category")
    has_supplier_gstin = frappe.db.has_column("Purchase Invoice", "supplier_gstin")
    has_eligibility = frappe.db.has_column("Purchase Invoice", "eligibility_for_itc")
    has_reverse_charge = frappe.db.has_column("Purchase Invoice", "reverse_charge")

    gst_cat_col = "pi.gst_category" if has_gst_category else "'' as gst_category"
    gstin_col = "pi.supplier_gstin" if has_supplier_gstin else "'' as supplier_gstin"
    elig_col = "pi.eligibility_for_itc" if has_eligibility else "'' as eligibility_for_itc"
    rcm_col = "pi.reverse_charge" if has_reverse_charge else "'N' as reverse_charge"

    has_base_tax = frappe.db.has_column("Purchase Taxes and Charges", "base_tax_amount_after_discount_amount")
    tax_col = "base_tax_amount_after_discount_amount" if has_base_tax else "tax_amount"

    query = f"""
        SELECT
            pi.name,
            pi.is_return,
            pi.base_net_total,
            {gst_cat_col},
            {gstin_col},
            {elig_col},
            {rcm_col},
            COALESCE(taxes.cgst, 0) as cgst,
            COALESCE(taxes.sgst, 0) as sgst,
            COALESCE(taxes.igst, 0) as igst,
            COALESCE(taxes.cess, 0) as cess
        FROM `tabPurchase Invoice` pi
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
    """
    invoices = frappe.db.sql(query, filters, as_dict=True)

    buckets = {
        k: get_empty_bucket() for k in [
            "6A", "6B", "6B_goods", "6B_capital", "6B_services",
            "6C", "6C_goods", "6C_capital", "6C_services",
            "6D", "6D_goods", "6D_capital", "6D_services",
            "6E", "6E_goods", "6E_capital", "6F", "6G", "6H", "6K", "6L", "6M",
            "7A", "7B", "7C", "7D", "7E", "7F", "7G", "7H",
            "8A", "8C", "8E", "8F", "8G", "8H",
            "T12", "T13", "16A", "16B", "16C"
        ]
    }

    for inv in invoices:
        gst_category = (inv.get("gst_category") or "").strip()
        supplier_gstin = (inv.get("supplier_gstin") or "").strip()
        is_registered = bool(supplier_gstin) or gst_category in ["Registered Regular", "Registered Composition", "SEZ", "Deemed Export"]
        reverse_charge = (inv.get("reverse_charge") or "N").upper() in ["Y", "YES"]
        eligibility = (inv.get("eligibility_for_itc") or "").lower()

        taxable = flt(inv.get("base_net_total", 0.0))
        cgst = flt(inv.get("cgst", 0.0))
        sgst = flt(inv.get("sgst", 0.0))
        igst = flt(inv.get("igst", 0.0))
        cess = flt(inv.get("cess", 0.0))

        if "ineligible" in eligibility:
            target = "7E"
        elif gst_category == "Overseas":
            target = "6E"
        elif reverse_charge:
            target = "6D" if is_registered else "6C"
        elif gst_category == "Composition":
            target = "16A"
        else:
            target = "6B"

        b = buckets[target]
        b["taxable"] += taxable
        b["cgst"] += cgst
        b["sgst"] += sgst
        b["igst"] += igst
        b["cess"] += cess

    return buckets


def get_hsn_totals(filters, doctype):
    conditions = ["parent_doc.docstatus = 1"]
    if filters.get("company"):
        conditions.append("parent_doc.company = %(company)s")
    if filters.get("from_date"):
        conditions.append("parent_doc.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("parent_doc.posting_date <= %(to_date)s")

    parent_tab = "tabSales Invoice" if doctype == "Sales Invoice Item" else "tabPurchase Invoice"
    cond_str = " AND ".join(conditions)

    # Dynamic column check
    hsn_col = None
    if frappe.db.has_column(doctype, "gst_hsn_code"):
        hsn_col = "gst_hsn_code"
    elif frappe.db.has_column(doctype, "hsn_sac"):
        hsn_col = "hsn_sac"

    query = f"""
        SELECT
            SUM(child.base_net_amount) as taxable,
            SUM(COALESCE(child.cgst_amount, 0)) as cgst,
            SUM(COALESCE(child.sgst_amount, 0)) as sgst,
            SUM(COALESCE(child.igst_amount, 0)) as igst,
            SUM(COALESCE(child.cess_amount, 0)) as cess
        FROM `tab{doctype}` child
        JOIN `{parent_tab}` parent_doc ON parent_doc.name = child.parent
        WHERE {cond_str}
    """
    try:
        res = frappe.db.sql(query, filters, as_dict=True)
        if res and res[0].get("taxable") is not None:
            return {
                "taxable": flt(res[0].get("taxable", 0.0)),
                "cgst": flt(res[0].get("cgst", 0.0)),
                "sgst": flt(res[0].get("sgst", 0.0)),
                "igst": flt(res[0].get("igst", 0.0)),
                "cess": flt(res[0].get("cess", 0.0)),
            }
    except Exception:
        pass

    return get_empty_bucket()


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

    # Fetch address
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
    ws.title = "GSTR-9"
    ws.views.sheetView[0].showGridLines = True

    # Styles
    title_font = Font(name="Calibri", size=11, bold=True)
    header_fill = PatternFill(start_color="336699", end_color="336699", fill_type="solid")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    section_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
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

    # 3. Report Name
    ws.cell(row=row_idx, column=1, value="GSTR-9 (Annual Return)").font = title_font
    row_idx += 1

    # 4. Date Range
    from_str = formatdate(from_date, "dd-mm-yyyy") if from_date else ""
    to_str = formatdate(to_date, "dd-mm-yyyy") if to_date else ""
    date_label = f"From {from_str} to {to_str}"
    ws.cell(row=row_idx, column=1, value=date_label).font = title_font
    row_idx += 1

    # 5. Headers
    headers = [
        "Section Name",
        "Taxable Value",
        "Central Tax Amt.",
        "State/UT Tax Amt.",
        "Integrated Tax Amt.",
        "Cess Amt."
    ]

    header_row = row_idx
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left", vertical="center")
        cell.border = grid_border

    row_idx += 1

    # Get data
    data = get_data(filters)

    for row_data in data:
        is_header = row_data.get("is_header")
        is_subtotal = row_data.get("is_subtotal")
        is_grandtotal = row_data.get("is_grandtotal")
        is_blank = row_data.get("is_blank")

        current_font = bold_font if (is_header or is_subtotal or is_grandtotal) else normal_font

        c1 = ws.cell(row=row_idx, column=1, value=row_data.get("section_name", ""))
        c1.font = current_font
        c1.border = grid_border
        if is_header:
            c1.fill = section_fill

        for c_idx, key in enumerate(["taxable_value", "cgst_amount", "sgst_amount", "igst_amount", "cess_amount"], start=2):
            val = flt(row_data.get(key, 0.0))
            c = ws.cell(row=row_idx, column=c_idx, value=val)
            c.font = current_font
            c.number_format = "#,##0.00"
            c.alignment = Alignment(horizontal="right")
            c.border = grid_border
            if is_header:
                c.fill = section_fill

        row_idx += 1

    # Column Widths
    ws.column_dimensions["A"].width = 75
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 20
    ws.column_dimensions["F"].width = 16

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.response["filename"] = f"GSTR_9_Annual_Return_{company_name.replace(' ', '_')}_{from_str}_to_{to_str}.xlsx"
    frappe.response["filecontent"] = output.getvalue()
    frappe.response["type"] = "binary"
