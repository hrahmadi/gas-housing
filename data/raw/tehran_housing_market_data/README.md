# Tehran housing market data — cleaned, provenance-first

Two source archives, two deterministic parsers, one output tree. Nothing is inferred, no value is
filled in, and everything doubtful is flagged rather than guessed.

| Source | Format | Parser | Output |
| --- | --- | --- | --- |
| `../rent-data-donyaeghtesad.rtf` (mixed conversation transcript) | RTF | `scripts/parse_rent_rtf.py` | `observations/`, `datasets/`, `excluded/`, `parse_report.json` |
| `../donya-e-eqtesad_rent-asking_tir-1404.md` (Donya-e-Eqtesad table, delimited) | markdown | `scripts/parse_donyae_eqtesad.py` | `sources/donya-e-eqtesad_1404-04/` |
| `../donya-e-eqtesad_rent-asking_tir-1404.corrupt-paste.txt` (superseded first paste) | plain text | same script (`--input`) | `sources/…/corrupt-paste/` |

```bash
python3 scripts/parse_rent_rtf.py          # transcript archive
python3 scripts/parse_donyae_eqtesad.py    # Donya-e-Eqtesad table (canonical)
```

Row conservation in the transcript archive is exact: 323 source table rows →
157 + 82 + 23 production rows + 82 excluded rows = **344** (dataset 1's 21 rows each carry two
price bases).

## Layout

```
tehran_housing_market_data/
├── observations/                       production rows from the transcript archive
│   ├── rent_observations.csv           157 rows — dated rent/deposit observations
│   ├── sale_observations.csv            82 rows — price per m²
│   └── district_sale_stats.csv          23 rows — district averages + transaction counts
├── datasets/                           publication files (one per source table)
│   ├── rent_asking_1404-08_tehran_22_districts.csv                108
│   ├── rent_asking_1400-05_tehran_up_to_60sqm.csv                  39
│   ├── rent_asking_isna_1402-04_tehran.csv                         10
│   ├── sale_price_1403-04_tehran_apartments.csv                    40
│   ├── sale_price_district_avg_1402-08_origin_unverified.csv       23
│   └── sale_price_kilid_images_undated_tehran_neighbourhoods.csv   42
├── sources/
│   └── donya-e-eqtesad_1404-04/        second source: Donya-e-Eqtesad, Tir 1404
│       ├── rent_asking.csv             109 rows, 109 fully parsed (see its README)
│       ├── parse_report.json
│       └── corrupt-paste/              the superseded first paste, kept for audit
├── excluded/                           not to be used — reason on every row
│   ├── rent_asking_undated_tehran_districts_8_13_14.csv   53 rows
│   └── dataset_7_simulated.csv                            29 rows
├── parse_report.json
└── README.md
```

## ⛔ Excluded material

Both blocks are out of every production file (verified: zero rows leak into `observations/` or
`datasets/`), and every excluded row carries `excluded_reason`.

| File | Rows | Reason |
| --- | --- | --- |
| `excluded/rent_asking_undated_tehran_districts_8_13_14.csv` | 53 | **owner instruction: incomplete** — the transcript states the image carried no date, and it covers only districts 8, 13 and 14 |
| `excluded/dataset_7_simulated.csv` | 29 | **simulated / unreliable provenance** — the transcript labels it *"Simulated web research from fardayeeghtesad.com"* (Fardayeeghtesad, tier D) |

## Sources inside the transcript archive

| # | Table | Provenance line (verbatim) | Date | Rows | Tier |
| --- | --- | --- | --- | --- | --- |
| 1 | Kilid est. vs newly-built price/m² | `Kilid (Images 1 & 2)` | **none** | 42 sale | C |
| 2 | District 8/13/14 rentals | `User Image (Turn 3)` | none stated | **excluded (53)** | C |
| 3 | Aban 1404 rentals, 22 districts | `User Images (Turns 4, 5, 6)` | 1404-08 | 108 rent | C |
| 4 | Tir 1403 sale prices | `User Image (Turn 7)` | 1403-04 | 40 sale | C |
| 5 | Mordad 1400 rentals ≤ 60 m² | `User Image (Turn 8)` | 1400-05 | 39 rent | C |
| 6 | Aban 1402 district averages + transactions | `User Image (Turn 11)` | 1402-08 | 23 stats | C |
| 7 | "Fardayeeghtesad" web research | `Simulated web research from fardayeeghtesad.com.` | 1401-08 → 1402-03 | **excluded (29)** | **D** |
| 8 | ISNA suggested rentals | `User Image (Turn 13)` | 1402-04 | 10 rent | C |

220 of the 262 production rows are dated; the 42 undated ones are dataset 1. No table row carries
its own date — the period comes from the dataset header or sub-table title only.

**The archive names no Donya-e-Eqtesad source.** The string «اقتصاد» occurs zero times in its
Persian text; the only outlet string inside is `fardayeeghtesad.com`, in the excluded block. The
owner-supplied Tir 1404 table under `sources/` *is* attributed to Donya-e-Eqtesad, by its own
header line — recorded as owner-provided, not as something this archive proves.

## Naming policy

Publication files are named **measurement kind + date** (+ outlet only where a source names one).
No file is named after an outlet we cannot verify, which is why no `rent_asking_donyaye_eghtesad_*`
file appears under `datasets/`: that series lives under `sources/` with its own provenance line.
The dated, reproducible Kilid sale series is in `kilid/kilid_data/`.

## Quality flags — three-way classification (+ notation)

`issue_classes` on every row; `flag_amount_ambiguous = TRUE` whenever the amount could not be
trusted as written.

| Class | Meaning | Policy | Instances |
| --- | --- | --- | --- |
| `data_error` | the pipeline can prove and fix it | must not survive — all six parser bugs were fixed and are listed in `parse_report.json → parser_fixes` | 0 |
| `source_ambiguity` | the source itself does not say clearly | value stays empty (or min/max), flag stays | 10 |
| `source_anomaly` | looks strange but may be real | keep the value, flag it, never remove it | 1 |
| `notation` | recorded assumption / notation | no action | 20 |

Rows needing a human in the rent file (9 amounts + 1 anomaly):

| Class | Dataset / row | Cell | Why | Output holds |
| --- | --- | --- | --- | --- |
| anomaly | D2 · row 46 · `مجیدیه` | `سن بنا = 90` | implausible age | in `excluded/`, `90` kept and flagged |
| ambiguity | D3 · row 144 · `دکترهوشیار` | rent `6 / 15.5` | two values in one cell | min/max only |
| ambiguity | D3 · row 148 · `بریانک` | rent `5 / 10.5` | same | min/max only |
| ambiguity | D3 · row 152 · `سلیمانی، غفوری` | rent `4 / 12.5` | same | min/max only |
| ambiguity | D3 · row 153 · `منیریه` | rent `0` | literal zero | `0`, not missing |
| ambiguity | D3 · row 186 · `بلورسازی` | rent `0` | same | `0` |
| ambiguity | D5 · row 297 · `فرجام، احدزاده` | rent `3 میلیون و ۸۰۰` | chunk lost its «هزار» | empty + flag |
| ambiguity | D5 · row 308 · `سبلان شمالی، حیدری` | rent `یک میلیون و ۵۰۰` | same | empty + flag |
| ambiguity | D8 · row 413 · `پاسداران` | deposit `۱/۲ میلیارد` | Persian decimal slash | 1,200,000,000 + flag |
| ambiguity | D8 · row 415 · `نیاوران` | deposit `۱/۴ میلیارد` + `رایگان` | both | 1,400,000,000 + free flag |

## Dataset 4 reconciliation (Tir 1403)

Verdict: **sale price per m², not rent** (recorded in `parse_report.json → reconciliation`):
header `قیمت هر مترمربع (تومان)`, the transcript's own title and note say sales, magnitudes are
tens-to-hundreds of millions of toman per m² while every rent row here is per month, and floor
areas span 36–315 m² — so it is not the recalled "70–100 m² rent table". No Tir 1403 rent table
exists in the archive; the larger-apartment rent table in it is dataset 3, dated Aban 1404.

## Policies

* **Rent and sale are never interconverted.** `rent_*` columns are observed asking rents;
  `sale_*`/`price_psm_*` are observed asking sale prices; no column is derived from the other.
* **Methodology is frozen.** New source problems get a new flag class, not a re-tuning that would
  move existing values.
* **Raw + parsed are always kept side by side**: `deposit_raw`/`deposit_toman`,
  `rent_raw`/`rent_toman(_min/_max)`, `price_psm_raw`/`price_psm_toman`,
  `building_age_text`/`_years`, plus `dataset_id`, `source_row`, `source_kind`, `source_label`,
  `evidence_tier`, `verification`, `date_jalali_raw`/`_ym`/`_status`, `geography_level`,
  `issue_classes`, `notes`.
