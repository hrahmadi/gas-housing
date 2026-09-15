#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse the owner-supplied Donya-e-Eqtesad rent-asking table (Tir 1404) into CSV.

Two input formats are supported and auto-detected, because the table arrived twice:

``.md``  a delimited markdown table (canonical input). Rows and columns are intact, so every
         cell is read directly and nothing is ambiguous.
``.txt`` the earlier *corrupted* chat paste, kept for audit: all rows were concatenated into one
         line and the numeric columns were glued together. For that file the parser enumerates
         every arithmetically admissible split of each glued digit run and accepts a row only
         when exactly one split exists; ambiguous rows are left empty with their candidate list.

Both formats produce the same schema, so the two transcriptions can be diffed. The
``source_format`` column records which one produced the row.

District handling: the district printed in the table is kept as ``district_number`` verbatim.
Because the two Donya-e-Eqtesad months group a few neighbourhoods differently, each row is also
cross-checked against the district mapping derived from the earlier tables in this repo and the
result is recorded in ``district_cross_check`` — the value is never overwritten by the check.

Usage:
    python3 scripts/parse_donyae_eqtesad.py
    python3 scripts/parse_donyae_eqtesad.py --input data/raw/donya-e-eqtesad_rent-asking_tir-1404.corrupt-paste.txt \
        --out data/raw/tehran_housing_market_data/sources/donya-e-eqtesad_1404-04/corrupt-paste
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "data" / "raw" / "donya-e-eqtesad_rent-asking_tir-1404.md"
DEFAULT_OUT = REPO_ROOT / "data" / "raw" / "tehran_housing_market_data" / "sources" / "donya-e-eqtesad_1404-04"

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
PERSIAN_LETTERS = r"\u0600-\u06ff"

#: column ranges used to decide whether a split of a glued digit run is admissible.
#: Only used for the corrupted paste; documented in the report.
COLUMN_RANGES: Dict[str, Tuple[float, float]] = {
    "building_age_years": (1, 45),
    "floor_area_sqm": (40, 260),
    "rent_toman_millions": (0, 120),
    "deposit_toman_millions": (100, 3000),
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

JALALI_MONTHS = (
    ("فروردین", 1), ("اردیبهشت", 2), ("خرداد", 3), ("تیر", 4), ("مرداد", 5), ("شهریور", 6),
    ("مهر", 7), ("آبان", 8), ("آذر", 9), ("دی", 10), ("بهمن", 11), ("اسفند", 12),
)


def load_corrections(path: Optional[Path]) -> Dict[int, Dict[str, Any]]:
    """Owner-supplied district corrections, keyed by source row index.

    A correction never overwrites the printed value: it fills ``district_number`` (the value to
    use) while ``district_printed`` keeps what the table said, and every correction carries its
    basis and who verified it. Corrections live in their own file so the raw paste stays raw.
    """
    corrections: Dict[int, Dict[str, Any]] = {}
    if not path or not path.exists():
        return corrections
    with open(path, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            index = str(row.get("source_row_index") or "").strip()
            if not index.isdigit():
                continue
            corrections[int(index)] = {
                "area_name": str(row.get("area_name") or "").strip(),
                "printed": int(row["district_printed"]) if str(row.get("district_printed") or "").strip().isdigit() else None,
                "verified": int(row["district_verified"]) if str(row.get("district_verified") or "").strip().isdigit() else None,
                "basis": str(row.get("basis") or "").strip(),
                "verified_by": str(row.get("verified_by") or "").strip(),
                "note": str(row.get("note") or "").strip(),
            }
    return corrections


def apply_correction(record: Dict[str, Any], correction: Optional[Dict[str, Any]]) -> List[str]:
    """Apply an owner correction if the printed district still matches what was verified."""
    if not correction:
        return []
    printed = record.get("district_printed")
    if correction["printed"] is not None and printed is not None and correction["printed"] != printed:
        return [f"correction_not_applied_row_mismatch:printed_{printed}_expected_{correction['printed']}"]
    record["district_number"] = correction["verified"]
    if correction["verified"] == printed:
        record["district_correction"] = "confirmed"
        return ["district_confirmed_by_owner_geographic_check"]
    record["district_correction"] = "corrected"
    return [f"district_corrected_by_owner:{printed}_to_{correction['verified']}"]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u200c", "\u200c").strip())


def millions_to_toman(value: Optional[float]) -> Optional[float]:
    return None if value is None else value * 1_000_000


# --------------------------------------------------------------------------------------
# The corrupted-paste reader needs an enumerated splitter
# --------------------------------------------------------------------------------------


def _ok(*values: Any) -> bool:
    """A field is never written with a leading zero in this table."""
    for value in values:
        text = str(value)
        if text.startswith("0") and len(text) > 1:
            return False
    return True


def _in_range(name: str, value: float) -> bool:
    low, high = COLUMN_RANGES[name]
    return low <= value <= high


def _left_options(pre: str, with_rent_tail: bool) -> List[Tuple[str, str, str]]:
    options: List[Tuple[str, str, str]] = []
    for i in (1, 2):
        for j in range(i + 2, i + 5):
            if j > len(pre):
                continue
            if with_rent_tail:
                for k in range(j + 1, min(j + 4, len(pre) + 1)):
                    options.append((pre[:i], pre[i:j], pre[j:k]))
            elif j == len(pre):
                options.append((pre[:i], pre[i:j], ""))
    return options


def enumerate_splits(tail: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Every admissible reading of one glued row tail from the corrupted paste."""
    candidates: List[Dict[str, Any]] = []

    def add(age: str, area: str, deposit: str, rent: Optional[float],
            rent_min: Optional[float] = None, rent_max: Optional[float] = None) -> None:
        if not (age.isdigit() and area.isdigit() and deposit.isdigit()) or not _ok(age, area, deposit):
            return
        age_v, area_v, deposit_v = int(age), int(area), int(deposit)
        if not (_in_range("building_age_years", age_v) and _in_range("floor_area_sqm", area_v)
                and _in_range("deposit_toman_millions", deposit_v)):
            return
        if rent is not None and not _in_range("rent_toman_millions", rent):
            return
        if rent_min is not None and not (_in_range("rent_toman_millions", rent_min)
                                         and _in_range("rent_toman_millions", rent_max)):
            return
        candidates.append({"age": age_v, "area": area_v, "rent": rent,
                           "rent_min": rent_min, "rent_max": rent_max, "deposit": deposit_v})

    slash = re.match(r"^(\d+)\s*/\s*(.+)$", tail)
    if slash:
        pre, right_all = slash.group(1), slash.group(2).replace(" ", "")
        right_options: List[Tuple[float, str]] = []
        for cut in range(1, len(right_all)):
            rent_text, deposit_text = right_all[:cut], right_all[cut:]
            if not deposit_text.isdigit() or not re.fullmatch(r"\d+(\.\d+)?", rent_text):
                continue
            if _ok(rent_text, deposit_text):
                right_options.append((float(rent_text), deposit_text))
        for age, area, rent_left in _left_options(pre, with_rent_tail=True):
            if not rent_left:
                continue
            for rent_right, deposit in right_options:
                add(age, area, deposit, None, float(rent_left), rent_right)
        return candidates, ("range" if candidates else None)

    if "." in tail:
        dot = tail.index(".")
        before, after = tail[:dot], tail[dot + 1:].replace(" ", "")
        for rent_len in (1, 2, 3):
            if rent_len > len(before):
                continue
            pre, rent_int = before[: len(before) - rent_len], before[len(before) - rent_len:]
            for fraction_len in (1, 2):
                if fraction_len > len(after):
                    continue
                fraction, deposit = after[:fraction_len], after[fraction_len:]
                for age, area, rent_left in _left_options(pre, with_rent_tail=False):
                    if rent_left:
                        continue
                    add(age, area, deposit, float(f"{rent_int}.{fraction}"))
        return candidates, ("decimal" if candidates else None)

    dash = re.match(r"^(\d+)-(\d+)$", tail)
    if dash:
        pre, post = dash.groups()
        for age, area, rent_left in _left_options(pre, with_rent_tail=False):
            add(age, area, post, None)
        return candidates, ("missing" if candidates else None)

    digits = re.sub(r"\D", "", tail)
    for i in (1, 2):
        for j in (i + 2, i + 3, i + 4):
            for k in (j + 1, j + 2, j + 3, j + 4):
                if k >= len(digits) + 1:
                    continue
                age, area, rent, deposit = digits[:i], digits[i:j], digits[j:k], digits[k:]
                if deposit and rent.isdigit():
                    add(age, area, deposit, float(rent))
    return candidates, None


# --------------------------------------------------------------------------------------
# District cross-check
# --------------------------------------------------------------------------------------


def load_sibling_district_index(repo_root: Path) -> Dict[str, int]:
    """Neighbourhood -> district from the earlier tables in this repo.

    Geography does not change month to month; a name mapped to two different districts upstream
    is dropped as ambiguous.
    """
    index: Dict[str, int] = {}
    ambiguous: set = set()
    observations = repo_root / "data" / "raw" / "tehran_housing_market_data" / "observations" / "rent_observations.csv"
    if not observations.exists():
        return index
    with open(observations, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            district = str(row.get("district_number") or "").strip()
            name = str(row.get("area_name") or "")
            if not district.isdigit() or not name:
                continue
            segment = re.split(r"[،,\-–]", name)[0].strip()
            if not segment:
                continue
            if segment in index and index[segment] != int(district):
                ambiguous.add(segment)
            else:
                index.setdefault(segment, int(district))
    for segment in ambiguous:
        index.pop(segment, None)
    return index


def cross_check_district(name: str, printed: Optional[int], index: Dict[str, int]) -> Tuple[str, Optional[str]]:
    """Compare the printed district with the repo's mapping. Never changes the printed value."""
    segment = re.split(r"[،,\-–]", name)[0].strip()
    if segment not in index:
        return "unchecked", None
    expected = index[segment]
    if printed is None:
        return "unchecked", f"sibling_table_says:{expected}"
    if printed == expected:
        return "match", None
    return "conflict", f"district_print_{printed}_vs_sibling_{expected}"


# --------------------------------------------------------------------------------------
# Readers
# --------------------------------------------------------------------------------------


def parse_meta(lines: Iterable[str]) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for line in lines:
        plain = line.replace("*", "").strip()
        for key, label in (("عنوان", "title"), ("منبع", "outlet_raw"), ("تاریخ", "date_raw"), ("نکته", "note")):
            if plain.startswith(f"{key}:"):
                meta[label] = normalise(plain.split(":", 1)[1])
    return meta


def iter_markdown_rows(lines: Iterable[str]) -> List[Dict[str, Any]]:
    """Delimited markdown table: every cell is read directly."""
    rows: List[Dict[str, Any]] = []
    header_seen = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if header_seen and rows:
                break
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", cell or "-") for cell in cells):
            continue
        if not header_seen:
            header_seen = True
            continue
        rows.append(
            {
                "row_raw": stripped,
                "cells": cells,
            }
        )
    return rows


def split_markdown_cells(cells: List[str]) -> Dict[str, Any]:
    district_text = cells[0].replace("*", "").strip() if cells else ""
    district = int(district_text) if district_text.isdigit() else None
    return {
        "district": district,
        "district_marker": district_text,
        "name": normalise(cells[1]) if len(cells) > 1 else "",
        "age_text": cells[2] if len(cells) > 2 else "",
        "area_text": cells[3] if len(cells) > 3 else "",
        "rent_text": cells[4] if len(cells) > 4 else "",
        "deposit_text": cells[5] if len(cells) > 5 else "",
    }


def iter_paste_rows(data_line: str) -> List[Dict[str, Any]]:
    """Corrupted paste: recover row boundaries, then enumerate splits of the glued digits."""
    row_re = re.compile(r"(?:(?<=[0-9۰-۹])|^)([۰-۹]{1,2}\*?|\*[۰-۹]{1,2})(?=[" + PERSIAN_LETTERS + r"])")
    starts = [(m.start(), m.group(1).translate(PERSIAN_DIGITS)) for m in row_re.finditer(data_line)]
    rows: List[Dict[str, Any]] = []
    for i, (position, marker) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(data_line)
        raw = data_line[position:end]
        body = re.sub(r"^[\*۰-۹]+", "", raw)
        match = re.match(r"^([" + PERSIAN_LETTERS + r"\s\-\u200c]+)(.*)$", body, re.S)
        rows.append(
            {
                "row_raw": raw,
                "marker": marker,
                "name": normalise(match.group(1)) if match else "",
                "tail": re.sub(r"\s+", " ", match.group(2)).strip() if match else "",
                "has_name": bool(match),
            }
        )
    return rows


# --------------------------------------------------------------------------------------
# Record building
# --------------------------------------------------------------------------------------


def base_record(meta: Dict[str, str], date_ym: Optional[str], input_path: Path, source_format: str) -> Dict[str, Any]:
    return {
        "source_format": source_format,
        "district_number": None,
        "district_printed": None,
        "district_correction": "",
        "district_number_source": "",
        "district_cross_check": "",
        "district_marker_raw": "",
        "area_name": "",
        "row_raw": "",
        "flag_amount_ambiguous": False,
        "issue_classes": "",
        "notes": "",
        "source_file": display_path(input_path),
        "outlet": "دنیای اقتصاد (Donya-e-Eqtesad)",
        "outlet_evidence": "owner-supplied header line 'منبع: دنیای اقتصاد (Donya-e-Eqtesad)'",
        "evidence_tier": "C",
        "verification": "unverified_owner_transcription",
        "date_jalali_raw": meta.get("date_raw", ""),
        "date_jalali_ym": date_ym,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--corrections", default=str(DEFAULT_INPUT.with_suffix(".corrections.csv")),
                        help="owner corrections applied to district_number (printed value is kept)")
    args = parser.parse_args(argv)

    input_path = Path(args.input).resolve()
    raw_bytes = input_path.read_bytes()
    lines = raw_bytes.decode("utf-8").split("\n")
    meta = parse_meta(lines)
    source_format = "markdown_table" if any(line.strip().startswith("|") for line in lines) else "corrupt_paste"

    date_ym = None
    for name, month in JALALI_MONTHS:
        if name in meta.get("date_raw", ""):
            year = re.search(r"1[34]\d{2}", meta.get("date_raw", ""))
            if year:
                date_ym = f"{year.group(0)}-{month:02d}"
            break

    sibling_index = load_sibling_district_index(REPO_ROOT)
    corrections = load_corrections(Path(args.corrections))
    records: List[Dict[str, Any]] = []
    ambiguous: List[Dict[str, Any]] = []
    unparsed: List[Dict[str, Any]] = []
    cross_conflicts: List[Dict[str, Any]] = []

    if source_format == "markdown_table":
        for index, row in enumerate(iter_markdown_rows(lines), start=1):
            cells = split_markdown_cells(row["cells"])
            record = base_record(meta, date_ym, input_path, source_format)
            record["source_row_index"] = index
            record["row_raw"] = row["row_raw"]
            record["district_marker_raw"] = cells["district_marker"]
            record["area_name"] = cells["name"]
            notes: List[str] = []
            classes: List[str] = []

            record["building_age_years"] = int(cells["age_text"]) if cells["age_text"].isdigit() else None
            record["floor_area_sqm"] = int(cells["area_text"]) if cells["area_text"].isdigit() else None
            record["deposit_toman"] = millions_to_toman(float(cells["deposit_text"])) if re.fullmatch(r"\d+(\.\d+)?", cells["deposit_text"]) else None
            record["rent_raw"] = cells["rent_text"]

            rent_text = cells["rent_text"].replace(" ", "")
            range_match = re.fullmatch(r"(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)", rent_text)
            if range_match:
                record["rent_toman_min"] = millions_to_toman(float(range_match.group(1)))
                record["rent_toman_max"] = millions_to_toman(float(range_match.group(2)))
                notes.append("rent_range_as_written")
                classes.append("notation")
            elif rent_text == "-":
                notes.append("rent_missing_as_written")
                classes.append("notation")
            elif re.fullmatch(r"\d+(\.\d+)?", rent_text):
                record["rent_toman"] = millions_to_toman(float(rent_text))
                if float(rent_text) == 0:
                    notes.append("zero_rent_as_written")
                    classes.append("source_ambiguity")
                    record["flag_amount_ambiguous"] = True
            else:
                notes.append("rent_unparsed")
                classes.append("data_error")
                unparsed.append({"source_row_index": index, "row_raw": row["row_raw"], "rent_text": cells["rent_text"]})

            record["district_number"] = cells["district"]
            record["district_number_source"] = "print"
            record["district_printed"] = cells["district"]
            record["district_correction"] = ""
            for note in apply_correction(record, corrections.get(index)):
                notes.append(note)
                classes.append("notation")
            if record["district_correction"]:
                record["district_number_source"] = "owner_geographic_verification"
            check, detail = cross_check_district(cells["name"], record["district_number"], sibling_index)
            record["district_cross_check"] = check
            if detail:
                notes.append(detail)
            if check == "conflict":
                classes.append("source_ambiguity")
                cross_conflicts.append(
                    {
                        "source_row_index": index,
                        "area_name": cells["name"],
                        "district_printed": cells["district"],
                        "district_used": record["district_number"],
                        "sibling_table_district": sibling_index[re.split(r"[،,\-–]", cells["name"])[0].strip()],
                    }
                )

            record["notes"] = "; ".join(dict.fromkeys(notes))
            record["issue_classes"] = ";".join(sorted({c for c in classes if c}))
            records.append(record)

    else:
        data_line = next((line for line in lines if "فرمانیه" in line), "")
        if not data_line:
            print("no data line found", file=sys.stderr)
            return 1
        blocks: List[Dict[str, Any]] = []
        for row in iter_paste_rows(data_line):
            if blocks and blocks[-1]["marker"] == row["marker"]:
                blocks[-1]["rows"].append(row)
            else:
                blocks.append({"marker": row["marker"], "clean": row["marker"].isdigit(), "rows": [row]})
        previous_anchor = 0
        for position, block in enumerate(blocks):
            if block["clean"]:
                block["district"] = int(block["marker"])
                previous_anchor = block["district"]
                continue
            next_anchor = next((int(b["marker"]) for b in blocks[position + 1:] if b["clean"]), previous_anchor + 1)
            missing = [d for d in range(previous_anchor + 1, next_anchor) if d not in {previous_anchor, next_anchor}]
            block["district"] = missing[0] if len(missing) == 1 else None

        index = 0
        for block in blocks:
            for row in block["rows"]:
                index += 1
                record = base_record(meta, date_ym, input_path, source_format)
                record["source_row_index"] = index
                record["row_raw"] = row["row_raw"]
                record["district_marker_raw"] = row["marker"]
                record["area_name"] = row["name"]
                notes: List[str] = []
                classes: List[str] = []
                if not block["clean"]:
                    notes.append(f"district_marker_corrupt:{row['marker']}")
                    classes.append("notation" if block["district"] else "source_ambiguity")
                if not row["has_name"]:
                    notes.append("row_text_unparsed")
                    classes.append("data_error")
                    unparsed.append({"source_row_index": index, "row_raw": row["row_raw"], "reason": "no name+digits split"})
                    record.update({"notes": "; ".join(notes), "issue_classes": ";".join(sorted(set(classes))), "flag_amount_ambiguous": True})
                    records.append(record)
                    continue

                candidates, rent_kind = enumerate_splits(row["tail"])
                stripped = 0
                while not candidates and stripped < 2:
                    stripped += 1
                    candidates, rent_kind = enumerate_splits(row["tail"][:-stripped].rstrip())
                if stripped:
                    notes.append(f"trailing_digits_stripped:{stripped}")

                if len(candidates) == 1:
                    chosen = candidates[0]
                    record["building_age_years"] = chosen["age"]
                    record["floor_area_sqm"] = chosen["area"]
                    record["deposit_toman"] = millions_to_toman(chosen["deposit"])
                    if chosen["rent"] is not None:
                        record["rent_toman"] = millions_to_toman(chosen["rent"])
                    elif chosen["rent_min"] is not None:
                        record["rent_toman_min"] = millions_to_toman(chosen["rent_min"])
                        record["rent_toman_max"] = millions_to_toman(chosen["rent_max"])
                        notes.append("rent_range_as_written")
                        classes.append("notation")
                    elif rent_kind == "missing":
                        notes.append("rent_missing_as_written")
                        classes.append("notation")
                elif len(candidates) > 1:
                    classes.append("source_ambiguity")
                    record["flag_amount_ambiguous"] = True
                    notes.append(f"ambiguous_column_split:{len(candidates)}_candidates")
                    ambiguous.append({"source_row_index": index, "area_name": record["area_name"],
                                      "row_raw": row["row_raw"], "candidates": candidates})
                else:
                    classes.append("source_ambiguity")
                    record["flag_amount_ambiguous"] = True
                    notes.append("column_split_not_recoverable")
                    unparsed.append({"source_row_index": index, "row_raw": row["row_raw"], "tail": row["tail"]})

                record["rent_raw"] = row["tail"]
                record["district_number"] = block["district"]
                record["district_printed"] = block["district"]
                record["district_correction"] = ""
                record["district_number_source"] = "marker" if block["clean"] else ("gap_fill" if block["district"] else "unknown")
                for note in apply_correction(record, corrections.get(index)):
                    notes.append(note)
                    classes.append("notation")
                if record["district_correction"]:
                    record["district_number_source"] = "owner_geographic_verification"
                check, detail = cross_check_district(record["area_name"], record["district_number"], sibling_index)
                record["district_cross_check"] = check
                if detail:
                    notes.append(detail)
                if check == "conflict":
                    classes.append("source_ambiguity")
                    cross_conflicts.append({"source_row_index": index, "area_name": record["area_name"],
                                            "district_printed": block["district"],
                                            "district_used": record["district_number"],
                                            "sibling_table_district": sibling_index[re.split(r"[،,\-–]", record["area_name"])[0].strip()]})
                record["notes"] = "; ".join(dict.fromkeys(notes))
                record["issue_classes"] = ";".join(sorted({c for c in classes if c}))
                records.append(record)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "rent_asking.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FIELDS), lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({key: ("" if record.get(key) is None else record.get(key)) for key in FIELDS})

    range_rows = sum(1 for r in records if r.get("rent_toman_min"))
    zero_rows = sum(1 for r in records if "zero_rent_as_written" in str(r.get("notes")))
    missing_rows = sum(1 for r in records if "rent_missing_as_written" in str(r.get("notes")))

    report = {
        "input": {
            "path": display_path(input_path),
            "bytes": len(raw_bytes),
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "format": source_format,
        },
        "header_metadata": meta,
        "date_jalali_ym": date_ym,
        "outlet": "دنیای اقتصاد (Donya-e-Eqtesad)",
        "outlet_evidence": "owner-supplied 'منبع' line; the file itself names no outlet beyond that",
        "row_counts": {
            "rows": len(records),
            "fully_parsed": sum(1 for r in records if not r["flag_amount_ambiguous"]),
            "rent_range_rows": range_rows,
            "zero_rent_rows": zero_rows,
            "rent_missing_rows": missing_rows,
            "ambiguous_split": len(ambiguous),
            "unparsed": len(unparsed),
            "district_markers_corrupt": sum(1 for r in records if "district_marker_corrupt" in str(r["notes"])),
        },
        "district_cross_check": {
            "match": sum(1 for r in records if r["district_cross_check"] == "match"),
            "conflict": sum(1 for r in records if r["district_cross_check"] == "conflict"),
            "unchecked": sum(1 for r in records if r["district_cross_check"] == "unchecked"),
            "note": (
                "The printed district is never overwritten; district_number carries the value to "
                "use (printed, or owner-corrected where a correction file exists) and "
                "district_printed carries what the table said. A conflict is measured against "
                "district_number."
            ),
            "conflicting_rows": cross_conflicts,
        },
        "district_corrections": {
            "file": display_path(Path(args.corrections)) if Path(args.corrections).exists() else None,
            "applied": sum(1 for r in records if r["district_correction"] == "corrected"),
            "confirmed": sum(1 for r in records if r["district_correction"] == "confirmed"),
            "note": (
                "Corrections come from the owner (geographic verification) and live in their own "
                "file, so the raw transcription stays untouched. Both the printed and the "
                "corrected value are kept on every row."
            ),
        },
        "split_constraints": ({k: list(v) for k, v in COLUMN_RANGES.items()} if source_format == "corrupt_paste" else {}),
        "ambiguous_rows": ambiguous,
        "unparsed_rows": unparsed,
        "known_defects_of_the_corrupt_paste": (
            [
                "42 district markers corrupted ('۱*'/'۲*' where 11-20 should be)",
                "numeric columns concatenated with no delimiter: the rent/deposit boundary is "
                "arithmetically ambiguous in many rows",
            ]
            if source_format == "corrupt_paste"
            else []
        ),
    }
    with open(out_dir / "parse_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    counts = report["row_counts"]
    print(f"format        : {source_format}")
    print(f"rows          : {counts['rows']}")
    print(f"fully parsed  : {counts['fully_parsed']}")
    print(f"rent ranges   : {counts['rent_range_rows']} | zero rents: {counts['zero_rent_rows']} | missing rent: {counts['rent_missing_rows']}")
    print(f"ambiguous     : {counts['ambiguous_split']} | unparsed: {counts['unparsed']}")
    print(f"district check: {report['district_cross_check']['match']} match, "
          f"{report['district_cross_check']['conflict']} conflict, {report['district_cross_check']['unchecked']} unchecked")
    print(f"corrections   : {report['district_corrections']['applied']} applied, "
          f"{report['district_corrections']['confirmed']} confirmed from {report['district_corrections']['file']}")
    print(f"output        : {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
