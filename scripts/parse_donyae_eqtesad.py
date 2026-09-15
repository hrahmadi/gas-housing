#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse the owner-supplied Donya-e-Eqtesad rent table (Tir 1404) into CSV.

Input: ``data/raw/donya-e-eqtesad_rent-asking_tir-1404.txt`` — a **chat paste**, not a
delimited export. Two consequences drive this parser:

1. **Row boundaries are gone.** Rows are concatenated into one long line; a row starts with a
   district marker (1–2 digits) immediately followed by a Persian letter, so that transition is
   the only reliable boundary signal.
2. **Column boundaries are gone.** Each row is ``<district><name><age><area><rent><deposit>``
   with the four numeric columns glued together. Only a few tokens survive: an ``a / b`` rent
   range, a decimal rent (``17.5``), or a ``-`` for a missing rent.

The parser therefore *enumerates* every arithmetically possible split of the digit run under
explicit range constraints, and accepts a row only when exactly one split is possible:

* a field written with a leading zero is rejected (nobody writes ``01500`` for 1500),
* ranges used for splitting are documented in ``parse_report.json`` and come from the observed
  values of this table plus its sibling table (Aban 1404, dataset 3 of the RTF archive).

Everything ambiguous is left empty and flagged with its candidate list, never guessed. The
verbatim row text is kept in ``row_raw`` on every row, so a human can always finish the job
by hand or re-export the table with delimiters.

District markers may be corrupted in the paste (``۱*`` where 11–20 should be). A corrupted
marker block is resolved by gap-filling between the clean anchors around it and flagged
``district_inferred_by_gap_fill``; unresolved districts stay empty.

Usage:
    python3 scripts/parse_donyae_eqtesad.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "data" / "raw" / "donya-e-eqtesad_rent-asking_tir-1404.txt"
DEFAULT_OUT = REPO_ROOT / "data" / "raw" / "tehran_housing_market_data" / "sources" / "donya-e-eqtesad_1404-04"

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
PERSIAN_LETTERS = r"\u0600-\u06ff"

#: column ranges used to decide whether a split of the glued digit run is admissible.
#: Documented in the report; derived from this table + the sibling Aban 1404 table.
COLUMN_RANGES: Dict[str, Tuple[float, float]] = {
    "building_age_years": (1, 45),
    "floor_area_sqm": (40, 260),
    "rent_toman_millions": (0, 120),
    "deposit_toman_millions": (100, 3000),
}

FIELDS: Tuple[str, ...] = (
    "source_row_index",
    "district_number",
    "district_marker_raw",
    "district_number_source",
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


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u200c", "\u200c").strip())


def millions_to_toman(value: Optional[float]) -> Optional[float]:
    return None if value is None else value * 1_000_000


def _ok(*values: Any) -> bool:
    """Field values must be inside range and never written with a leading zero."""
    for value in values:
        text = str(value)
        if text.startswith("0") and len(text) > 1:
            return False
    return True


def _in_range(name: str, value: float) -> bool:
    low, high = COLUMN_RANGES[name]
    return low <= value <= high


def _left_options(pre: str, with_rent_tail: bool) -> List[Tuple[str, str, str]]:
    """Split the digits that precede the rent token into (age, area, rent_left)."""
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


def enumerate_splits(tail: str) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], str]:
    """Enumerate every admissible reading of one glued row tail.

    Returns ``(candidates, rent_info, rent_raw)`` where each candidate is a dict with
    ``age``, ``area``, ``rent``/``rent_min``/``rent_max`` and ``deposit`` (values in the units
    written in the table: years, m², million toman).

    Four shapes are handled, because only these tokens survive the paste:

    ``10706 / 15.5500``   rent range, left operand glued to the area digits
    ``57517.5600``        decimal rent, integer part glued to the area digits
    ``873-800``           rent written as ``-``
    ``6130501500``        everything glued: age, area, rent, deposit

    Splits are enumerated explicitly rather than by a greedy regex, because a greedy match on
    ``10706 / 15.5500`` reads the deposit as ``0`` and loses the row.
    """
    candidates: List[Dict[str, Any]] = []

    def add(age: str, area: str, deposit: str, rent: Optional[float],
            rent_min: Optional[float] = None, rent_max: Optional[float] = None) -> None:
        if not (age.isdigit() and area.isdigit() and deposit.isdigit()):
            return
        if not _ok(age, area, deposit):
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

    # --- an «a / b» rent range, e.g. «6 / 15.5» glued in front of the deposit
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
        return candidates, ({"kind": "range"} if candidates else None), tail

    # --- a decimal rent, e.g. «17.5» glued in front of the deposit
    dot = re.search(r"\.", tail)
    if dot:
        before, after = tail[: dot.start()], tail[dot.end() :].replace(" ", "")
        for rent_len in (1, 2, 3):
            if rent_len > len(before):
                continue
            pre, rent_int = before[: len(before) - rent_len], before[len(before) - rent_len :]
            for fraction_len in (1, 2):
                if fraction_len > len(after):
                    continue
                fraction, deposit = after[:fraction_len], after[fraction_len:]
                rent_value = float(f"{rent_int}.{fraction}")
                for age, area, rent_left in _left_options(pre, with_rent_tail=False):
                    if rent_left:
                        continue
                    add(age, area, deposit, rent_value)
        return candidates, ({"kind": "decimal"} if candidates else None), tail

    # --- a rent written as «-»
    dash = re.match(r"^(\d+)-(\d+)$", tail)
    if dash:
        pre, post = dash.groups()
        for age, area, rent_left in _left_options(pre, with_rent_tail=False):
            add(age, area, post, None)
        return candidates, ({"kind": "missing"} if candidates else None), tail

    # --- everything glued: age, area, rent, deposit
    digits = re.sub(r"\D", "", tail)
    for i in (1, 2):
        for j in (i + 2, i + 3, i + 4):
            for k in (j + 1, j + 2, j + 3, j + 4):
                if k >= len(digits) + 1:
                    continue
                age, area, rent, deposit = digits[:i], digits[i:j], digits[j:k], digits[k:]
                if deposit and rent.isdigit():
                    add(age, area, deposit, float(rent))
    return candidates, None, tail


def load_sibling_district_index(repo_root: Path) -> Dict[str, int]:
    """Neighbourhood -> district, from the earlier tables in this repo that carry a district.

    Geography does not change month to month, so ``هاشمی`` is district 11 whatever month a table
    covers. Dataset 2 (districts 8/13/14) and dataset 3 (all 22 districts) of the RTF archive
    provide the mapping. A name that maps to more than one district is dropped as ambiguous.
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


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    raw_bytes = input_path.read_bytes()
    lines = raw_bytes.decode("utf-8").split("\n")

    meta: Dict[str, str] = {}
    for line in lines:
        for key, label in (("عنوان", "title"), ("منبع", "outlet_raw"), ("تاریخ", "date_raw"), ("نکته", "note")):
            if line.startswith(f"{key}:"):
                meta[label] = normalise(line.split(":", 1)[1])
    header_line = next((l for l in lines if l.strip().startswith("منطقه")), "")
    data_line = next((l for l in lines if "فرمانیه" in l), "")
    if not data_line:
        print("no data line found", file=sys.stderr)
        return 1

    date_text, date_ym = meta.get("date_raw", ""), None
    for name, month in (("فروردین", 1), ("اردیبهشت", 2), ("خرداد", 3), ("تیر", 4), ("مرداد", 5), ("شهریور", 6),
                        ("مهر", 7), ("آبان", 8), ("آذر", 9), ("دی", 10), ("بهمن", 11), ("اسفند", 12)):
        if name in date_text:
            year = re.search(r"1[34]\d{2}", date_text)
            if year:
                date_ym = f"{year.group(0)}-{month:02d}"
            break

    # ---- row boundaries: a district marker (digits, maybe corrupted with '*') followed by a letter
    row_re = re.compile(r"(?:(?<=[0-9۰-۹])|^)([۰-۹]{1,2}\*?|\*[۰-۹]{1,2})(?=[" + PERSIAN_LETTERS + r"])")
    starts = [(m.start(), m.group(1).translate(PERSIAN_DIGITS)) for m in row_re.finditer(data_line)]
    rows_raw = [
        (marker, data_line[pos : (starts[i + 1][0] if i + 1 < len(starts) else len(data_line))])
        for i, (pos, marker) in enumerate(starts)
    ]

    # ---- district markers: clean ones are anchors, corrupted blocks are gap-filled
    blocks: List[Dict[str, Any]] = []
    for marker, raw in rows_raw:
        if blocks and blocks[-1]["marker"] == marker:
            blocks[-1]["rows"].append(raw)
        else:
            blocks.append({"marker": marker, "clean": marker.isdigit(), "rows": [raw]})
    previous_anchor = 0
    for index, block in enumerate(blocks):
        if block["clean"]:
            block["district"] = int(block["marker"])
            previous_anchor = block["district"]
            continue
        next_anchor = next((int(b["marker"]) for b in blocks[index + 1 :] if b["clean"]), previous_anchor + 1)
        missing = [d for d in range(previous_anchor + 1, next_anchor) if d not in {previous_anchor, next_anchor}]
        block["district"] = missing[0] if len(missing) == 1 else None

    name_re = re.compile(r"^([" + PERSIAN_LETTERS + r"\s\-\u200c]+)(.*)$", re.S)
    sibling_index = load_sibling_district_index(REPO_ROOT)
    records: List[Dict[str, Any]] = []
    ambiguous: List[Dict[str, Any]] = []
    unparsed: List[Dict[str, Any]] = []
    index = 0

    for block in blocks:
        for raw_row in block["rows"]:
            index += 1
            body = raw_row[len(block["marker"]) :] if raw_row.startswith(block["marker"]) else raw_row
            body = re.sub(r"^[\*۰-۹]+", "", body)
            match = name_re.match(body)
            notes: List[str] = []
            classes: List[str] = []
            record: Dict[str, Any] = {
                "source_row_index": index,
                "district_number": block["district"],
                "district_marker_raw": block["marker"],
                "district_number_source": "marker" if block["clean"] else ("gap_fill" if block["district"] else "unknown"),
                "area_name": normalise(match.group(1)) if match else "",
                "flag_amount_ambiguous": False,
                "issue_classes": "",
                "notes": "",
                "source_file": str(input_path.relative_to(REPO_ROOT)),
                "outlet": "دنیای اقتصاد (Donya-e-Eqtesad)",
                "outlet_evidence": "owner-supplied header line 'منبع: دنیای اقتصاد (Donya-e-Eqtesad)'",
                "evidence_tier": "C",
                "verification": "unverified_owner_paste",
                "date_jalali_raw": date_text,
                "date_jalali_ym": date_ym,
            }
            if not block["clean"]:
                notes.append(f"district_marker_corrupt:{block['marker']}")
                classes.append("notation" if block["district"] else "source_ambiguity")

            # the pasted markers disagree with the earlier tables for some rows, so the district
            # is taken from a name match where one exists, and the marker is kept as evidence
            segment = re.split(r"[،,\-–]", record["area_name"])[0].strip()
            if segment in sibling_index:
                verified = sibling_index[segment]
                if block["district"] is not None and block["district"] != verified:
                    notes.append(f"district_marker_disagrees_with_sibling_table:{block['district']}_vs_{verified}")
                    classes.append("source_ambiguity")
                record["district_number"] = verified
                record["district_number_source"] = "sibling_table_name_match"
            elif block["district"] is None:
                notes.append("district_unresolved")
                classes.append("source_ambiguity")

            record["row_raw"] = raw_row

            if not match:
                notes.append("row_text_unparsed")
                classes.append("data_error")
                unparsed.append({"source_row_index": index, "row_raw": raw_row, "reason": "no name+digits split"})
                record.update({"notes": "; ".join(notes), "issue_classes": ";".join(sorted(set(classes))), "flag_amount_ambiguous": True})
                records.append(record)
                continue

            tail = re.sub(r"\s+", " ", match.group(2)).strip()
            candidates, rent_info, rent_raw = enumerate_splits(tail)
            stripped = 0
            working_tail = tail
            while not candidates and stripped < 2:
                # a row boundary can leave a stray digit at the end (e.g. the next row's marker)
                working_tail = working_tail[:-1].rstrip()
                stripped += 1
                candidates, rent_info, rent_raw = enumerate_splits(working_tail)
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
                elif rent_info and rent_info["kind"] == "missing":
                    notes.append("rent_missing_as_written")
                    classes.append("notation")
            elif len(candidates) > 1:
                classes.append("source_ambiguity")
                record["flag_amount_ambiguous"] = True
                notes.append(f"ambiguous_column_split:{len(candidates)}_candidates")
                ambiguous.append(
                    {
                        "source_row_index": index,
                        "district_number": block["district"],
                        "area_name": record["area_name"],
                        "row_raw": raw_row,
                        "tail": working_tail,
                        "candidates": candidates,
                        "note": "the rent/deposit (or area/rent) boundary is not recoverable from the paste",
                    }
                )
            else:
                classes.append("source_ambiguity")
                record["flag_amount_ambiguous"] = True
                notes.append("column_split_not_recoverable")
                unparsed.append({"source_row_index": index, "row_raw": raw_row, "tail": working_tail})

            record["rent_raw"] = rent_raw
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

    report = {
        "input": {
            "path": str(input_path.relative_to(REPO_ROOT)),
            "bytes": len(raw_bytes),
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "format": "chat paste: one long line, row and column boundaries lost",
        },
        "header_metadata": meta,
        "column_header_line": header_line,
        "date_jalali_ym": date_ym,
        "outlet": "دنیای اقتصاد (Donya-e-Eqtesad)",
        "outlet_evidence": "owner-supplied 'منبع' line; the file itself names no outlet",
        "row_counts": {
            "rows_detected": len(records),
            "fully_parsed": sum(1 for r in records if not r["flag_amount_ambiguous"]),
            "ambiguous_split": len(ambiguous),
            "unparsed": len(unparsed),
            "district_markers_corrupt": sum(1 for r in records if "district_marker_corrupt" in r["notes"]),
            "district_inferred_by_gap_fill": sum(1 for r in records if r["district_number_source"] == "gap_fill"),
        },
        "split_constraints": {k: list(v) for k, v in COLUMN_RANGES.items()},
        "split_rules": [
            "a field written with a leading zero is rejected ('01500' is never written for 1500)",
            "an 'a / b' rent range, a decimal rent (17.5) and a '-' are preserved tokens, not digits",
            "a row is accepted only when exactly one admissible split exists",
        ],
        "ambiguous_rows": ambiguous,
        "unparsed_rows": unparsed,
        "known_defects_of_the_input": [
            "the district marker is corrupted for 42 rows ('۱*'/'۲*' where 11-20 should be); districts were gap-filled between clean anchors and flagged",
            "the numeric columns are concatenated with no delimiter, so the rent/deposit boundary is arithmetically ambiguous in many rows",
            "re-exporting the table with delimiters (or supplying the original PDF/Excel) would make every row unambiguous",
        ],
    }
    with open(out_dir / "parse_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    counts = report["row_counts"]
    print(f"rows detected : {counts['rows_detected']}")
    print(f"fully parsed  : {counts['fully_parsed']}")
    print(f"ambiguous     : {counts['ambiguous_split']} (candidates recorded, values left empty)")
    print(f"unparsed      : {counts['unparsed']}")
    print(f"corrupt markers: {counts['district_markers_corrupt']} (gap-filled: {counts['district_inferred_by_gap_fill']})")
    print(f"output        : {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
