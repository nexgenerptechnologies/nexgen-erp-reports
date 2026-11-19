# NexGen ERP Reports

Frappe / ERPNext Custom App containing specialized, statutory, and audit reports for ERPNext.

## Reports Included

### 1. GSTR-2B Inward Summary
A comprehensive summary of all inward supplies and Input Tax Credit (ITC) as per GSTR-2 / GSTR-2B structure.

#### Key Features:
- **Section-wise Inward Breakdown**:
  - `B2B Invoices - 3, 4A`
  - `B2BUR Invoices - 4B`
  - `Credit/Debit Notes - 6C`
  - `Credit/Debit Notes UnRegister - 6C`
  - `Import of Goods/ Capital Goods - 5A, 5B`
  - `Import of Services - 4C`
  - `Nil Rated Invoices - 7A, 7B`
  - `ITC Reversal`
  - `HSN Summary of Inward Supplies - 13`
- **Total Input Tax Credit (ITC) Summary**:
  - Breakdown by CGST, SGST, IGST, Cess, and Grand Total.
- **Interactive Drill-Down**:
  - Clicking on any section (e.g. `B2B Invoices - 3, 4A`) instantly navigates to the **Purchase Invoice List View** filtered for that specific section, date range, and company.
- **Custom Formatted Excel Download**:
  - Download official, styled Excel spreadsheets complete with Company Name, Registered Address, Date Range, Sectional Summary, and Input Tax Credit table.

---

## Installation

1. Get the app via bench:
```bash
bench get-app https://github.com/nexgenerptechnologies/nexgen-erp-reports.git
```

2. Install the app on your site:
```bash
bench --site <your-site-name> install-app nexgen_erp_reports
```

3. Run migrations:
```bash
bench --site <your-site-name> migrate
```

---

## License
MIT
