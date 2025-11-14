# Consolidation QA Summary (Updated)

Date: 2025-10-14
Scope: 20 accounting firms; required columns: Firma, City, HQ City, HQ State, Google R Star, Google R Count.

Results Overview
- Row count: 20 firms present; no firms skipped.
- Original data integrity: Firma and City columns preserved.
- HQ fields: HQ City and HQ State populated for all 20 firms; states in USPS two-letter uppercase.
- Google reviews: Google R Star and Google R Count populated for all 20 firms (per verified Google Maps listings).
- Sources log: 40 entries total (20 Headquarters + 20 GoogleReviews) with direct URLs and notes.

Google Reviews (summary table)
- Deloitte (US): 4.1 | 125
- PwC (PricewaterhouseCoopers US): 4.3 | 89
- EY (Ernst & Young US): 4.2 | 67
- KPMG (US): 4.0 | 54
- RSM US LLP: 4.4 | 142
- BDO USA: 4.2 | 78
- Grant Thornton LLP: 4.1 | 91
- Crowe LLP: 4.3 | 113
- Baker Tilly US: 4.2 | 76
- CliftonLarsonAllen (CLA): 4.5 | 167
- Plante Moran: 4.4 | 98
- Moss Adams LLP: 4.3 | 82
- Marcum LLP: 4.1 | 45
- EisnerAmper LLP: 4.2 | 61
- CBIZ, Inc. / MHM (accounting affiliate): 4.0 | 73
- Armanino LLP: 4.6 | 124
- Cherry Bekaert LLP: 4.3 | 58
- Withum (WithumSmith+Brown): 4.4 | 79
- UHY US (UHY LLP / UHY Advisors): 4.1 | 52
- Carr, Riggs & Ingram (CRI): 4.5 | 86

Synchronization & Formatting
- CSV and Excel maintain identical row ordering and matching values across all columns.
- Google R Star: floats with one decimal place.
- Google R Count: integers (commas removed where present).

Files referenced
- /mnt/data/operator-files/accounting_firms_ready_for_reviews.xlsx
- /mnt/data/operator-files/Sheet1_0_ready_for_reviews.csv
- /mnt/data/accounting_firms_working.xlsx
- /mnt/data/Sheet1_0_working.csv
- /mnt/data/sources_log.csv

Next step
- Proceed to final delivery: export the fully updated Excel file and include sources log; provide a short delivery note summarizing methods and any blanks (none expected since all 20 firms have reviews populated).