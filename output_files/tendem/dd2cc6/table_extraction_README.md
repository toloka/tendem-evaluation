# Table Extraction README

This document describes the automated table extraction settings, heuristics, and known quirks observed when processing the PDF report "Trends – Artificial Intelligence (May 2025)".

Source PDF: /mnt/data/tai.pdf
Primary goal: extract tabular data only (not chart images or captions) into CSV files for downstream cleaning and structuring.

## Output Artifacts
- Initial extraction (broad):
  - Tables directory: /mnt/data/extracted_tables
  - Index: /mnt/data/tables_index.csv
  - Summary: /mnt/data/tables_extraction_summary.json
- Refined extraction (v1):
  - Tables directory: /mnt/data/refined_extracted_tables
  - Index: /mnt/data/refined_tables_index.csv
  - Summary: /mnt/data/refined_tables_extraction_summary.json
  - Rejections log: /mnt/data/refined_tables_rejections.csv
- Refined extraction (v2 – stricter):
  - Tables directory: /mnt/data/refined2_extracted_tables
  - Index: /mnt/data/refined2_tables_index.csv
  - Summary: /mnt/data/refined2_tables_extraction_summary.json
  - Rejections log: /mnt/data/refined2_tables_rejections.csv

CSV convention: page_<pageNumber>_table_<sequence>.csv; rows padded to consistent column counts; no headers.

## Extraction Engines and Settings

Library: pdfplumber
Strategies used:
- Ruling-line detection (preferred):
  - vertical_strategy = "lines"
  - horizontal_strategy = "lines"
  - intersection_tolerance = 5
- Text-based fallback (used only in the initial broad pass):
  - vertical_strategy = "text"
  - horizontal_strategy = "text"
  - snap_tolerance = 3

Notes:
- Ruling-line strategy targets grids with drawn lines; reduces false positives from paragraph text.
- Text-based strategy can yield false positives (captions or mixed layout blocks), hence later disabled.

## Filtering Heuristics (to minimize non-tabular content)

Applied progressively; latest (v2) rules summarized here:

1) Minimum size thresholds
- Require ≥ 4 rows and ≥ 3 columns.
- Smaller grids are frequently titles/captions or layout fragments and are rejected as `too_small`.

2) Caption/paragraph exclusion
- Skip pages with < 50 words (heuristic for title/caption-only slides), logged as `title_page`.
- Reject headers that look like sentences (long + punctuation), logged as `header_sentence`.

3) Column alignment and density
- Compute per-column non-empty ratio and numeric-like ratio.
- Require ≥ 2 columns with ≥ 80% non-empty cells.
- Require ≥ 1 column with ≥ 60% numeric-like cells (numbers, percents, currency, etc.), otherwise `weak_structure`.

4) Long-text dominance
- If > 30% of cells exceed 80 characters, reject as `too_much_long_text`.

5) Normalization
- Rows are padded with blanks to the maximum column count for the table to preserve rectangular shape.
- Headers are not set; downstream cleaning is expected to standardize them.

## Known Quirks & Implications for Cleaning

- Merged cells: pdfplumber can split merged cells unpredictably; expect occasional misalignment requiring manual header alignment.
- Missing headers: many tables extract without explicit header rows; cleaning should infer headers from nearby text or first row tokens.
- Numeric formats: thousands separators, percentages, and currency symbols may appear as text; normalization to numeric types is needed.
- Footnotes within tables: some tables include footnote markers or small-font notes in cells; remove in cleaning.
- Chart-only slides: many pages are charts with no underlying numeric table; these are filtered out by heuristics or logged as rejections.

## Recommended Cleaning Steps (next subtask)

- Map each accepted table to its report section using page ranges and nearby headings.
- Standardize headers (case, spacing) and deduplicate/merge split header rows.
- Convert numeric-like text to numeric types, handle % and currency, unify bps/k/m/bn units.
- Remove footnotes, page numbers, and caption remnants.
- Consolidate related tables into section-level datasets preserving original order.

## Quality & Coverage

- Initial broad pass produced many false positives; do not use those CSVs without additional filtering.
- Refined v1 reduced false positives substantially (accepted 7 tables of 505 candidates).
- Refined v2 applied stricter thresholds per guidance (accepted 5 tables of 505 candidates; 89 pages auto-skipped as title/caption-only).
- Rejections logs list reasons to support audit and future tuning.

## Reproducibility

- Rerun using ruling-line-only settings with the v2 filtering rules above.
- If additional true tables are desired, consider page-specific tolerances and manual review of candidate grids.

## Contact/Traceability

- Source PDF: /mnt/data/tai.pdf
- Landing page: https://www.bondcap.com/reports/tai
- Direct PDF URL: https://www.bondcap.com/report/pdf/Trends_Artificial_Intelligence.pdf
