# NexGen ERP Reports

Frappe / ERPNext Custom App containing specialized, statutory, and audit reports for ERPNext.

---

## Reports Included

### 1. GSTR-2B Inward Summary
A comprehensive summary of all inward supplies and Input Tax Credit (ITC) as per GSTR-2 / GSTR-2B structure.
- **Section-wise Inward Breakdown**: B2B (3, 4A), B2BUR (4B), Credit/Debit Notes (6C), Imports (5A, 5B, 4C), Nil Rated (7A, 7B), ITC Reversal, HSN Summary.
- **Total Input Tax Credit (ITC) Summary**: Breakdown by CGST, SGST, IGST, Cess, and Grand Total.
- **Interactive Drill-Down**: Click on any section to navigate directly to the filtered **Purchase Invoice List View**.
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
- **Excel Export**: One-click download of the complete GSTR-9 multi-section formatted workbook.

---

## Installation & Deployment

### 1. Frappe Cloud Installation
1. Go to **Apps** in Frappe Cloud and click **Add App** (from GitHub).
2. Enter Repository URL:
   ```text
   https://github.com/nexgenerptechnologies/nexgen-erp-reports.git
   ```
3. Select Branch: **`main`**.
4. Once built, open your **Site** -> **Apps** tab -> Click **Install App** for **NexGen ERP Reports**.

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
- Works with standard ERPNext GST as well as the official India Compliance app.

---

## License
MIT
