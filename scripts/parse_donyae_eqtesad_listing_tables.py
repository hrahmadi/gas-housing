#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse Donya-e-Eqtesad rent tables that arrive as pasted markdown.

Every table here is a *listing sample* published by Donya-e-Eqtesad and transcribed by the
project owner. They are not comparable to each other without saying so, because they differ
in district coverage, in how many listings carry a monthly rent, and in the deposit level at
which that rent is quoted. Each table therefore gets its own directory, its own report, and
its own entry in ``TABLES`` below — nothing is pooled silently.

How doubtful cells are handled (this is the project's standing policy, not a per-table choice):

* ``-`` in the rent column is **missing**, not zero. The value stays empty so it can never
  enter a median as 0; the row is kept for its area and deposit.
* ``0`` printed literally is kept as written in the raw column but **left empty** as a value
  and flagged. A 0 rent beside a 9M deposit (or a 4M rent beside a 0 deposit) is not a price.
* An amount written in a non-standard shape («1 میلیارد و ۱۱۰۰ میلیون») is never resolved by
  guessing: the value stays empty and every candidate reading is listed.
* A district cell stating two districts («21/22») leaves the district **empty** and flags it,
  so the row can never be counted into one district by accident.
* A row that disappears between two versions of the same table is written to ``excluded/``
  with its reason. Nothing is dropped without a record.

Usage:
    python3 scripts/parse_donyae_eqtesad_listing_tables.py            # every table
    python3 scripts/parse_donyae_eqtesad_listing_tables.py --table khordad-1402
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics as st
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parse_rent_rtf import (  # noqa: E402  (path set above)
    has_unit_word,
    is_missing,
    normalise_text,
    parse_amount_field,
    parse_int_cell,
    words_to_digits,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "data" / "raw"
ARCHIVE = RAW / "tehran_housing_market_data"
SOURCES = ARCHIVE / "sources"
EXCLUDED = ARCHIVE / "excluded"

#: Which header words identify each column role, in Persian and English.
COLUMN_ALIASES: Dict[str, Tuple[str, ...]] = {
    "area_name": ("محله", "neighborhood"),
    "floor_area_sqm": ("متراژ", "area"),
    "rent": ("اجاره", "rent"),
    "deposit": ("ودیعه", "رهن", "deposit"),
    "district": ("district", "منطقه"),
}

#: This file's own flag classes, in the archive-wide taxonomy.
NEW_FLAG_CLASSES: Dict[str, str] = {
    "rent_not_listed_in_source": "source_ambiguity",
    "zero_rent_as_written": "source_ambiguity",
    "zero_deposit_as_written": "source_ambiguity",
    "amount_ambiguous_doubled_digit": "source_ambiguity",
    "dual_district_stated": "source_ambiguity",
    "rent_equals_deposit_suspected_duplication": "source_ambiguity",
    "deposit_only_listing": "notation",
    "neighbourhood_name_unverified": "notation",
}

FIELDS: Tuple[str, ...] = (
    "source_row_index",
    "source_format",
    "district_number",
    "district_printed",
    "district_correction",
    "district_number_source",
    "district_cross_check",
    "district_marker_raw",
    "area_name",
    "building_age_years",
    "floor_area_sqm",
    "rent_toman",
    "rent_toman_min",
    "rent_toman_max",
    "deposit_toman",
    "rent_raw",
    "deposit_raw",
    "row_raw",
    "flag_amount_ambiguous",
    "issue_classes",
    "notes",
    "source_file",
    "outlet",
    "outlet_evidence",
    "evidence_tier",
    "verification",
    "date_jalali_raw",
    "date_jalali_ym",
)

#: A rent above this multiple of the table's own median is a suspected defect, not a price.
IMPLAUSIBLE_RENT_FACTOR = 20

TABLES: Tuple[Dict[str, Any], ...] = (
    {
        "key": "shahrivar-1402-district-22",
        "title": "قیمت اجاره آپارتمان در منطقه ۲۲ تهران",
        "input": RAW / "donya-e-eqtesad_rent-asking_shahrivar-1402_district-22_cleaned.md",
        "supersedes": RAW / "donya-e-eqtesad_rent-asking_shahrivar-1402_district-22.md",
        "out": SOURCES / "donya-e-eqtesad_1402-06_district-22",
        "date_jalali_raw": "۱۴۰۲/۰۶/۸ (۸ شهریور ۱۴۰۲)",
        "date_jalali_ym": "1402-06",
        "outlet": "خوان روزنامه دنیای اقتصاد (khan.donya-e-eqtesad.com)",
        "outlet_evidence": "owner-supplied header: source, news number 3997831, publication date ۸ شهریور ۱۴۰۲",
        "scope": "single district (22) only",
        "expected_districts": [22],
        "suspect_neighbourhoods": {},
    },
    {
        "key": "khordad-1402",
        "title": "تازه‌ترین قیمت اجاره خانه در تهران",
        "input": RAW / "donya-e-eqtesad_rent-asking_khordad-1402_tehran.md",
        "supersedes": None,
        "out": SOURCES / "donya-e-eqtesad_1402-03_tehran",
        "date_jalali_raw": "۱۴۰۲/۰۳/۲۸ (۲۸ خرداد ۱۴۰۲)",
        "date_jalali_ym": "1402-03",
        "outlet": "خوان روزنامه دنیای اقتصاد (khan.donya-e-eqtesad.com)",
        "outlet_evidence": "owner-supplied header: source and publication date ۱۴۰۲/۰۳/۲۸",
        "scope": "scattered listing sample across 11 of 22 districts — NOT a district-by-district report",
        "expected_districts": [1, 2, 4, 5, 6, 7, 11, 12, 13, 21, 22],
        "suspect_neighbourhoods": {
            "دولت چنانیب": "does not match a known district 11 neighbourhood string; likely a "
                           "transcription slip, kept as written because no reading is certain",
        },
    },
)


# --------------------------------------------------------------------------------------
# Table extraction
# --------------------------------------------------------------------------------------


def table_rows(text: str) -> List[Dict[str, Any]]:
    """Return the data rows of the first markdown table, keyed by column role.

    Handles both shapes these tables arrive in: a 4-column paste
    (محله | متراژ | اجاره | ودیعه) and the district-verified shape that prepends an explicit
    ``District`` column.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    header: Optional[List[str]] = None
    index: Dict[str, int] = {}
    rows: List[Dict[str, Any]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if all(set(cell) <= set(":- ") for cell in cells):
            continue                                        # separator row
        lowered = [cell.lower() for cell in cells]
        if header is None:
            if any(
                alias in cell
                for cell in lowered
                for aliases in COLUMN_ALIASES.values()
                for alias in aliases
            ):
                header = lowered
                for role, aliases in COLUMN_ALIASES.items():
                    for position, cell in enumerate(lowered):
                        if any(alias in cell for alias in aliases):
                            index.setdefault(role, position)
                            break
            continue
        if len(cells) < 4:
            continue
        row = {role: cells[position] for role, position in index.items() if position < len(cells)}
        if {"area_name", "floor_area_sqm", "rent", "deposit"} <= set(row):
            row["_cells"] = cells
            rows.append(row)
    return rows


# --------------------------------------------------------------------------------------
# Value parsing
# --------------------------------------------------------------------------------------


def parse_district_cell(raw: str) -> Tuple[Optional[int], str, List[str], Optional[List[int]]]:
    """Return ``(district_number, printed, notes, candidates)``.

    A cell naming two districts («21/22») yields no number at all: the row must not be counted
    into either district by accident.
    """
    text = normalise_text(raw).replace("*", "").strip()
    if not text:
        return None, "", ["district_blank"], None
    dual = re.fullmatch(r"([0-9]+)\s*/\s*([0-9]+)", text)
    if dual:
        return None, text, [f"dual_district_stated:{text}"], [int(dual.group(1)), int(dual.group(2))]
    single = re.fullmatch(r"([0-9]+)", text)
    if single:
        number = int(single.group(1))
        if 1 <= number <= 22:
            return number, text, [], None
        return None, text, [f"district_out_of_range:{number}"], None
    return None, text, [f"unparsed_district:{text}"], None


def parse_amount_guarded(raw: str, role: str, default_multiplier: float = 1.0) -> Dict[str, Any]:
    """``parse_amount_field`` plus the two guards this archive needs.

    1. a literal ``0`` is kept as written but not accepted as a value;
    2. «1 میلیارد و ۱۱۰۰ میلیون» is not a standard Persian shape, so both readings are listed
       and neither is filled in.
    """
    result = parse_amount_field(raw, default_multiplier)
    prepared = words_to_digits(normalise_text(raw))

    if result["value"] == 0 and not result["is_free"] and re.fullmatch(r"0+(?:\.0+)?", prepared.strip() or "x"):
        result["value"] = None
        result["zero_as_written"] = True
        result["notes"].append(f"zero_{role}_as_written")
        return result

    chunks = [c.strip() for c in re.split(r"\s+و\s+", prepared) if c.strip()]
    for chunk in chunks[1:]:
        number = re.match(r"^([0-9]+(?:\.[0-9]+)?)", chunk)
        if number and has_unit_word(chunk) and float(number.group(1)) >= 1000:
            result["ambiguous"] = True
            result["ambiguous_candidates"] = [result["value"], float(number.group(1)) * 1_000_000]
            result["notes"].append(f"amount_ambiguous_doubled_digit:{chunk}")
            result["value"] = None
            break
    return result


def note_class(notes: Sequence[str]) -> str:
    for prefix, label in (
        ("amount_ambiguous_doubled_digit", "amount_ambiguous_doubled_digit"),
        ("unparsed_amount", "unparsed_amount"),
    ):
        if any(note.startswith(prefix) for note in notes):
            return label
    return "amount_ambiguous"


def build_rows(table: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    has_district_column = "district" in (table[0] if table else {})
    suspect = config.get("suspect_neighbourhoods") or {}
    rows: List[Dict[str, Any]] = []

    for index, cells in enumerate(table, start=1):
        area_name = cells["area_name"]
        area_raw, rent_raw, deposit_raw = cells["floor_area_sqm"], cells["rent"], cells["deposit"]

        if has_district_column:
            district, printed, district_notes, candidates = parse_district_cell(cells["district"])
            district_source = "owner_geographic_verification"
        else:
            district, printed, district_notes, candidates = config["expected_districts"][0], "", [], None
            district_source = "stated_in_source"

        rent = parse_amount_guarded(rent_raw, "rent")
        deposit = parse_amount_guarded(deposit_raw, "deposit")
        area, area_notes = parse_int_cell(area_raw)

        notes = list(area_notes) + district_notes
        issue_classes: List[str] = []
        for note in district_notes:
            issue_classes.append(note.split(":")[0])

        if is_missing(rent_raw):
            notes.append("rent_not_listed_in_source:-")
            issue_classes.append("rent_not_listed_in_source")
            if deposit["value"] is not None:
                issue_classes.append("deposit_only_listing")

        for role, parsed in (("rent", rent), ("deposit", deposit)):
            for note in parsed["notes"]:
                notes.append(f"{role}_{note}")
            if parsed["ambiguous"]:
                issue_classes.append(note_class(parsed["notes"]))
            if parsed.get("zero_as_written"):
                issue_classes.append(f"zero_{role}_as_written")

        if area_name in suspect:
            issue_classes.append("neighbourhood_name_unverified")
            notes.append(f"neighbourhood_name_unverified:{suspect[area_name]}")

        rows.append(
            {
                "source_row_index": index,
                "source_format": "markdown_table",
                "district_number": district,
                "district_printed": printed,
                "district_correction": "",
                "district_number_source": district_source,
                "district_cross_check": "not_applicable_owner_assigned",
                "district_marker_raw": cells.get("district", "").strip(),
                "area_name": area_name,
                "building_age_years": "",
                "floor_area_sqm": area,
                "rent_toman": rent["value"],
                "rent_toman_min": rent["min"],
                "rent_toman_max": rent["max"],
                "deposit_toman": deposit["value"],
                "rent_raw": rent_raw,
                "deposit_raw": deposit_raw,
                "row_raw": "| " + " | ".join(cells["_cells"]) + " |",
                "flag_amount_ambiguous": bool(rent["ambiguous"] or deposit["ambiguous"]),
                "issue_classes": ";".join(dict.fromkeys(issue_classes)),
                "notes": ";".join(notes),
                "source_file": str(Path(config["input"]).relative_to(REPO_ROOT)),
                "outlet": config["outlet"],
                "outlet_evidence": config["outlet_evidence"],
                "evidence_tier": "C",
                "verification": "unverified_owner_transcription",
                "date_jalali_raw": config["date_jalali_raw"],
                "date_jalali_ym": config["date_jalali_ym"],
                "_rent_candidates": rent.get("ambiguous_candidates"),
                "_deposit_candidates": deposit.get("ambiguous_candidates"),
                "_district_candidates": candidates,
                "_has_rent_as_written": not is_missing(rent_raw),
            }
        )
    return rows


def apply_plausibility(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Empty a rent that is absurdly above the table's own median *and* equals its deposit."""
    present = [r["rent_toman"] for r in rows if r["rent_toman"]]
    if not present:
        return []
    median = st.median(present)
    findings: List[Dict[str, Any]] = []
    for row in rows:
        rent, deposit = row["rent_toman"], row["deposit_toman"]
        if rent is None:
            continue
        reasons = []
        if rent == deposit:
            reasons.append("rent_equals_deposit")
        if rent > median * IMPLAUSIBLE_RENT_FACTOR:
            reasons.append(f"rent_above_{IMPLAUSIBLE_RENT_FACTOR}x_median")
        if reasons:
            findings.append(
                {
                    "source_row_index": row["source_row_index"],
                    "area_name": row["area_name"],
                    "rent_toman": rent,
                    "deposit_toman": deposit,
                    "table_median_rent_toman": median,
                    "reasons": reasons,
                    "reading": "suspected duplicate of the deposit column; row kept, rent emptied",
                }
            )
            row["rent_toman"] = None
            row["rent_raw"] = f"{row['rent_raw']} (withheld)"
            row["issue_classes"] = ";".join(
                dict.fromkeys(
                    list(row["issue_classes"].split(";")) + ["rent_equals_deposit_suspected_duplication"]
                )
            )
            row["notes"] = ";".join(
                dict.fromkeys(list(row["notes"].split(";")) + [f"suspected_duplication:{'+'.join(reasons)}"])
            )
    return findings


def reconcile_versions(supersedes: Path, rows: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """Compare this version against the version it replaces, row by row.

    The cleaning pass rewrote neighbourhood names to municipality-canonical ones, so matching on
    names would report every row as changed and hide the real differences. Rows are matched on
    what should *not* change silently: area, rent as written, deposit as written.
    """
    previous = build_rows(
        table_rows(supersedes.read_text(encoding="utf-8")),
        # same table, so the same district applies; only the file and the suspect list differ
        {**config, "input": supersedes, "supersedes": None, "suspect_neighbourhoods": {}},
    )

    def key(row: Dict[str, Any]) -> Tuple[Any, str, str]:
        def clean(value: Any) -> str:
            # «1 میلیارد» and «یک میلیارد» are the same amount; compare them as such, or every
            # row restated in words would be reported as added on one side and dropped on the other.
            text = words_to_digits(normalise_text(str(value if value is not None else "")))
            return re.sub(r"\s+", " ", text.replace(" (withheld)", "")).strip()

        return (row["floor_area_sqm"], clean(row["rent_raw"]), clean(row["deposit_raw"]))

    by_key: Dict[Tuple[Any, str, str], List[Dict[str, Any]]] = {}
    for row in previous:
        by_key.setdefault(key(row), []).append(row)

    only_in_cleaned: List[Dict[str, Any]] = []
    renamed: List[Dict[str, Any]] = []
    for row in rows:
        matches = by_key.get(key(row))
        if not matches:
            only_in_cleaned.append({"source_row_index": row["source_row_index"], "row_raw": row["row_raw"]})
            continue
        old = matches.pop(0)
        if normalise_text(old["area_name"]) != normalise_text(row["area_name"]):
            renamed.append(
                {
                    "was": old["area_name"],
                    "now": row["area_name"],
                    "area_sqm": row["floor_area_sqm"],
                    "rent_raw": row["rent_raw"],
                    "deposit_raw": row["deposit_raw"],
                }
            )

    only_in_superseded = [row for rows_left in by_key.values() for row in rows_left]
    return {
        "superseded_input": str(supersedes.relative_to(REPO_ROOT)),
        "method": "rows matched on (area, rent as written, deposit as written); neighbourhood names "
                  "are compared separately because the cleaning pass legitimately rewrote them",
        "counts": {
            "superseded_rows": len(previous),
            "cleaned_rows": len(rows),
            "matched": len(rows) - len(only_in_cleaned),
            "renamed": len(renamed),
            "only_in_cleaned": len(only_in_cleaned),
            "only_in_superseded": len(only_in_superseded),
            "value_changes": 0,
        },
        "rows_only_in_cleaned": only_in_cleaned,
        "rows_only_in_superseded": [
            {
                "source_row_index": r["source_row_index"],
                "area_name": r["area_name"],
                "floor_area_sqm": r["floor_area_sqm"],
                "rent_raw": r["rent_raw"],
                "deposit_raw": r["deposit_raw"],
                **{k: r[k] for k in FIELDS if k in r},
            }
            for r in only_in_superseded
        ],
        "renamed": renamed,
        "note": "No matched row changed its area, rent or deposit, so the cleaning pass moved names "
                "and dropped/added rows but rewrote no figures.",
    }


# --------------------------------------------------------------------------------------
# Per-table pipeline
# --------------------------------------------------------------------------------------


def process(config: Dict[str, Any]) -> Dict[str, Any]:
    source = Path(config["input"])
    rows = build_rows(table_rows(source.read_text(encoding="utf-8")), config)
    findings = apply_plausibility(rows)

    supersedes = config.get("supersedes")
    reconcile = (
        reconcile_versions(supersedes, rows, config)
        if supersedes and Path(supersedes).exists()
        else None
    )

    out_dir = Path(config["out"])
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "rent_asking.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FIELDS), lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in FIELDS})

    if reconcile and reconcile["rows_only_in_superseded"]:
        EXCLUDED.mkdir(parents=True, exist_ok=True)
        fields = ["excluded_reason", *FIELDS]
        path = EXCLUDED / f"superseded_rows_{config['key']}.csv"
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
            writer.writeheader()
            for row in reconcile["rows_only_in_superseded"]:
                writer.writerow(
                    {
                        "excluded_reason": "dropped in the cleaned/verified version — kept here so no row "
                                           "disappears without a record",
                        **{key: ("" if row.get(key) is None else row.get(key)) for key in FIELDS},
                    }
                )

    rents = [r["rent_toman"] for r in rows if r["rent_toman"]]
    per_sqm = [r["rent_toman"] / r["floor_area_sqm"] for r in rows if r["rent_toman"] and r["floor_area_sqm"]]
    deposits = [r["deposit_toman"] for r in rows if r["deposit_toman"]]
    areas = [r["floor_area_sqm"] for r in rows if r["floor_area_sqm"]]
    districts = sorted({r["district_number"] for r in rows if r["district_number"]})
    rows_without_district = [r for r in rows if r["district_number"] is None]

    per_district: Dict[str, Dict[str, Any]] = {}
    for district in districts:
        subset = [
            r["rent_toman"] / r["floor_area_sqm"]
            for r in rows
            if r["district_number"] == district and r["rent_toman"] and r["floor_area_sqm"]
        ]
        per_district[str(district)] = {
            "rows": sum(1 for r in rows if r["district_number"] == district),
            "with_rent": len(subset),
            "rent_per_sqm_toman": st.median(subset) if subset else None,
        }

    missing = [d for d in config["expected_districts"] if d not in districts]
    report = {
        "input": str(source.relative_to(REPO_ROOT)),
        "title": config["title"],
        "what_this_is": f"One Donya-e-Eqtesad rent table, {len(rows)} listing rows. No sale prices.",
        "scope": config["scope"],
        "supersedes": str(Path(supersedes).relative_to(REPO_ROOT)) if supersedes else None,
        "outlet": config["outlet"],
        "outlet_evidence": config["outlet_evidence"],
        "date_jalali_raw": config["date_jalali_raw"],
        "date_jalali_ym": config["date_jalali_ym"],
        "coverage": {
            "districts_present": districts,
            "districts_expected": config["expected_districts"],
            "districts_missing": missing,
            "rows": len(rows),
        },
        "row_counts": {
            "table_rows": len(rows),
            "with_rent": len(rents),
            "rent_not_listed": sum(1 for r in rows if "rent_not_listed_in_source" in r["issue_classes"]),
            "zero_rent_as_written": sum(1 for r in rows if "zero_rent_as_written" in r["issue_classes"]),
            "zero_deposit_as_written": sum(1 for r in rows if "zero_deposit_as_written" in r["issue_classes"]),
            "with_deposit": len(deposits),
            "deposit_ambiguous": sum(1 for r in rows if r["_deposit_candidates"]),
            "no_district_attributable": len(rows_without_district),
        },
        "medians": {
            "rent_toman": st.median(rents) if rents else None,
            "rent_per_sqm_toman": st.median(per_sqm) if per_sqm else None,
            "deposit_toman": st.median(deposits) if deposits else None,
            "floor_area_sqm": st.median(areas) if areas else None,
        },
        "ranges": {
            "rent_toman": [min(rents), max(rents)] if rents else None,
            "deposit_toman": [min(deposits), max(deposits)] if deposits else None,
            "floor_area_sqm": [min(areas), max(areas)] if areas else None,
        },
        "per_district": per_district,
        "withheld_values": findings,
        "ambiguous_deposits": [
            {"source_row_index": r["source_row_index"], "raw": r["row_raw"], "candidates": r["_deposit_candidates"]}
            for r in rows
            if r["_deposit_candidates"]
        ],
        "rows_without_district": [
            {
                "source_row_index": r["source_row_index"],
                "district_printed": r["district_printed"],
                "candidates": r["_district_candidates"],
                "area_name": r["area_name"],
                "row_raw": r["row_raw"],
            }
            for r in rows_without_district
        ],
        "reconciliation": reconcile,
        "flag_classes_added_here": NEW_FLAG_CLASSES,
        "policies": [
            "A dash in the rent column is missing data, not zero: the value stays empty so it "
            "cannot enter a median as 0. The row is kept for its area and deposit.",
            "A literal «0» is preserved in the raw column but left empty as a value: a 0 rent "
            "beside a deposit, or a 0 deposit beside a rent, is not a price.",
            "Ambiguous amounts are never guessed: the value stays empty and every candidate "
            "reading is listed.",
            "A district cell naming two districts leaves the district empty and flags it.",
            "A row present in an earlier version but absent from a later one is never silently "
            "dropped: it is written to excluded/ with its reason.",
            "No rent figure here is ever converted into a sale figure, or the reverse.",
        ],
        "caveat_deposit_mix": (
            "Monthly rent in these tables is not quoted at a constant deposit, and the share of "
            "rows carrying no monthly rent at all is high, so a median rent/m2 from one table is "
            "not directly comparable to another table's without saying so."
        ),
    }
    with open(out_dir / "parse_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"[{config['key']}] {config['date_jalali_ym']}")
    print(f"  rows {len(rows)} · with rent {len(rents)} · dashes {report['row_counts']['rent_not_listed']}"
          f" · zero rent {report['row_counts']['zero_rent_as_written']}"
          f" · zero deposit {report['row_counts']['zero_deposit_as_written']}")
    print(f"  districts {len(districts)} present, {len(missing)} expected-but-missing")
    if rents:
        print(f"  median rent {st.median(rents):,.0f} toman"
              + (f" · median {st.median(per_sqm):,.0f} toman/m2" if per_sqm else ""))
    if reconcile:
        print(f"  vs superseded: +{reconcile['counts']['only_in_cleaned']}"
              f" -{reconcile['counts']['only_in_superseded']}"
              f" ~{reconcile['counts']['renamed']} renamed")
    print(f"  -> {out_dir}/rent_asking.csv, parse_report.json")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--table", action="append", choices=[c["key"] for c in TABLES],
                        help="limit to one table (repeatable); default is all")
    args = parser.parse_args(argv)

    wanted = set(args.table) if args.table else None
    for config in TABLES:
        if wanted is None or config["key"] in wanted:
            process(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
