# DATA_DICTIONARY

| Column | Type | Description |
|---|---|---|
| Country | string | Country name standardized to OWID naming (ISO-mapped) |
| Date (YYYY-MM-DD) | date (string ISO) | Calendar date in ISO format |
| New Cases | float | Daily new confirmed cases. From WHO **date reported to WHO** daily release; `NaN` when no report for that day |
| New Deaths | float | Daily new confirmed deaths. From WHO **date reported to WHO** daily release; `NaN` when no report for that day |
| Total Vaccinations | float | Cumulative total vaccine doses administered (OWID). `NaN` on days without OWID updates |
| Stringency Index | float | OxCGRT Stringency Index relayed by OWID. Sparse/`NaN` in 2023–2024 due to end of routine updates |

## Notes
- No imputation in this strict panel. Missing values reflect true upstream gaps.
- Sorting: `Country`, `Date (YYYY-MM-DD)`; dates are ISO strings.
