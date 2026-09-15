#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse and clean ``data/raw/rent-data-donyaeghtesad.rtf``.

The RTF is not a single newspaper table: it is a transcript dump of eight different
datasets (rent listings, sale listings, district averages) in mixed units and
timeframes, one of which is explicitly *simulated* research. Cleaning therefore means:

* extract the text from the RTF with the standard library (no ``textutil`` dependency),
* split it back into its source tables and keep them separate (the transcript itself
  warns against combining timeframes),
* normalise numbers (Persian digits, «میلیون/میلیارد/هزار», «الی» ranges, «رایگان»,
  Persian decimal slashes, million-rial columns) into explicit toman values,
* never invent a value: missing stays empty, ambiguous values are parsed but flagged,
* record provenance and an anomaly list in ``parse_report.json``.

Outputs (next to the input, in ``data/raw/rent-data-donyaeghtesad/``):

    rent_observations.csv     one row per rent/deposit observation (datasets 2,3,5,7,8)
    sale_observations.csv     one row per sale-price observation (datasets 1,4)
    district_sale_stats.csv   dataset 6 (22 districts + city total, Aban 1402)
    parse_report.json         provenance, counts, unit conversions, anomalies, warnings
    README.md                 how to read these files and what not to claim

Usage:
    python3 scripts/parse_rent_rtf.py                # write the outputs
    python3 scripts/parse_rent_rtf.py --dump-text    # print the extracted text only
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "data" / "raw" / "rent-data-donyaeghtesad.rtf"
DEFAULT_OUTDIR = REPO_ROOT / "data" / "raw" / "rent-data-donyaeghtesad"

# --------------------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------------------

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
MISSING_TOKENS = {"", "-", "–", "—", "‑", "n/a", "N/A", "؟", "?"}

JALALI_MONTHS = {
    "فروردین": 1,
    "اردیبهشت": 2,
    "خرداد": 3,
    "تیر": 4,
    "مرداد": 5,
    "شهریور": 6,
    "مهر": 7,
    "آبان": 8,
    "آذر": 9,
    "دی": 10,
    "بهمن": 11,
    "اسفند": 12,
}

PERSIAN_NUMBER_WORDS = {
    "یک": 1,
    "دو": 2,
    "سه": 3,
    "چهار": 4,
    "پنج": 5,
    "شش": 6,
    "هفت": 7,
    "هشت": 8,
    "نه": 9,
    "ده": 10,
    "یازده": 11,
    "دوازده": 12,
    "سیزده": 13,
    "چهارده": 14,
    "پانزده": 15,
    "شانزده": 16,
    "هفده": 17,
    "هجده": 18,
    "نوزده": 19,
    "بیست": 20,
    "سی": 30,
    "چهل": 40,
    "پنجاه": 50,
    "شصت": 60,
    "هفتاد": 70,
    "هشتاد": 80,
    "نود": 90,
    "صد": 100,
}

UNIT_MULTIPLIERS = {
    "میلیارد": 1_000_000_000,
    "billion": 1_000_000_000,
    "میلیون": 1_000_000,
    "million": 1_000_000,
    "هزار": 1_000,
    "thousand": 1_000,
}

#: monetary unit implied by a column header, expressed as (multiplier to toman, label)
HEADER_UNITS: Tuple[Tuple[str, float, str], ...] = (
    ("میلیون تومان", 1_000_000.0, "million_toman"),
    ("میلیون ریال", 100_000.0, "million_rials_to_toman"),
    ("میلیارد تومان", 1_000_000_000.0, "billion_toman"),
    ("(تومان)", 1.0, "toman"),
)

RENT_FIELDS: Tuple[str, ...] = (
    "dataset_id",
    "dataset_title",
    "sub_table",
    "source_kind",
    "source_label",
    "evidence_tier",
    "verification",
    "date_jalali_raw",
    "date_jalali_ym",
    "date_status",
    "geography_level",
    "district_number",
    "district_raw",
    "area_name",
    "floor_area_sqm",
    "building_age_years",
    "building_age_text",
    "deposit_toman",
    "deposit_toman_min",
    "deposit_toman_max",
    "deposit_raw",
    "rent_toman",
    "rent_toman_min",
    "rent_toman_max",
    "rent_raw",
    "rent_is_free",
    "amenities",
    "flag_amount_ambiguous",
    "notes",
    "source_row",
)

SALE_FIELDS: Tuple[str, ...] = (
    "dataset_id",
    "dataset_title",
    "sub_table",
    "source_kind",
    "source_label",
    "evidence_tier",
    "verification",
    "date_jalali_raw",
    "date_jalali_ym",
    "date_status",
    "geography_level",
    "district_number",
    "area_name",
    "area_name_en",
    "price_basis",
    "floor_area_sqm",
    "building_age_years",
    "building_age_text",
    "price_psm_toman",
    "price_psm_raw",
    "price_psm_unit_source",
    "flag_amount_ambiguous",
    "notes",
    "source_row",
)

DISTRICT_STATS_FIELDS: Tuple[str, ...] = (
    "dataset_id",
    "dataset_title",
    "source_kind",
    "source_label",
    "evidence_tier",
    "verification",
    "date_jalali_raw",
    "date_jalali_ym",
    "date_status",
    "district_number",
    "district_raw",
    "price_avg_million_rials",
    "price_psm_toman",
    "price_psm_unit_source",
    "transactions_n",
    "is_total_row",
    "notes",
    "source_row",
)


# --------------------------------------------------------------------------------------
# RTF -> text (standard library only)
# --------------------------------------------------------------------------------------

#: groups whose contents are formatting metadata, not document text
RTF_IGNORED_DESTINATIONS = (
    "fonttbl",
    "colortbl",
    "expandedcolortbl",
    "stylesheet",
    "listtable",
    "listoverridetable",
    "rsidtbl",
    "generator",
    "themedata",
    "colorschememapping",
    "latentstyles",
    "datastore",
    "xmlnstbl",
    "info",
)


def _strip_rtf_group(text: str, start: int) -> int:
    """Return the index just past the balanced group that starts at ``start`` ('{')."""
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return len(text)


def _combine_surrogates(text: str) -> str:
    """RTF encodes non-BMP characters (e.g. 📊) as two negative ``\\uN`` surrogates."""
    try:
        return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le")
    except UnicodeDecodeError:
        return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def rtf_to_text(raw: bytes) -> str:
    """Decode a TextEdit-style RTF document to plain text.

    Handles ``\\uNNNN?`` and ``\\'hh`` escapes, drops formatting destination groups, and
    turns ``\\par``/``\\line`` and literal newlines into line breaks. Deliberately small —
    it only needs to be correct for this repository's vendored file, and the extracted text
    is what gets committed, not the RTF.
    """
    text = raw.decode("cp1252", errors="replace")

    # drop metadata groups (fonttbl, colortbl, {\*\...}, ...)
    out: List[str] = []
    index = 0
    while index < len(text):
        if text[index] == "{":
            probe = text[index + 1 : index + 60]
            stripped = probe.lstrip()
            destination = re.match(r"\\\*?\\?([a-zA-Z]+)", stripped)
            name = destination.group(1).lower() if destination else ""
            if stripped.startswith("\\*") or name in RTF_IGNORED_DESTINATIONS:
                index = _strip_rtf_group(text, index)
                continue
            index += 1
            continue
        if text[index] == "}":
            index += 1
            continue
        out.append(text[index])
        index += 1

    body = "".join(out)

    # unicode + codepage escapes (ASCII-only digit classes: \d would also match Persian digits)
    body = re.sub(r"\\u(-?[0-9]+)\s?", lambda m: chr(int(m.group(1)) % 65536), body)
    body = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: bytes([int(m.group(1), 16)]).decode("cp1252", "replace"), body)
    body = _combine_surrogates(body)

    # line-ish and spacing control words
    body = re.sub(r"\\(par|line|sect|page|pard)\b\s?", "\n", body)
    body = re.sub(r"\\tab\b\s?", "\t", body)
    body = re.sub(r"\\~", "\u00a0", body)
    body = re.sub(r"\\_", "-", body)

    # remaining control words / symbols
    body = re.sub(r"\\[a-zA-Z]+-?[0-9]*\s?", "", body)
    # TextEdit writes a line break as a trailing backslash + newline; the newline is content
    body = body.replace("\\\r\n", "\n").replace("\\\n", "\n")
    body = body.replace("\\{", "{").replace("\\}", "}").replace("\\\\", "\\")

    # normalise newlines and trim trailing whitespace per line
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"\\+$", "", line).rstrip() for line in body.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


# --------------------------------------------------------------------------------------
# Value parsing
# --------------------------------------------------------------------------------------


def normalise_text(value: str) -> str:
    """Normalise digits and unicode, strip markdown emphasis, keep Persian ZWNJ."""
    text = unicodedata.normalize("NFC", value)
    text = text.translate(PERSIAN_DIGITS)
    text = text.replace("**", "").replace("__", "")
    text = text.replace("\u00a0", " ").replace("\u200f", "").replace("\u200e", "")
    return re.sub(r"\s+", " ", text).strip()


def is_missing(value: str) -> bool:
    return normalise_text(value).strip() in MISSING_TOKENS


def words_to_digits(text: str) -> str:
    """«یک میلیون و 800 هزار» -> «1 میلیون و 800 هزار» (longest words first)."""
    result = text
    for word in sorted(PERSIAN_NUMBER_WORDS, key=len, reverse=True):
        result = re.sub(
            rf"(?<![\u0600-\u06FF]){word}(?![\u0600-\u06FF])",
            str(PERSIAN_NUMBER_WORDS[word]),
            result,
        )
    return result


def has_unit_word(text: str) -> bool:
    return any(word in text for word in UNIT_MULTIPLIERS)


def unit_multiplier_of(text: str, default: float) -> float:
    for word, factor in UNIT_MULTIPLIERS.items():
        if word in text:
            return factor
    return default


def first_number(text: str) -> Optional[float]:
    match = re.search(r"[0-9]+(?:\.[0-9]+)?", text)
    return float(match.group(0)) if match else None


def parse_single_amount(text: str, default_multiplier: float) -> Tuple[Optional[float], List[str]]:
    """Parse an amount such as «2 میلیون و 400 هزار», «60 میلیون», «1/2 میلیارد».

    Returns ``(value_or_None, notes)`` where the value is already multiplied by the unit
    written in the cell, or by ``default_multiplier`` (from the column header) when the cell
    has no unit word. A chunk that lost its unit («3 میلیون و 3800») is *not* guessed: the
    function returns ``None`` and flags it for human review.
    """
    notes: List[str] = []
    prepared = words_to_digits(normalise_text(text)).replace("٬", "").replace(",", "").replace("،", "")
    if not prepared:
        return None, notes

    # Persian decimal written with a slash and no spaces: «1/2 میلیارد» == 1.2 billion
    decimal_match = re.match(r"^([0-9]+)/([0-9]+)\s*(.*)$", prepared)
    if decimal_match:
        whole, fraction, rest = decimal_match.group(1), decimal_match.group(2), decimal_match.group(3)
        value = float(whole) + float(fraction) / (10 ** len(fraction))
        notes.append(f"persian_decimal_slash:{whole}/{fraction}")
        return value * unit_multiplier_of(rest, default_multiplier), notes

    chunks = [chunk.strip() for chunk in re.split(r"\s+و\s+", prepared) if chunk.strip()]
    if not chunks:
        return None, notes

    if len(chunks) == 1:
        number = first_number(chunks[0])
        if number is None:
            notes.append(f"unparsed_amount:{prepared}")
            return None, notes
        return number * unit_multiplier_of(chunks[0], default_multiplier), notes

    total = 0.0
    for index, chunk in enumerate(chunks):
        number = first_number(chunk)
        if number is None:
            notes.append(f"unparsed_amount:{prepared}")
            return None, notes
        if has_unit_word(chunk):
            total += number * unit_multiplier_of(chunk, default_multiplier)
        elif index == 0:
            total += number * default_multiplier
        else:
            notes.append(f"missing_unit_in_chunk:{chunk}")
            return None, notes
    return total, notes


def parse_amount_field(
    raw: str, default_multiplier: float
) -> Dict[str, Any]:
    """Parse a money cell into scalar/range/free/missing plus flags."""
    result: Dict[str, Any] = {
        "value": None,
        "min": None,
        "max": None,
        "is_free": False,
        "ambiguous": False,
        "notes": [],
    }
    text = normalise_text(raw)
    if is_missing(text):
        return result
    if "رایگان" in text:
        result["value"] = 0.0
        result["is_free"] = True
        result["notes"].append("free_of_charge_as_written")
        return result

    if "الی" in text:
        parts = [part for part in re.split(r"\s*الی\s*", text) if part.strip()]
        # «12 الی 32 میلیون»: a side without its own unit inherits the unit written in the cell
        fallback = unit_multiplier_of(text, default_multiplier)
        if not has_unit_word(text):
            fallback = default_multiplier
        values = []
        for part in parts:
            value, notes = parse_single_amount(part, fallback)
            result["notes"].extend(notes)
            if value is not None:
                values.append(value)
        if values:
            result["min"] = min(values)
            result["max"] = max(values)
        if len(values) != 2:
            result["ambiguous"] = True
            result["notes"].append("range_not_two_sides")
        return result

    # «6 / 15.5» — two values in one cell, slash surrounded by spaces
    if re.search(r"[0-9]\s+/|/\s+[0-9]", text):
        parts = [part.strip() for part in re.split(r"/", text) if part.strip()]
        parsed = [parse_single_amount(part, default_multiplier) for part in parts]
        numbers = [value for value, _ in parsed if value is not None]
        for _, notes in parsed:
            result["notes"].extend(notes)
        if numbers:
            result["min"] = min(numbers)
            result["max"] = max(numbers)
        result["ambiguous"] = True
        result["notes"].append("two_values_in_one_cell")
        return result

    value, notes = parse_single_amount(text, default_multiplier)
    result["value"] = value
    result["notes"].extend(notes)
    return result


def parse_int_cell(raw: str) -> Tuple[Optional[int], List[str]]:
    """Parse a count / area / age cell such as «90» or «61 متر»."""
    text = normalise_text(raw)
    if is_missing(text):
        return None, []
    match = re.search(r"[0-9]+(?:\.[0-9]+)?", text)
    if not match:
        return None, [f"unparsed_number:{text}"]
    return int(round(float(match.group(0)))), []


def parse_building_age(raw: str) -> Tuple[Optional[int], str, List[str]]:
    text = normalise_text(raw)
    if is_missing(text):
        return None, "", []
    if "نوساز" in text:
        return None, "نوساز (new build)", ["age_new_build"]
    value, notes = parse_int_cell(text)
    return value, text, notes


def parse_district(raw: str) -> Tuple[Optional[int], str]:
    text = normalise_text(raw)
    if is_missing(text):
        return None, ""
    match = re.search(r"(\d+)", text)
    number = int(match.group(1)) if match else None
    return number, text


def parse_jalali_date(raw: str) -> Tuple[str, Optional[str], List[str]]:
    """«آبان ۱۴۰۴» -> ('1404-08'). Returns (raw, ym_or_None, notes)."""
    text = normalise_text(raw)
    if not text:
        return "", None, []
    notes: List[str] = []
    ym = None
    for name, month in JALALI_MONTHS.items():
        if name in text:
            year_match = re.search(r"(13\d{2}|14\d{2})", text)
            if year_match:
                ym = f"{year_match.group(1)}-{month:02d}"
            else:
                notes.append("month_without_year")
            break
    if ym is None and re.search(r"13\d{2}/|14\d{2}/", text):
        parts = re.findall(r"\d+", text)
        if len(parts) >= 2:
            ym = f"{parts[0]}-{int(parts[1]):02d}"
    return text, ym, notes


# --------------------------------------------------------------------------------------
# Header mapping
# --------------------------------------------------------------------------------------

HEADER_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"^(منطقه شهری|منطقه)$", "district"),
    (r"^(محل|محله|شهرستان)$", "area_name"),
    (r"^neighborhood \(persian\)$", "area_name"),
    (r"^neighborhood \(english\)$", "area_name_en"),
    (r"^متراژ( \(مترمربع\))?$", "floor_area"),
    (r"^سن بنا( \(سال\))?$", "building_age"),
    (r"^(ودیعه|رهن)( \(میلیون تومان\)| \(تومان\)| \(میلیارد تومان\))?$", "deposit"),
    (r"^(اجاره بها|اجاره)( \(میلیون تومان\)| \(تومان\))?$", "rent"),
    (r"^قیمت هر مترمربع \(تومان\)$", "price_psm"),
    (r"^estimated avg price / m²$", "price_psm_estimated"),
    (r"^newly built price / m²$", "price_psm_newbuilt"),
    (r"^متوسط قیمت \(میلیون ریال\)$", "price_avg_million_rials"),
    (r"^تعداد معاملات \(فقره\)$", "transactions"),
    (r"^امکانات$", "amenities"),
)


def canonical_field(header: str) -> Optional[str]:
    text = normalise_text(header).rstrip(":").strip()
    lowered = text.lower()
    for pattern, field in HEADER_PATTERNS:
        if re.match(pattern, text) or re.match(pattern, lowered):
            return field
    return None


def header_unit(header: str) -> Tuple[float, str]:
    text = normalise_text(header)
    for token, multiplier, label in HEADER_UNITS:
        if token in text:
            return multiplier, label
    if "million" in text.lower():
        return 1_000_000.0, "million_toman"
    return 1.0, "assumed_toman"


# --------------------------------------------------------------------------------------
# Transcript structure
# --------------------------------------------------------------------------------------

DATASET_HEADING = re.compile(r"^###\s*📊\s*Dataset\s+(\d+):\s*(.+?)\s*$")
META_LINE = re.compile(r"^\*\*(Source|Date|Title|Note)s?:\*\*\s*(.*)$", re.IGNORECASE)
SUB_TABLE_HEADING = re.compile(r"^\*\*جدول\s*([0-9۰-۹]+):\s*(.+?)\*\*$")
FULLWIDTH_HEADING = re.compile(r"^\*\*(جدول[^*]+)\*\*$")


class Block:
    """One source table: a dataset (or one of its sub-tables)."""

    def __init__(self, dataset_id: int, title: str):
        self.dataset_id = dataset_id
        self.title = title
        self.sub_table = ""
        self.meta: Dict[str, str] = {}
        self.header: List[str] = []
        self.rows: List[List[str]] = []
        self.line_numbers: List[int] = []


def split_blocks(lines: Iterable[str]) -> List[Block]:
    blocks: List[Block] = []
    current: Optional[Block] = None
    in_table = False

    for number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        heading = DATASET_HEADING.match(line.strip())
        if heading:
            current = Block(int(heading.group(1)), normalise_text(heading.group(2)))
            blocks.append(current)
            in_table = False
            continue
        if current is None:
            continue

        sub = SUB_TABLE_HEADING.match(line.strip()) or FULLWIDTH_HEADING.match(line.strip())
        if sub and not line.strip().startswith("|"):
            # a new sub-table inside the same dataset (used by dataset 7)
            is_new = bool(current.header or current.rows)
            if is_new:
                clone = Block(current.dataset_id, current.title)
                clone.meta = dict(current.meta)
                clone.sub_table = normalise_text(line)
                blocks.append(clone)
                current = clone
            else:
                current.sub_table = normalise_text(line)
            in_table = False
            continue

        meta = META_LINE.match(line.strip())
        if meta and not line.strip().startswith("|"):
            key = meta.group(1).capitalize()
            value = normalise_text(meta.group(2))
            if key not in current.meta:
                current.meta[key] = value
            else:
                current.meta[key] = f"{current.meta[key]} {value}"
            in_table = False
            continue

        if line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", cell or "-") for cell in cells):
                in_table = True
                continue
            if not current.header:
                current.header = cells
                in_table = True
                continue
            current.rows.append(cells)
            current.line_numbers.append(number)
            continue

        if not line.strip():
            in_table = False

    return [block for block in blocks if block.header and block.rows]


# --------------------------------------------------------------------------------------
# Row normalisation
# --------------------------------------------------------------------------------------


def base_metadata(block: Block, date_raw: str, date_ym: Optional[str], date_status: str) -> Dict[str, Any]:
    source = block.meta.get("Source", "")
    simulated = "simulated" in source.lower() or "simulated" in block.meta.get("Note", "").lower()
    source_kind = "simulated_web_research" if simulated else "image_transcription"
    return {
        "dataset_id": block.dataset_id,
        "dataset_title": block.title,
        "sub_table": block.sub_table,
        "source_kind": source_kind,
        "source_label": source,
        "evidence_tier": "D" if simulated else "C",
        "verification": "unverified_simulated_source" if simulated else "unverified_transcription",
        "date_jalali_raw": date_raw,
        "date_jalali_ym": date_ym,
        "date_status": date_status,
    }


def resolve_date(block: Block) -> Tuple[str, Optional[str], str, List[str]]:
    """Date comes from the dataset metadata, else from the sub-table title, else missing."""
    notes: List[str] = []
    for key in ("Date", "Title"):
        if block.meta.get(key):
            raw, ym, date_notes = parse_jalali_date(block.meta[key])
            notes.extend(date_notes)
            if ym:
                return raw, ym, "explicit" if key == "Date" else "from_title", notes
    raw, ym, date_notes = parse_jalali_date(block.sub_table)
    notes.extend(date_notes)
    if ym:
        return raw, ym, "from_sub_table_title", notes
    return block.meta.get("Date", ""), None, "missing", notes


def normalise_block(block: Block) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return ``(rent_rows, sale_rows, district_stat_rows)`` for one block."""
    fields = [canonical_field(header) for header in block.header]
    date_raw, date_ym, date_status, date_notes = resolve_date(block)
    meta = base_metadata(block, date_raw, date_ym, date_status)

    rent_rows: List[Dict[str, Any]] = []
    sale_rows: List[Dict[str, Any]] = []
    stat_rows: List[Dict[str, Any]] = []

    units = {index: header_unit(header) for index, header in enumerate(block.header)}

    for row, line_number in zip(block.rows, block.line_numbers):
        values = {fields[i]: row[i] for i in range(min(len(fields), len(row))) if fields[i]}
        notes: List[str] = list(date_notes)
        ambiguous = False

        district_number, district_raw = parse_district(values.get("district", ""))

        if "price_avg_million_rials" in values or "transactions" in values:
            # this column is numeric in *millions of rials*: 1349.3 -> 1,349,300,000 rials
            raw_text = values.get("price_avg_million_rials", "")
            millions_of_rials, amount_notes = parse_single_amount(raw_text, 1.0)
            notes.extend(amount_notes)
            toman = millions_of_rials * 100_000.0 if millions_of_rials is not None else None
            transactions, txn_notes = parse_int_cell(values.get("transactions", ""))
            notes.extend(txn_notes)
            district_text = normalise_text(values.get("district", ""))
            is_total = "متوسط شهر" in district_text or "سرجمع" in district_text
            stat_rows.append(
                {
                    **meta,
                    "district_number": district_number,
                    "district_raw": district_raw,
                    "price_avg_million_rials": millions_of_rials,
                    "price_psm_toman": toman,
                    "price_psm_unit_source": "million_rials_to_toman",
                    "transactions_n": transactions,
                    "is_total_row": is_total,
                    "notes": "; ".join(list(dict.fromkeys(notes + (["city_total_row"] if is_total else [])))),
                    "source_row": line_number,
                }
            )
            continue

        if any(key in values for key in ("price_psm", "price_psm_estimated", "price_psm_newbuilt")):
            floor_area, area_notes = parse_int_cell(values.get("floor_area", ""))
            age_years, age_text, age_notes = parse_building_age(values.get("building_age", ""))
            notes.extend(area_notes + age_notes)

            bases: List[Tuple[str, str, Tuple[float, str]]] = []
            if "price_psm" in values:
                bases.append(("asking_price_per_sqm", values["price_psm"], units.get(0, (1.0, "toman"))))
            if "price_psm_estimated" in values:
                bases.append(("kilid_estimated_avg", values["price_psm_estimated"], (1_000_000.0, "million_toman")))
            if "price_psm_newbuilt" in values:
                bases.append(("kilid_newly_built", values["price_psm_newbuilt"], (1_000_000.0, "million_toman")))

            for basis, raw_value, (multiplier, unit_label) in bases:
                amount = parse_amount_field(raw_value, multiplier)
                ambiguous = ambiguous or amount["ambiguous"]
                sale_rows.append(
                    {
                        **meta,
                        "geography_level": "neighbourhood",
                        "district_number": district_number,
                        "area_name": values.get("area_name", ""),
                        "area_name_en": values.get("area_name_en", ""),
                        "price_basis": basis,
                        "floor_area_sqm": floor_area,
                        "building_age_years": age_years,
                        "building_age_text": age_text,
                        "price_psm_toman": amount["value"],
                        "price_psm_raw": raw_value,
                        "price_psm_unit_source": unit_label,
                        "flag_amount_ambiguous": ambiguous,
                        "notes": "; ".join(notes + amount["notes"]),
                        "source_row": line_number,
                    }
                )
            continue

        # default: a rent/deposit observation
        deposit_multiplier, deposit_unit = units.get(
            next((i for i, f in enumerate(fields) if f == "deposit"), -1), (1.0, "assumed_toman")
        )
        rent_multiplier, rent_unit = units.get(
            next((i for i, f in enumerate(fields) if f == "rent"), -1), (1.0, "assumed_toman")
        )
        deposit = parse_amount_field(values.get("deposit", ""), deposit_multiplier)
        rent = parse_amount_field(values.get("rent", ""), rent_multiplier)
        floor_area, area_notes = parse_int_cell(values.get("floor_area", ""))
        age_years, age_text, age_notes = parse_building_age(values.get("building_age", ""))
        notes.extend(area_notes + age_notes + deposit["notes"] + rent["notes"])
        ambiguous = deposit["ambiguous"] or rent["ambiguous"]
        if age_years is not None and age_years > 60:
            notes.append(f"implausible_building_age:{age_years}")
        if rent["value"] == 0 and not rent["is_free"]:
            ambiguous = True
            notes.append("zero_rent_as_written")
        if deposit_unit == "assumed_toman" or rent_unit == "assumed_toman":
            notes.append("unit_assumed_toman_from_values")

        rent_rows.append(
            {
                **meta,
                "geography_level": "county" if "شهرستان" in block.header else "neighbourhood",
                "district_number": district_number,
                "district_raw": district_raw,
                "area_name": values.get("area_name", ""),
                "floor_area_sqm": floor_area,
                "building_age_years": age_years,
                "building_age_text": age_text,
                "deposit_toman": deposit["value"],
                "deposit_toman_min": deposit["min"],
                "deposit_toman_max": deposit["max"],
                "deposit_raw": values.get("deposit", ""),
                "rent_toman": rent["value"],
                "rent_toman_min": rent["min"],
                "rent_toman_max": rent["max"],
                "rent_raw": values.get("rent", ""),
                "rent_is_free": rent["is_free"],
                "amenities": values.get("amenities", ""),
                "flag_amount_ambiguous": ambiguous,
                "notes": "; ".join(dict.fromkeys(notes)),
                "source_row": line_number,
            }
        )

    return rent_rows, sale_rows, stat_rows


# --------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------


def write_csv(path: Path, fields: Iterable[str], rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in writer.fieldnames})


def number(value: Optional[float]) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Clean the rent-data RTF transcript into CSVs.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="input .rtf")
    parser.add_argument("--out", default=str(DEFAULT_OUTDIR), help="output directory")
    parser.add_argument("--dump-text", action="store_true", help="print the extracted text and stop")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    raw = input_path.read_bytes()
    text = rtf_to_text(raw)

    if args.dump_text:
        print(text)
        return 0

    blocks = split_blocks(text.split("\n"))
    rent_rows: List[Dict[str, Any]] = []
    sale_rows: List[Dict[str, Any]] = []
    stat_rows: List[Dict[str, Any]] = []
    dataset_report: List[Dict[str, Any]] = []
    anomalies: List[Dict[str, Any]] = []

    for block in blocks:
        block_rent, block_sale, block_stats = normalise_block(block)
        rent_rows.extend(block_rent)
        sale_rows.extend(block_sale)
        stat_rows.extend(block_stats)
        dataset_report.append(
            {
                "dataset_id": block.dataset_id,
                "title": block.title,
                "sub_table": block.sub_table,
                "source": block.meta.get("Source", ""),
                "date": block.meta.get("Date", "") or block.meta.get("Title", ""),
                "note": block.meta.get("Note", ""),
                "columns": block.header,
                "rows": len(block.rows),
                "parsed_as": {"rent": len(block_rent), "sale": len(block_sale), "district_stats": len(block_stats)},
            }
        )
        for row in block_rent + block_sale + block_stats:
            flags = [flag for flag in str(row.get("notes", "")).split("; ") if flag]
            for flag in flags:
                anomalies.append(
                    {
                        "dataset_id": block.dataset_id,
                        "sub_table": block.sub_table,
                        "source_row": row.get("source_row"),
                        "flag": flag,
                    }
                )

    out_dir = Path(args.out)
    write_csv(out_dir / "rent_observations.csv", RENT_FIELDS, rent_rows)
    write_csv(out_dir / "sale_observations.csv", SALE_FIELDS, sale_rows)
    write_csv(out_dir / "district_sale_stats.csv", DISTRICT_STATS_FIELDS, stat_rows)

    flag_counts: Dict[str, int] = {}
    for anomaly in anomalies:
        flag_counts[anomaly["flag"]] = flag_counts.get(anomaly["flag"], 0) + 1

    report = {
        "input": {
            "path": str(input_path.relative_to(REPO_ROOT)),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "extracted_lines": len(text.split("\n")),
        },
        "what_this_is": (
            "An LLM-conversation transcript ('all the raw data extracted and transcribed from every "
            "image and text prompt'), not a single newspaper dataset. Its own header warns against "
            "combining timeframes, so each source table is kept separate here."
        ),
        "datasets": dataset_report,
        "unit_rules": {
            "money_output": "toman",
            "million_toman": "x 1,000,000",
            "million_rials_to_toman": "x 1,000,000 rials = x 100,000 toman (header says million rials)",
            "bare_number": "uses the unit in its column header; if the header has none, toman is assumed and flagged",
            "persian_decimal_slash": "'1/2 میلیارد' read as 1.2 billion; flagged for review",
        },
        "row_counts": {
            "rent_observations": len(rent_rows),
            "sale_observations": len(sale_rows),
            "district_sale_stats": len(stat_rows),
        },
        "flag_counts": dict(sorted(flag_counts.items(), key=lambda item: -item[1])),
        "warnings": [
            "Dataset 7 is labelled 'Simulated web research from fardayeeghtesad.com' — it is NOT a "
            "real scrape and must not be cited as Fardayeeghtesad/Donya-e-Eqtesad reporting (tier D).",
            "Every other dataset is a transcription of images; values need checking against the "
            "original screenshots/newspaper before publication (tier C).",
            "The file name says 'donyaeghtesad' but the only named outlet inside is Fardayeeghtesad; "
            "no Donya-e-Eqtesad table is present in this file.",
            "Datasets 1 and 2 carry no date; dataset 1 is also neighbourhood-level with no floor area.",
            "Deposit/rent column order differs between datasets (2 uses deposit-first, 3 rent-first); "
            "columns were mapped by header name, never by position.",
            "Kilid's own scraped series (kilid/kilid_data) supersedes dataset 1 for any Tehrans "
            "price-per-m2 claim, because it is dated and reproducible.",
        ],
        "anomalies": anomalies,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "parse_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"input       : {input_path} ({len(raw):,} bytes, sha256 {report['input']['sha256'][:12]}…)")
    print(f"blocks      : {len(blocks)} table(s) across {len({b.dataset_id for b in blocks})} dataset(s)")
    print(f"rent rows   : {len(rent_rows)}")
    print(f"sale rows   : {len(sale_rows)}")
    print(f"district rows: {len(stat_rows)}")
    print("flags       :", json.dumps(report["flag_counts"], ensure_ascii=False))
    print(f"output      : {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
