# Copyright (c) 2026, NexGen ERP Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today


class ExpenseInvoice(Document):
    def validate(self):
        self.calculate_taxes_and_totals()

    def calculate_taxes_and_totals(self):
        gst_rate = flt(self.gst_rate)
        tax_type = self.tax_type or "In-State (CGST + SGST)"

        total_net = 0.0
        total_cgst = 0.0
        total_sgst = 0.0
        total_igst = 0.0

        for item in self.get("items", []):
            amt = flt(item.amount)
            item_gst = flt(item.gst_rate) if item.gst_rate is not None else gst_rate
            item.gst_rate = item_gst

            if tax_type == "In-State (CGST + SGST)":
                half_rate = item_gst / 2.0
                item.cgst = flt(amt * (half_rate / 100.0), 2)
                item.sgst = flt(amt * (half_rate / 100.0), 2)
                item.igst = 0.0
            elif tax_type == "Out-of-State (IGST)":
                item.cgst = 0.0
                item.sgst = 0.0
                item.igst = flt(amt * (item_gst / 100.0), 2)
            else:
                item.cgst = 0.0
                item.sgst = 0.0
                item.igst = 0.0

            item.total_amount = amt + item.cgst + item.sgst + item.igst
            total_net += amt
            total_cgst += item.cgst
            total_sgst += item.sgst
            total_igst += item.igst

        self.net_total = flt(total_net, 2)
        self.cgst_amount = flt(total_cgst, 2)
        self.sgst_amount = flt(total_sgst, 2)
        self.igst_amount = flt(total_igst, 2)
        self.total_tax = flt(self.cgst_amount + self.sgst_amount + self.igst_amount, 2)
        self.grand_total = flt(self.net_total + self.total_tax, 2)

        # TDS calculation
        if self.apply_tds and flt(self.tds_rate) > 0:
            self.tds_amount = flt(self.net_total * flt(self.tds_rate) / 100.0, 2)
        else:
            self.tds_amount = 0.0

        self.net_payable = flt(self.grand_total - flt(self.tds_amount), 2)

    def on_submit(self):
        # Create and submit the background Purchase Invoice for full accounting and GST compliance
        if not self.purchase_invoice:
            pi_name = self.create_and_submit_purchase_invoice()
            self.db_set("purchase_invoice", pi_name)
            self.db_set("status", "Submitted")

    def on_cancel(self):
        if self.purchase_invoice and frappe.db.exists("Purchase Invoice", self.purchase_invoice):
            pi = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
            if pi.docstatus == 1:
                pi.cancel()
        self.db_set("status", "Cancelled")

    def create_and_submit_purchase_invoice(self):
        pi = frappe.new_doc("Purchase Invoice")
        pi.company = self.company
        pi.supplier = self.supplier
        pi.bill_no = self.bill_no
        pi.bill_date = self.bill_date
        pi.posting_date = self.posting_date
        pi.due_date = self.due_date or self.posting_date

        # Mark as expense invoice so it can be filtered out of regular purchase lists
        if frappe.db.has_column("Purchase Invoice", "is_expense_invoice"):
            pi.is_expense_invoice = 1
        if frappe.db.has_column("Purchase Invoice", "expense_invoice"):
            pi.expense_invoice = self.name

        pi.remarks = f"Created from Expense Invoice {self.name}: {self.remarks or ''}"

        cost_center = frappe.db.get_value("Company", self.company, "cost_center")
        if not cost_center:
            cost_center = frappe.db.get_value("Cost Center", {"company": self.company, "is_group": 0}, "name")

        has_sac = frappe.db.has_column("Purchase Invoice Item", "gst_hsn_code")

        for item in self.items:
            item_data = {
                "item_name": item.description or item.expense_account,
                "description": item.description,
                "expense_account": item.expense_account,
                "qty": 1,
                "rate": flt(item.amount),
                "amount": flt(item.amount),
                "cost_center": cost_center
            }
            if has_sac and item.sac_code:
                item_data["gst_hsn_code"] = item.sac_code

            pi.append("items", item_data)

        # Set Purchase Taxes and Charges Template if available
        abbr = frappe.db.get_value("Company", self.company, "abbr")
        if self.tax_type == "In-State (CGST + SGST)":
            template = f"Input GST In-state - {abbr}"
        elif self.tax_type == "Out-of-State (IGST)":
            template = f"Input GST Out-state - {abbr}"
        else:
            template = None

        if template and frappe.db.exists("Purchase Taxes and Charges Template", template):
            pi.taxes_and_charges = template

        # Tax rows (strictly non-RCM Input tax accounts)
        cgst_acc = get_tax_account(self.company, "CGST")
        sgst_acc = get_tax_account(self.company, "SGST")
        igst_acc = get_tax_account(self.company, "IGST")

        half_rate = flt(self.gst_rate) / 2.0
        full_rate = flt(self.gst_rate)

        if self.cgst_amount > 0 and cgst_acc:
            pi.append("taxes", {
                "charge_type": "Actual",
                "account_head": cgst_acc,
                "rate": half_rate,
                "tax_amount": self.cgst_amount,
                "description": f"Input Tax CGST ({half_rate}%)"
            })
        if self.sgst_amount > 0 and sgst_acc:
            pi.append("taxes", {
                "charge_type": "Actual",
                "account_head": sgst_acc,
                "rate": half_rate,
                "tax_amount": self.sgst_amount,
                "description": f"Input Tax SGST ({half_rate}%)"
            })
        if self.igst_amount > 0 and igst_acc:
            pi.append("taxes", {
                "charge_type": "Actual",
                "account_head": igst_acc,
                "rate": full_rate,
                "tax_amount": self.igst_amount,
                "description": f"Input Tax IGST ({full_rate}%)"
            })

        # TDS
        if self.apply_tds and self.tax_withholding_category:
            if hasattr(pi, "apply_tds"):
                pi.apply_tds = 1
                pi.tax_withholding_category = self.tax_withholding_category

        pi.flags.ignore_permissions = True
        pi.save()
        pi.submit()

        return pi.name


def get_tax_account(company, tax_type):
    """Finds normal (non-RCM) Input Tax account for CGST, SGST, or IGST in Company"""
    # Exclude RCM, Refund, and Output accounts to avoid Reverse Charge validation errors
    accounts = frappe.db.sql("""
        SELECT name
        FROM `tabAccount`
        WHERE company = %s
          AND is_group = 0
          AND account_name LIKE %s
          AND account_name NOT LIKE '%%RCM%%'
          AND account_name NOT LIKE '%%Refund%%'
          AND account_name NOT LIKE '%%Output%%'
        ORDER BY LENGTH(account_name) ASC, name ASC
    """, (company, f"%Input%{tax_type}%"), as_dict=True)

    if accounts:
        return accounts[0].name

    fallback = frappe.db.sql("""
        SELECT name
        FROM `tabAccount`
        WHERE company = %s
          AND is_group = 0
          AND account_type = 'Tax'
          AND account_name LIKE %s
          AND account_name NOT LIKE '%%RCM%%'
          AND account_name NOT LIKE '%%Refund%%'
          AND account_name NOT LIKE '%%Output%%'
        ORDER BY LENGTH(account_name) ASC, name ASC
    """, (company, f"%{tax_type}%"), as_dict=True)

    if fallback:
        return fallback[0].name

    return None


@frappe.whitelist()
def sync_past_expense_invoices():
    """
    Scans past submitted Purchase Invoices that represent expenses/services
    and creates corresponding Expense Invoice records.
    """
    # Ensure custom fields exist first
    try:
        from nexgen_erp_reports.setup import setup_custom_fields
        setup_custom_fields()
    except Exception:
        pass

    has_exp_col = frappe.db.has_column("Purchase Invoice", "expense_invoice")
    exp_condition = "AND (pi.expense_invoice IS NULL OR pi.expense_invoice = '')" if has_exp_col else ""

    invoices = frappe.db.sql(f"""
        SELECT
            pi.name,
            pi.company,
            pi.supplier,
            pi.bill_no,
            pi.bill_date,
            pi.posting_date,
            pi.due_date,
            pi.net_total,
            pi.grand_total,
            pi.outstanding_amount,
            pi.status
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1
          {exp_condition}
          AND EXISTS (
              SELECT 1 FROM `tabPurchase Invoice Item` pii
              JOIN `tabAccount` acc ON acc.name = pii.expense_account
              WHERE pii.parent = pi.name
                AND acc.root_type = 'Expense'
          )
        ORDER BY pi.posting_date DESC
    """, as_dict=True)

    synced_count = 0
    valid_statuses = ["Draft", "Submitted", "Paid", "Partly Paid", "Unpaid", "Overdue", "Return", "Cancelled"]

    for inv in invoices:
        try:
            # Check if already synced
            if frappe.db.exists("Expense Invoice", {"purchase_invoice": inv.name}):
                continue

            exp = frappe.new_doc("Expense Invoice")
            exp.company = inv.company
            exp.supplier = inv.supplier
            exp.bill_no = inv.bill_no or inv.name
            exp.bill_date = inv.bill_date or inv.posting_date
            exp.posting_date = inv.posting_date
            exp.due_date = inv.due_date
            exp.purchase_invoice = inv.name
            exp.status = inv.status if inv.status in valid_statuses else "Submitted"
            exp.outstanding_amount = inv.outstanding_amount

            # Items
            items = frappe.db.sql("""
                SELECT pii.expense_account, pii.description, pii.amount
                FROM `tabPurchase Invoice Item` pii
                WHERE pii.parent = %s
            """, (inv.name,), as_dict=True)

            for it in items:
                exp.append("items", {
                    "expense_account": it.expense_account,
                    "description": it.description or it.expense_account,
                    "amount": flt(it.amount),
                    "total_amount": flt(it.amount)
                })

            exp.calculate_taxes_and_totals()
            exp.docstatus = 1
            exp.flags.ignore_permissions = True
            exp.flags.ignore_mandatory = True
            exp.insert()

            # Update Purchase Invoice flag
            if frappe.db.has_column("Purchase Invoice", "is_expense_invoice"):
                frappe.db.set_value("Purchase Invoice", inv.name, "is_expense_invoice", 1)
            if frappe.db.has_column("Purchase Invoice", "expense_invoice"):
                frappe.db.set_value("Purchase Invoice", inv.name, "expense_invoice", exp.name)

            synced_count += 1
        except Exception as e:
            frappe.log_error(title="Sync Past Expense Invoice", message=f"Error syncing {inv.name}: {str(e)}")
            continue

    frappe.msgprint(_("Successfully synced {0} past expense invoices.").format(synced_count))

    return {"synced": synced_count}


@frappe.whitelist()
def make_payment_entry(expense_invoice_name):
    """Creates a Payment Entry against the linked Purchase Invoice"""
    exp = frappe.get_doc("Expense Invoice", expense_invoice_name)
    if not exp.purchase_invoice:
        frappe.throw(_("No Purchase Invoice linked to this Expense Invoice."))

    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    pe = get_payment_entry("Purchase Invoice", exp.purchase_invoice)
    return pe
