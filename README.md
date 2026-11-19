# NexGen ERP Reports

Frappe / ERPNext Custom App containing specialized, statutory, and audit reports for ERPNext.

---

## Reports Included

### 1. GSTR-2B Inward Summary
A comprehensive summary of all inward supplies and Input Tax Credit (ITC) as per GSTR-2 / GSTR-2B structure.
- **Section-wise Inward Breakdown**: B2B (3, 4A), B2BUR (4B), Credit/Debit Notes (6C), Imports (5A, 5B, 4C), Nil Rated (7A, 7B), ITC Reversal, HSN Summary.
- **Total Input Tax Credit (ITC) Summary**: Breakdown by CGST, SGST, IGST, Cess, and Grand Total.
- **Interactive Drill-Down**: Click on any section name or record count to open the **Purchase Invoice List View** filtered for that specific section, company, and date range.
- **Excel Export**: Formatted official workbook matching the statutory layout.

### 2. GSTR-9 Annual Return
Official statutory annual GST return summary matching Form GSTR-9.
- **Table 4**: Details of advances, inward and outward supplies on which tax is payable (4A to 4N).
- **Table 5**: Details of outward supplies on which tax is not payable (5A to 5N).
- **Table 6**: Details of ITC availed (6A to 6O).
- **Table 7**: Details of ITC reversal and ineligible ITC (7A to 7J).
- **Table 8**: Other ITC reconciliation (8A to 8K).
- **Table 10 - 13**: Amendments and prior period adjustments.
- **Table 16**: Composition supplies and deemed supplies.
- **Table 17 & 18**: HSN-wise summary of outward and inward supplies.
- **Interactive Drill-Down**: Click on outward sections (4A–5H, 17) to view filtered **Sales Invoices**, or inward sections (6B–7E, 18) to view filtered **Purchase Invoices**.
- **Excel Export**: One-click download of the complete GSTR-9 multi-section formatted workbook.

### 3. Ageing Receivables FIFO Basis
Busy-style FIFO Accounts Receivable Ageing report for Customers.
- **True FIFO Allocation**: Allocates credits against the oldest debit vouchers first, calculating exact ageing on remaining open amounts.
- **Statutory Slabs**: `( 0 - 30 ) Days`, `( 31 - 60 ) Days`, `( 61 - 90 ) Days`, `( 91 - 120 ) Days`, `( 121 - 150 ) Days`, `( >= 151 ) Days`.
- **Interactive Drill-Down**: Click on any Customer name to instantly open their **General Ledger** statement.
- **Mathematical Accuracy**: The sum of all ageing slabs strictly reconciles with the customer's Closing Amount.
- **Excel Export**: Formatted Excel download with company headers, date stamps, and column totals.

### 4. Ageing Payable FIFO Basis
Busy-style FIFO Accounts Payable Ageing report for Suppliers.
- **True FIFO Allocation**: Allocates payments and debit notes against the oldest purchase bills first, calculating exact ageing on remaining open payables.
- **Statutory Slabs**: `( 0 - 30 ) Days`, `( 31 - 60 ) Days`, `( 61 - 90 ) Days`, `( 91 - 120 ) Days`, `( 121 - 150 ) Days`, `( >= 151 ) Days`.
- **Interactive Drill-Down**: Click on any Supplier name to instantly open their **General Ledger** statement.
- **Mathematical Accuracy**: The sum of all ageing slabs strictly reconciles with the supplier's Closing Amount.
- **Excel Export**: Formatted Excel download with company headers, date stamps, and column totals.

---

## Installation & Deployment

### 1. Frappe Cloud Installation
1. Go to **Apps** in Frappe Cloud and click **Add App** (from GitHub).
2. Enter Repository URL:
   ```text
   https://github.com/nexgenerptechnologies/nexgen-erp-reports.git
   ```
3. Select Branch: **`main`**.
4. Once built, open your **Site** -> **Apps** tab -> Click **Install App** (or **Update**) for **NexGen ERP Reports**.

### 2. Self-Hosted Bench Installation
```bash
bench get-app https://github.com/nexgenerptechnologies/nexgen-erp-reports.git
bench --site <your-site-name> install-app nexgen_erp_reports
bench --site <your-site-name> migrate
```

---

## Compatibility
- ERPNext v15 & v16
- Frappe Framework v15 & v16
- Frappe Cloud ready

---

## License
MIT
