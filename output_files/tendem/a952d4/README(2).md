# COVID-19 Daily Panel (Strict) — README

**Deliverables**
- CSV: `final_daily_panel.csv`
- Excel: `final_daily_panel.xlsx` (sheet: **Daily Panel**)
- Summary: `final_merge_summary.txt`

**Scope**
- Countries (15): Australia, Brazil, Canada, France, Germany, India, Italy, Japan, Mexico, Russia, South Africa, South Korea, Spain, United Kingdom, United States
- Date window: 2022-01-01 → 2024-12-31 (daily grid)
- Columns: `Country`, `Date (YYYY-MM-DD)`, `New Cases`, `New Deaths`, `Total Vaccinations`, `Stringency Index`
- Retrieval timestamp: 2025-10-22 16:19 UTC

## Provenance (sources)
- **Cases & Deaths (WHO, date reported to WHO):** WHO COVID-19 dashboard/data download (daily statistical release; reflects *date reported to WHO* and includes weekly submissions as single-day lumps).
- **Vaccinations & Stringency (OWID):** Our World in Data COVID-19 datasets. *Stringency Index* is sourced from **OxCGRT** (Oxford COVID-19 Government Response Tracker). OxCGRT ended routine updates after 2022; OWID therefore has sparse/empty stringency values for 2023–2024.
- Notes on cadence changes:
  - From **Aug 2023**, countries were no longer required to report to WHO daily; many switched to **weekly** submissions.
  - **Stringency Index** has **no routine updates in 2023–2024**, so values are `NaN` by design for that period.

## Processing (strict, no imputation)
1. Standardized country names via ISO2/ISO3 mappings (OWID naming).
2. Built a complete daily grid for 15 countries from 2022-01-01 to 2024-12-31.
3. LEFT-joined WHO (cases/deaths) and OWID (vaccinations/stringency) to the grid.
4. **No zero-filling**; missing days remain **NaN**.
5. Enforced ISO date format `YYYY-MM-DD`; sorted by `Country, Date`.

## Quality checks
- Exact schema & column order validated.
- ISO dates verified.
- Duplicate `(Country, Date)` rows = 0.
- CSV vs Excel parity confirmed post-merge.

## Missingness (overall % NaN)
- New Cases: **55.8%**
- New Deaths: **57.1%**
- Total Vaccinations: **61.2%**
- Stringency Index: **66.7%**

### Missingness by year (% NaN)
      New Cases  New Deaths  Total Vaccinations  Stringency Index
Year                                                             
2022       22.9        24.5                21.1               0.0
2023       54.2        54.4                69.5             100.0
2024       90.1        92.4                93.0             100.0

**Interpretation**
- Post-2023 NaNs are expected due to **weekly** reporting to WHO and the **end of OxCGRT daily updates** for stringency.
- The dataset is intentionally *strict* (no fabrication). Use the companion options below for analysis-ready series if needed.

## Suggested companion outputs (on request; not included here)
- **Weekly panel (recommended for trends):** ISO week sums for cases/deaths; last-observation for cumulative vaccinations; mean for stringency.
- **Daily analysis-ready:** Replace cases/deaths with OWID daily aggregates (or disaggregate weekly WHO submissions); forward-fill cumulative vaccinations. Include an `imputed_flag` for transparency.

## Repro & updates
- Inputs: WHO daily statistical release (cases/deaths), OWID COVID-19 datasets (vaccinations, stringency).
- Refresh guidance: rerun the same pipeline with updated sources; expect 2023–2024 daily gaps to persist (structural).

## Limitations
- WHO “date reported” causes lumpy spikes when countries submit weekly batches.
- OxCGRT stringency post-2022 is not routinely maintained → `NaN` for 2023–2024.


## Why Stringency Index is empty in 2023–2024
The Stringency Index in this panel is sourced from OxCGRT via OWID. OxCGRT ended routine daily updates after 2022 and published a final dataset in mid‑2023. As a result, OWID has little to no stringency values for 2023–2024, so those cells appear as `NaN` by design. This is a source‑availability constraint rather than an extraction or merge error.

## Why New Cases / New Deaths / Total Vaccinations have many NaNs in 2023–2024
From August 2023, WHO no longer required countries to report daily, and many countries shifted to weekly or ad‑hoc submissions. The WHO “daily” statistical release reflects **date reported to WHO**, which can manifest as several blank days followed by a single large spike when a weekly batch is submitted. In parallel, some OWID series (especially late‑period vaccination totals and policy metrics) have sparser updates as national reporting wound down. Consequently, post‑2023 values are often missing on a day‑by‑day basis.

### What this means for analysis
- This strict daily panel intentionally preserves `NaN` values instead of fabricating numbers.
- For robust time‑series analysis in 2023–2024, prefer:
  - **Weekly aggregation** (ISO week) for cases/deaths; last‑observation for cumulative vaccinations; mean for stringency.
  - Or a clearly documented **analysis‑ready daily companion** that replaces/derives daily flows (e.g., from OWID daily aggregates or distributed weekly sums) and flags imputed spans.
