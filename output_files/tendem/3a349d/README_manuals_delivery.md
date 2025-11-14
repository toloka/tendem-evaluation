# Oven Manuals Delivery — Consolidated Results

## Scope
This delivery consolidates user manuals for 20 oven models (Beko and Bosch), sourced primarily from official manufacturer CDNs and product pages, with reputable alternates where needed.

## Search Strategy
- Prioritized manufacturer official sources:
  - Beko CDN: https://bekoplc.blob.core.windows.net/bekoupload/manuals
  - Bosch CDN: https://media3.bosch-home.com/Documents
- When an official direct PDF was not readily accessible (e.g., BBDF22300), used the manufacturer product page and attempted reputable alternates (ManualsLib, ManualOwl, retailers like AO, Currys, Euronics).
- Verified model codes against product pages, and accepted series/variant manuals where applicable (Bosch series documents, Beko variant group PDFs).

## Filenaming & Indexing
- Canonical paths use the operator-files/ directory exactly as uploaded.
- A standardized summary index (`manuals_index.csv`) lists basename-only file_name, source_url, status, and notes for quick review.
- The comprehensive index (`manuals_index_all_updated.csv`) includes full file paths, enabling direct file resolution.

## Variant Applicability
- Beko BBAIF22300 is covered by the BBRIF22300 manual (variant group).
- Bosch series manuals (e.g., HBS534B.0B) cover variants such as HBS534BS0B and HBS534BW0B.
- Bosch double oven series (MBS533B.0B) documents apply to MBA/MBS variant codes as indicated by Bosch documentation.

## Notable Challenges
- BBDF22300: Manufacturer provides a product page with an embedded/manual viewer; a direct CDN PDF was not initially available. A local PDF has since been provided and indexed.
- Environment constraints at times prevented direct automated downloads; resolved via expert uploads (documented in the index).

## Verification
- All 20 models are listed in `manuals_index_all_updated.csv` with file paths under operator-files/, source URLs, statuses, and notes.
- Spot checks should confirm that file paths exist and PDFs open (e.g., Bosch HHF113B.0B.pdf, HQA.74B.3B.pdf, Beko CIFY81.pdf).
- Variant coverage notes are included for models using series/variant manuals.

## Maintenance
- If filenames in operator-files/ are standardized (e.g., `manual_{Manufacturer}_{ProductCode}.pdf`), update both indices accordingly.
- For any future missing manuals, attempt manufacturer CDNs first, then trusted alternates, documenting all attempts in the notes.