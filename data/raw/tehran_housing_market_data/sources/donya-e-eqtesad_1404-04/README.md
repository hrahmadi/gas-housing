# Donya-e-Eqtesad rent-asking table — Tir 1404

Second source in this collection: **`data/raw/donya-e-eqtesad_rent-asking_tir-1404.txt`**
(owner-supplied paste, `sha256` in `parse_report.json`), parsed by
`scripts/parse_donyae_eqtesad.py`.

```bash
python3 scripts/parse_donyae_eqtesad.py        # rewrites rent_asking.csv + parse_report.json
```

**This is new data, not a duplicate of the archive.** Dataset 3 of the RTF archive is the *same
Donya-e-Eqtesad series* (its English title in the transcript is *"Suggested rental prices for
medium-sized apartments in the 22 districts of Tehran"*, the same six columns, the same
`6 / 15.5`-style composite cells) but for **Aban 1404**, with different rows and values. This file
covers **Tir 1404**. Together they give two months of the same series.

Provenance, exactly as supplied: `منبع: دنیای اقتصاد (Donya-e-Eqtesad)` ·
`تاریخ: تیر ۱۴۰۴` → `date_jalali_ym = 1404-04`. The attribution is **owner-provided**; the file
itself names no outlet beyond that header line.

## Why this file needed a different parser

It is a **chat paste**, so the table structure is gone in two ways:

1. **No row boundaries** — all rows are concatenated into a single line. A row starts with a
   district marker followed immediately by a Persian letter, which is the only reliable signal.
2. **No column boundaries** — each row is `<district><name><age><area><rent><deposit>` with the
   four numeric columns glued together. Only three tokens survive: an `a / b` rent range, a
   decimal rent (`17.5`), and a `-` for a missing rent.

The parser therefore *enumerates* every arithmetically admissible split of each glued digit run
and accepts a row only when exactly one split exists. Rules, all recorded in `parse_report.json`:

* ranges for admissibility come from the observed values of this table plus its sibling Aban 1404
  table: age 1–45, area 40–260 m², rent 0–120, deposit 100–3000 (million toman);
* a field written with a leading zero is rejected (`01500` is never written for 1500);
* a row whose split is not unique is **left empty and flagged with its candidate list** — never
  guessed;
* the verbatim row text is kept in `row_raw`, so any row can be finished by hand.

## District markers are unreliable in the paste — and were cross-checked

42 rows carry a corrupted marker (`۱*`/`۲*` where 11–20 should be). Worse, the surviving markers
**disagree with the earlier table for about a fifth of comparable rows** (e.g. the paste puts
`تجریش` in 2 while the Aban 1404 table puts it in 1). District geography does not change month to
month, so the parser resolves each row against the earlier tables in this repo and records where
the answer came from:

| `district_number_source` | Rows | Meaning |
| --- | --- | --- |
| `sibling_table_name_match` | 65 | matched a neighbourhood that dataset 2/3 of the archive places in a known district — **this is the trustworthy column** |
| `marker` | 25 | clean marker, no name match available (not cross-checked) |
| `gap_fill` | 5 | corrupted marker resolved between clean anchors |
| `unknown` | 15 | left empty, flagged `district_unresolved` |

Every disagreement is recorded per row as
`district_marker_disagrees_with_sibling_table:<marker>_vs_<verified>`.

## Result

| | |
| --- | --- |
| rows detected | 110 |
| **fully parsed** | **91** |
| ambiguous split (values empty, candidates recorded) | 18 |
| unparsed | 1 (a stray `۱۲` fragment left over from the paste) |
| districts resolved | all 22 present, 2–7 rows each |
| rows with a usable rent | 90 |
| rows with a deposit | 91 |

Columns: `district_number`, `district_number_source`, `district_marker_raw`, `area_name`,
`building_age_years`, `floor_area_sqm`, `rent_toman` (or `_min`/`_max` for a range),
`deposit_toman`, `rent_raw`, `row_raw`, `flag_amount_ambiguous`, `issue_classes`, `notes`,
`source_row_index`, plus provenance (`outlet`, `outlet_evidence`, `evidence_tier=C`,
`verification=unverified_owner_paste`, `date_jalali_raw`, `date_jalali_ym`).

## What would finish this dataset

The 18 ambiguous rows are ambiguous **in the paste**, not in the source table: their rent/deposit
boundary is arithmetically undecidable (e.g. `87831300` is either rent 3 / deposit 1300 or rent 31
/ deposit 300). Supplying any of the following makes every row unambiguous — and the parser will
then re-run with identical rules:

1. the original PDF/Excel export, or
2. the same table pasted **with delimiters** (tabs or `|`, as the Aban 1404 table arrived), or
3. just the rent and deposit for the 18 rows listed in `parse_report.json → ambiguous_rows`.

Until then those 18 rows stay empty and flagged, which is the point: nothing here is guessed.
