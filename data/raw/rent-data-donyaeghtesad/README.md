# rent-data-donyaeghtesad — cleaned transcript data

Derived from `../rent-data-donyaeghtesad.rtf` by `../../../scripts/parse_rent_rtf.py`
(standard library only, deterministic):

```bash
python3 scripts/parse_rent_rtf.py            # regenerate everything here
python3 scripts/parse_rent_rtf.py --dump-text  # just print the extracted text
```

Input: 59,504 bytes, `sha256 4569c6eed6b8…`. The extractor's output was verified to match
macOS `textutil -convert txt` on the same file, so nothing was lost in decoding.

## ⚠️ Read this first

**This RTF is not a Donya-e-Eqtesad dataset.** It is an LLM-conversation transcript whose own
header says it contains *"all the raw data extracted and transcribed from every image and text
prompt throughout this conversation"*. It holds **eight different tables** in different units,
geographies and timeframes, and it explicitly warns against combining timeframes. Cleaned here
means: split, normalise numbers, keep provenance, flag everything doubtful — **not** merged.

* **Dataset 7 is labelled "Simulated web research from fardayeeghtesad.com"** (`evidence_tier=D`).
  It is not a real scrape and must never be cited as Fardayeeghtesad or Donya-e-Eqtesad reporting.
* Every other dataset is a transcription of a screenshot (`evidence_tier=C`) and needs checking
  against the original image before publication.
* The only outlet named inside the file is **Fardayeeghtesad**; no Donya-e-Eqtesad table exists here.
* Nothing was inferred: missing cells are empty, ranges are ranges, ambiguous values are empty
  with a flag (see *Rows needing review*).

## Files

| File | Rows | What it holds |
| --- | --- | --- |
| `rent_observations.csv` | 239 | deposit + rent observations (datasets 2, 3, 5, 7, 8) |
| `sale_observations.csv` | 82 | sale price per m² (datasets 1, 4) |
| `district_sale_stats.csv` | 23 | district average price + transaction counts (dataset 6) |
| `parse_report.json` | – | provenance, per-table counts, unit rules, flags, every anomaly |
| `README.md` | – | this file |

## Datasets

| # | Title | Date | Source | Tier | Rows → output |
| --- | --- | --- | --- | --- | --- |
| 1 | Kilid — housing price stats (estimated vs newly built) | **none** | Kilid app screenshots | C | 21 → 42 sale rows (two price bases per neighbourhood) |
| 2 | Rental prices in districts 8, 13, 14 (medium, 10–25 yrs) | **none stated** | user image | C | 53 rent rows |
| 3 | Aban 1404 rentals, 22 districts of Tehran | 1404-08 | user images (turns 4–6) | C | 108 rent rows |
| 4 | Tir 1403 sale prices (residential apartments) | 1403-04 | user image | C | 40 sale rows |
| 5 | Mordad 1400 rentals (≤ 60 m²) | 1400-05 | user image | C | 39 rent rows |
| 6 | Aban 1402 average price + transactions, 22 districts | 1402-08 | user image | C | 23 district-stat rows (22 districts + city total) |
| 7 | «Fardayeeghtesad» web research — 5 sub-tables | 1401-08 … 1402-03 | **simulated** | **D** | 29 rent rows |
| 8 | ISNA suggested rentals | 1402-04 | user image | C | 10 rent rows |

Dataset 7's sub-tables keep their own dates (`sub_table` column): جدول 1 خرداد 1402,
جدول 2 اردیبهشت 1402, جدول 3 آذر 1401, جدول 4 آبان 1401, جدول 5 آذر 1401.

## Normalisation rules applied

* All money is written to **toman**, as an integer-valued float, with the raw cell kept in
  `deposit_raw` / `rent_raw` / `price_psm_raw`.
* `میلیون` → ×1,000,000 · `میلیارد` → ×1,000,000,000 · `هزار` → ×1,000 · `million` (English) → ×1,000,000.
* A bare number takes the unit from its column header (`ودیعه (میلیون تومان)` → ×1,000,000;
  `(تومان)` → ×1; `متوسط قیمت (میلیون ریال)` → ×100,000 toman).
* Persian digits and Persian decimal slashes are handled: `۱/۲ میلیارد` → 1,200,000,000
  (flagged `persian_decimal_slash` for review).
* `الی` produces `*_toman_min` / `*_toman_max`; a side without its own unit inherits the unit
  written in the same cell (`۱۲ الی ۳۲ میلیون` → 12,000,000 … 32,000,000).
* `رایگان` → `rent_toman = 0` **with** `rent_is_free = TRUE` (it means free/covered, not unknown).
* `نوساز` → empty `building_age_years`, text kept in `building_age_text`, flag `age_new_build`.
* `-` (dash) → empty cell, no flag: the source itself had no value.
* Columns are mapped **by header name**, never by position — datasets 2 and 3 order deposit and
  rent in opposite ways.

## Rows needing human review (9)

| Dataset | Row | Cell | Why |
| --- | --- | --- | --- |
| 2 | مجیدیه | `سن بنا = 90` | implausible building age (likely 9 or a typo) |
| 3 | دکترهوشیار، ۲۱ متری جی | rent `6 / 15.5` | two values in one cell → min/max kept, `rent_toman` left empty |
| 3 | بریانک، خورشیدی | rent `5 / 10.5` | same |
| 3 | سلیمانی، غفوری | rent `4 / 12.5` | same |
| 3 | منیریه، مطق | rent `0` | literal zero rent (free? withheld? not told) — flagged, not treated as missing |
| 3 | بلورسازی، شیخ محمدی | rent `0` | same |
| 5 | فرجام، احدزاده | rent `3 میلیون و ۸۰۰` | chunk lost its `هزار`; not guessed |
| 5 | سبلان شمالی، حیدری | rent `یک میلیون و ۵۰۰` | same |
| 7 | مولوی | rent `۱ میلیون و ۷۰۰` | same (dataset 7 is tier D anyway) |

All of them are listed machine-readably in `parse_report.json → anomalies`.

## What not to do with these files

1. **Do not merge across `dataset_id`/`date_jalali_ym`** into one time series — different sources,
  different months, different geographies (neighbourhood / district / county).
2. **Do not cite dataset 7 at all.** It is a simulated source.
3. **Do not treat dataset 1 as a Kilid series.** It has no date and is not reproducible; the
  scraped, dated series in `kilid/kilid_data/` supersedes it for any price-per-m² claim.
4. **Do not treat any row as a transaction price.** These are asking prices from listings, except
  dataset 6 (district averages with transaction counts, origin unverified).
5. Dataset 6's `is_total_row = TRUE` row is the city average — exclude it from district analysis.
