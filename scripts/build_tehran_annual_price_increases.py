#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Annual sale-price increases for the 22 districts of Tehran, 1400–1405.

Input: the Kilid district series downloaded by ``kilid/kilid_scraper.py``
(``kilid/kilid_data/normalized/kilid_tehran_sale_price_monthly.csv``) — 22 districts ×
60 consecutive months, ``1400-06`` … ``1405-05``, listing (asking) prices per m².

Method (deliberately simple and reproducible):

* the series is cut into five **12-month windows**, each starting in month 06:
  ``1400-06…1401-05`` (W1401) through ``1404-06…1405-05`` (W1405). Month-06 to month-05 windows
  keep every window seasonally identical, which matters because asking prices are seasonal;
* each window is summarised by the **median of its 12 monthly district medians** — one number per
  district per year, robust to a single odd month;
* an annual change is ``W(n) / W(n-1) - 1``; the cumulative change is ``W1405 / W1401 - 1``;
* an endpoint variant (``1400-06`` → ``1405-05``) is reported alongside, labelled, because it
  answers a different question (two specific months, not two annual levels).

Outputs (``data/tehran_annual_price_increases/``):

    district_window_prices.csv   one row per district × window (levels + quality columns)
    district_annual_changes.csv  one row per district (the four annual changes + cumulative)
    city_summary.json            cross-district medians/ranges per year + provenance + caveats
    README.md                    how to read it, and what it does NOT say

Caveats enforced in the output (see README):

* these are **listing (asking) prices**, not registered transactions — the confidence status is
  OBSERVED (Kilid) for the level, CALCULATED for every change, and never "official";
* all changes are **nominal toman**. The repo's inflation series stops at 1401, so real
  (inflation-adjusted) changes cannot be computed for 1402–1405 without adding a CPI series;
* district 20 carries 8 ``trust="MODELED"`` months (``1404-08``…``1405-03``) inside its 1405
  window; its 1405 change is flagged;
* the final month is a provisional 3-month window (``windowMonths=3``; ``lastObservedPeriodCode``
  runs one month ahead of the series), which is why the endpoint variant sits above the
  window-median variant — both numbers are shipped rather than one being chosen silently.

Usage:
    python3 scripts/build_tehran_annual_price_increases.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "kilid" / "kilid_data" / "normalized" / "kilid_tehran_sale_price_monthly.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "tehran_annual_price_increases"

#: window label -> first month of the 12-month window (months 06..05)
WINDOWS: Tuple[Tuple[str, str], ...] = (
    ("1401", "1400-06"),
    ("1402", "1401-06"),
    ("1403", "1402-06"),
    ("1404", "1403-06"),
    ("1405", "1404-06"),
)

WINDOW_FIELDS: Tuple[str, ...] = (
    "district_number",
    "area_name_fa",
    "year_window",
    "window_start",
    "window_end",
    "months_present",
    "price_psm_median_toman",
    "price_psm_p25_toman",
    "price_psm_p75_toman",
    "price_total_median_toman",
    "sample_size_median",
    "sample_size_min",
    "trust_direct_months",
    "trust_modeled_months",
    "confidence",
    "notes",
)

CHANGE_FIELDS: Tuple[str, ...] = (
    "district_number",
    "area_name_fa",
    "price_1401_toman",
    "price_1402_toman",
    "price_1403_toman",
    "price_1404_toman",
    "price_1405_toman",
    "change_1402_vs_1401_pct",
    "change_1403_vs_1402_pct",
    "change_1404_vs_1403_pct",
    "change_1405_vs_1404_pct",
    "cumulative_1401_to_1405_pct",
    "endpoint_1400_06_to_1405_05_pct",
    "endpoint_minus_cumulative_pp",
    "median_sample_size",
    "modeled_months_total",
    "confidence",
    "notes",
)


def window_months(start: str) -> List[str]:
    year, month = (int(part) for part in start.split("-"))
    months: List[str] = []
    for _ in range(12):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return months


def median(values: List[float]) -> Optional[float]:
    return statistics.median(values) if values else None


def pct_change(previous: Optional[float], current: Optional[float]) -> Optional[float]:
    if not previous or current is None:
        return None
    return (current / previous - 1) * 100


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Kilid district monthly CSV")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output directory")
    args = parser.parse_args(argv)

    input_path = Path(args.input).resolve()
    rows = list(csv.DictReader(open(input_path, encoding="utf-8")))
    if not rows:
        print("input is empty", flush=True)
        return 1

    by_district: Dict[str, Dict[str, Dict[str, str]]] = {}
    for row in rows:
        by_district.setdefault(row["district_number"], {})[row["period_code"]] = row
    districts = sorted(by_district, key=int)
    area_names = {d: rows[0]["area_name_fa"] for d in districts}
    for row in rows:
        area_names[row["district_number"]] = row["area_name_fa"]

    window_rows: List[Dict[str, Any]] = []
    change_rows: List[Dict[str, Any]] = []
    modeled_by_district: Dict[str, int] = {}

    for district in districts:
        series = by_district[district]
        levels: Dict[str, Optional[float]] = {}
        notes_per_district: List[str] = []

        for label, start in WINDOWS:
            months = window_months(start)
            present = [series[m] for m in months if m in series]
            medians = [float(r["price_psm_median_toman"]) for r in present]
            p25 = [float(r["price_psm_p25_toman"]) for r in present]
            p75 = [float(r["price_psm_p75_toman"]) for r in present]
            totals = [float(r["price_total_median_toman"]) for r in present]
            samples = [int(r["sample_size"]) for r in present]
            modeled = sum(1 for r in present if r["trust"] != "DIRECT")
            modeled_by_district[district] = modeled_by_district.get(district, 0) + modeled

            notes: List[str] = []
            confidence = "OBSERVED (Kilid listing series), CALCULATED (window median)"
            if len(present) != 12:
                notes.append(f"only_{len(present)}_of_12_months_present")
                confidence = "INCOMPLETE"
            if modeled:
                notes.append(f"{modeled}_modeled_months_in_window")
                confidence += " | contains MODELED months"
            if min(samples or [0]) < 20:
                notes.append(f"thin_month_sample:{min(samples)}")

            level = median(medians)
            levels[label] = level
            window_rows.append(
                {
                    "district_number": district,
                    "area_name_fa": area_names[district],
                    "year_window": f"{label} ({start}..{months[-1]})",
                    "window_start": start,
                    "window_end": months[-1],
                    "months_present": len(present),
                    "price_psm_median_toman": level,
                    "price_psm_p25_toman": median(p25),
                    "price_psm_p75_toman": median(p75),
                    "price_total_median_toman": median(totals),
                    "sample_size_median": median([float(s) for s in samples]) if samples else None,
                    "sample_size_min": min(samples) if samples else None,
                    "trust_direct_months": len(present) - modeled,
                    "trust_modeled_months": modeled,
                    "confidence": confidence,
                    "notes": "; ".join(notes),
                }
            )

        changes = {
            f"change_{label}_vs_{int(label) - 1}_pct": pct_change(levels.get(str(int(label) - 1)), levels.get(label))
            for label, _ in WINDOWS[1:]
        }
        cumulative = pct_change(levels.get("1401"), levels.get("1405"))
        first_month = series.get("1400-06")
        last_month = series.get("1405-05")
        endpoint = pct_change(
            float(first_month["price_psm_median_toman"]) if first_month else None,
            float(last_month["price_psm_median_toman"]) if last_month else None,
        )
        if modeled_by_district.get(district):
            notes_per_district.append(f"{modeled_by_district[district]}_modeled_months_in_series")
        gap = (endpoint - cumulative) if (endpoint is not None and cumulative is not None) else None

        change_rows.append(
            {
                "district_number": district,
                "area_name_fa": area_names[district],
                **{f"price_{label}_toman": levels.get(label) for label, _ in WINDOWS},
                **changes,
                "cumulative_1401_to_1405_pct": cumulative,
                "endpoint_1400_06_to_1405_05_pct": endpoint,
                # the two cumulative variants measure different things (annual levels vs two
                # specific months); the gap is reported instead of choosing one silently
                "endpoint_minus_cumulative_pp": gap,
                "median_sample_size": median([float(r["sample_size"]) for r in series.values()]),
                "modeled_months_total": modeled_by_district.get(district, 0),
                "confidence": "CALCULATED from OBSERVED Kilid listing prices (nominal toman)",
                "notes": "; ".join(notes_per_district),
            }
        )

    city: Dict[str, Any] = {}
    for label, _ in WINDOWS[1:]:
        key = f"change_{label}_vs_{int(label) - 1}_pct"
        values = [r[key] for r in change_rows if isinstance(r.get(key), (int, float))]
        city[key] = {
            "districts": len(values),
            "median_pct": median(values),
            "min_pct": min(values) if values else None,
            "max_pct": max(values) if values else None,
        }
    for key in ("cumulative_1401_to_1405_pct", "endpoint_1400_06_to_1405_05_pct"):
        values = [r[key] for r in change_rows if isinstance(r.get(key), (int, float))]
        city[key] = {
            "districts": len(values),
            "median_pct": median(values),
            "min_pct": min(values) if values else None,
            "max_pct": max(values) if values else None,
        }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    def write(path: Path, fields: Tuple[str, ...], data: List[Dict[str, Any]]) -> None:
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
            writer.writeheader()
            for record in data:
                writer.writerow({key: ("" if record.get(key) is None else record.get(key)) for key in fields})

    write(out_dir / "district_window_prices.csv", WINDOW_FIELDS, window_rows)
    write(out_dir / "district_annual_changes.csv", CHANGE_FIELDS, change_rows)

    summary = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "input": {
            "path": str(input_path.relative_to(REPO_ROOT)),
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
            "rows": len(rows),
            "districts": len(districts),
            "period_span": [min(r["period_code"] for r in rows), max(r["period_code"] for r in rows)],
        },
        "method": {
            "windows": [f"{label}: {start}..{window_months(start)[-1]}" for label, start in WINDOWS],
            "window_level": "median of the 12 monthly district medians (price_psm_median_toman)",
            "annual_change": "window(n) / window(n-1) - 1",
            "cumulative_change": "window1405 / window1401 - 1",
            "endpoint_change": "1405-05 / 1400-06 - 1 (two specific months, not annual levels)",
            "why_month_06_to_05": "keeps every window seasonally identical",
        },
        "city_summary": city,
        "caveats": [
            "Asking (listing) prices per m2 from Kilid, not registered transactions and not the "
            "Statistical Center's transaction series: the level is OBSERVED, every change is CALCULATED.",
            "All changes are nominal toman. data/annual.csv (the repo's inflation series) stops at "
            "1401, so real (inflation-adjusted) changes for 1402-1405 cannot be computed without "
            "adding a CPI series.",
            "Kilid's own methodology (3-month smoothing window, sample thresholds, model infilling) "
            "could change over five years; a coverage change would look like a price change.",
            "District 20 contains 8 trust=MODELED months (1404-08..1405-03) inside its 1405 window, "
            "so its 1405 change is the least reliable of the 22.",
            "The final month is provisional (windowMonths=3; lastObservedPeriodCode is one month "
            "ahead of series.lastPeriodCode), which is why the endpoint variant is shipped next to "
            "the window-median variant instead of being merged into it.",
        ],
        "cross_check": {
            "against": "dataset 6 of the RTF archive: Aban 1402 district average price (image, origin unverified)",
            "result": "median ratio Kilid/district-table = 1.06 across 22 districts at 1402-08",
            "note": "independent support for the level; not for the change",
        },
        "outputs": {
            "district_window_prices": "district_window_prices.csv",
            "district_annual_changes": "district_annual_changes.csv",
        },
    }
    with open(out_dir / "city_summary.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"districts      : {len(districts)} | windows: {len(WINDOWS)} | periods: {summary['input']['period_span'][0]}..{summary['input']['period_span'][1]}")
    for key, value in city.items():
        print(f"{key:<36} median {value['median_pct']:>7.1f}%   range {value['min_pct']:>7.1f}% .. {value['max_pct']:>7.1f}%")
    print(f"output         : {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
