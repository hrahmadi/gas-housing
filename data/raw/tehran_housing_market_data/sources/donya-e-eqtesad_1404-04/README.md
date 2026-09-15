# Donya-e-Eqtesad rent-asking table — Tir 1404

Second source in this collection. Canonical input:
**`data/raw/donya-e-eqtesad_rent-asking_tir-1404.md`** (delimited markdown table).
Parser: `scripts/parse_donyae_eqtesad.py`.

```bash
python3 scripts/parse_donyae_eqtesad.py                     # canonical (markdown) input
python3 scripts/parse_donyae_eqtesad.py \
  --input data/raw/donya-e-eqtesad_rent-asking_tir-1404.corrupt-paste.txt \
  --out   sources/donya-e-eqtesad_1404-04/corrupt-paste     # the earlier paste, for audit
```

The parser auto-detects the format. Both produce the same schema (with a `source_format` column),
so the two transcriptions can be diffed — and they were:

| input | rows | fully parsed | ambiguous | unparsed |
| --- | --- | --- | --- | --- |
| `…_tir-1404.md` (canonical, delimited) | 109 | **109** | 0 | 0 |
| `…_tir-1404.corrupt-paste.txt` (superseded) | 110 | 91 | 18 | 1 |

Provenance, exactly as supplied: `منبع: دنیای اقتصاد (Donya-e-Eqtesad)` · `تاریخ: تیر ۱۴۰۴` →
`date_jalali_ym = 1404-04`. The attribution is **owner-provided**; the file names no outlet beyond
that header line. `evidence_tier = C`, `verification = unverified_owner_transcription`.

**Not a duplicate of the archive:** dataset 3 of the RTF archive is the same Donya-e-Eqtesad
series (its English title in that transcript is *"Suggested rental prices for medium-sized
apartments in the 22 districts of Tehran"*, same six columns, same composite cells) but for
**Aban 1404**, with different rows and values. Two months of one series are now held.

## What the clean transcription fixed

The canonical input resolves everything the corrupted paste could not:

* **18 rows** whose rent/deposit boundary was arithmetically undecidable (e.g. `87831300` =
  rent 3 / deposit 1300 **or** rent 31 / deposit 300). All 18 are now read directly.
* **1 row** (a stray `۱۲` fragment) that the paste could not parse at all.
* **42 corrupted district markers** (`۱*`/`۲*` where 11–20 should be).

**The "leave it empty, flag it, list the candidates" policy was validated by this second
transcription:** the true reading was present among the enumerated candidates in **18 of 18**
cases — and in 17 of those the *other* candidate was the plausible-looking one (rent 1, deposit
1900 versus the actual rent 11, deposit 900). Any plausibility heuristic would have guessed wrong
on most rows; refusing to guess was the right call.

## Values preserved as written

| pattern | rows | handling |
| --- | --- | --- |
| rent range, e.g. `6 / 15.5` | 3 | `rent_toman` empty, `rent_toman_min`/`_max` filled, flag `rent_range_as_written` |
| rent `0` | 2 | `rent_toman = 0`, flagged `zero_rent_as_written` (free? withheld? not told) |
| rent `-` | 1 | rent empty, flag `rent_missing_as_written` |
| decimal rent, e.g. `17.5`, `4.5`, `6.5` | 6 | parsed as written |

## ⚠️ District cross-check: 7 rows disagree with the earlier table

The district printed in the table is kept verbatim as `district_number` and is never overwritten.
Each row is also compared with the neighbourhood→district mapping derived from the earlier tables
in this repo (dataset 3 of the archive, Aban 1404); the result is in `district_cross_check`:

| result | rows |
| --- | --- |
| `match` | 58 |
| `conflict` | **7** |
| `unchecked` (no counterpart name) | 44 |

| row | neighbourhood | printed district | earlier table says |
| --- | --- | --- | --- |
| 4 | گیشا | 1 | 2 |
| 5 | تجریش - فخارسر | 2 | 1 |
| 6 | زعفرانیه - سمین | 2 | 1 |
| 7 | ولنجک | 2 | 1 |
| 20 | هروی - پناهی نیا | 4 | 5 |
| 21 | پونک - کمالی | 4 | 5 |
| 31 | شهرداری شمالی - موزه | 7 | 6 |

All seven sit in the **first half** of the table, which is also the half affected by the
side-by-side merge you performed. Two readings are possible and the file cannot settle them:
either the source table genuinely groups these neighbourhoods differently from the Aban table, or
the merge shifted the district column for part of the first half. **This needs the original
layout** — a screenshot or PDF of the Tir 1404 table would resolve it in one look.

## Columns

`district_number`, `district_number_source` (`print` | `marker` | `gap_fill` | `unknown`),
`district_cross_check` (`match` | `conflict` | `unchecked`), `district_marker_raw`, `area_name`,
`building_age_years`, `floor_area_sqm`, `rent_toman` (`_min`/`_max` for ranges), `deposit_toman`,
`rent_raw`, `row_raw`, `source_format`, `flag_amount_ambiguous`, `issue_classes`, `notes`,
`source_row_index`, plus provenance (`outlet`, `outlet_evidence`, `evidence_tier`, `verification`,
`date_jalali_raw`, `date_jalali_ym`, `source_file`).

## Result

| | |
| --- | --- |
| rows | 109 |
| fully parsed | 109 |
| districts covered | all 22 (2–7 rows each) |
| rows with a usable rent | 106 (3 are ranges, 2 are literal zeros, 1 is a dash) |
| rows with a deposit | 109 |
| ambiguous / unparsed | 0 / 0 |
