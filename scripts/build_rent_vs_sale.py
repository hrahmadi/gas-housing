#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a switchable sale ↔ rent dataset for the 22 districts of Tehran.

Inputs (both already in this repo):

* **sales** — Kilid district series, 22 districts × 60 months (``1400-06``…``1405-05``),
  asking price per m². Cut into five 12-month windows to give the sale side a time dimension;
* **rents** — Donya-e-Eqtesad asking-rent tables, two snapshots at district level
  (Tir 1404 and Aban 1404), each row an ordinary mid-size apartment with a monthly rent
  and a deposit.

What the switch can and cannot show:

* sales: a level per year (five windows) and a five-year change per district;
* rents: a level per snapshot per district — **two months, so no rent trend**;
* the payoff of the switch: the **rent-to-price ratio** (gross yield) per district, computed by
  *comparing two observed series*, never by converting one into the other.

The ratio is a comparison, not a valuation: the rent side is asking rent for a mid-size
apartment, the sale side is asking price per m² from a different set of months, and both are
listing figures. It is shipped as indicative, with every input next to it.

Outputs (``data/rent_vs_sale/``):

    district_sale_rent_panel.csv   one row per district: all sale and rent metrics + ratio
    switch_data.json               the same, shaped for the interactive page
    explorer.html                  self-contained page with the sale / rent / ratio switch

Usage:
    python3 scripts/build_rent_vs_sale.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics as st
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
KILID_MONTHLY = REPO_ROOT / "kilid" / "kilid_data" / "normalized" / "kilid_tehran_sale_price_monthly.csv"
RENT_ABAN = REPO_ROOT / "data" / "raw" / "tehran_housing_market_data" / "observations" / "rent_observations.csv"
RENT_TIR = REPO_ROOT / "data" / "raw" / "tehran_housing_market_data" / "sources" / "donya-e-eqtesad_1404-04" / "rent_asking.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "rent_vs_sale"

SALE_WINDOWS: Tuple[Tuple[str, str], ...] = (
    ("1401", "1400-06"),
    ("1402", "1401-06"),
    ("1403", "1402-06"),
    ("1404", "1403-06"),
    ("1405", "1404-06"),
)
SALE_LEVEL_WINDOW = "1405"          # the window used as "current" for the ratio
RENT_SNAPSHOTS: Tuple[Tuple[str, str, str], ...] = (
    ("1404-08", "آبان ۱۴۰۴", "جدول آرشیو، مجموعه‌دادهٔ ۳"),
    ("1404-04", "تیر ۱۴۰۴", "جدول دنیای اقتصاد، بازنویسی مالک"),
)

PANEL_FIELDS: Tuple[str, ...] = (
    "district_number",
    "area_name_fa",
    "sale_level_1405_toman_per_sqm",
    "sale_1401_toman_per_sqm",
    "sale_1402_toman_per_sqm",
    "sale_1403_toman_per_sqm",
    "sale_1404_toman_per_sqm",
    "sale_cumulative_1401_1405_pct",
    "sale_p25_1405_toman_per_sqm",
    "sale_p75_1405_toman_per_sqm",
    "rent_snapshot_1404_08_listings",
    "rent_snapshot_1404_08_monthly_toman",
    "rent_snapshot_1404_08_per_sqm_toman",
    "rent_snapshot_1404_08_deposit_toman",
    "rent_snapshot_1404_08_median_area_sqm",
    "rent_snapshot_1404_04_listings",
    "rent_snapshot_1404_04_monthly_toman",
    "rent_snapshot_1404_04_per_sqm_toman",
    "rent_snapshot_1404_04_deposit_toman",
    "rent_snapshot_1404_04_median_area_sqm",
    "rent_change_1404_08_vs_1404_04_pct",
    "gross_yield_1404_08_pct",
    "gross_yield_1404_04_pct",
    "deposit_to_value_1404_08_pct",
    "rent_side_rows_conflicting_district",
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
    return st.median(values) if values else None


def load_sales() -> Dict[str, Dict[str, Any]]:
    rows = list(csv.DictReader(open(KILID_MONTHLY, encoding="utf-8")))
    per: Dict[str, Dict[str, Dict[str, str]]] = {}
    for row in rows:
        per.setdefault(row["district_number"], {})[row["period_code"]] = row

    out: Dict[str, Dict[str, Any]] = {}
    for district, series in per.items():
        levels: Dict[str, Optional[float]] = {}
        for label, start in SALE_WINDOWS:
            months = [series[m] for m in window_months(start) if m in series]
            levels[label] = median([float(r["price_psm_median_toman"]) for r in months])
        current_months = [series[m] for m in window_months(dict(SALE_WINDOWS)[SALE_LEVEL_WINDOW]) if m in series]
        area_name = next(iter(series.values()))["area_name_fa"]
        out[district] = {
            "area_name_fa": area_name,
            "levels": levels,
            "p25": median([float(r["price_psm_p25_toman"]) for r in current_months]),
            "p75": median([float(r["price_psm_p75_toman"]) for r in current_months]),
            "cumulative_pct": ((levels["1405"] / levels["1401"] - 1) * 100)
            if levels.get("1401") and levels.get("1405")
            else None,
            "source": "kilid",
        }
    return out


def load_rents(path: Path, dataset_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    if dataset_id is not None:
        rows = [r for r in rows if r["dataset_id"] == dataset_id]
    per: Dict[str, List[Dict[str, Any]]] = {}
    excluded = 0
    for row in rows:
        district = str(row.get("district_number") or "").strip()
        area = str(row.get("floor_area_sqm") or "").strip()
        rent = str(row.get("rent_toman") or "").strip()
        if not (district.isdigit() and area.isdigit() and rent):
            excluded += 1
            continue
        rent_value = float(rent)
        area_value = float(area)
        per.setdefault(district, []).append(
            {
                "rent": rent_value,
                "deposit": float(row["deposit_toman"]) if str(row.get("deposit_toman") or "").strip() else None,
                "area": area_value,
                "rent_per_sqm": rent_value / area_value,
                "district_conflict": row.get("district_cross_check") == "conflict",
            }
        )
    out: Dict[str, Dict[str, Any]] = {}
    for district, items in per.items():
        deposits = [i["deposit"] for i in items if i["deposit"]]
        out[district] = {
            "listings": len(items),
            "monthly": median([i["rent"] for i in items]),
            "per_sqm": median([i["rent_per_sqm"] for i in items]),
            "deposit": median(deposits),
            "median_area": median([i["area"] for i in items]),
            "excluded_rows": excluded,
            "conflicts": sum(1 for i in items if i["district_conflict"]),
        }
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    sales = load_sales()
    rent_aban = load_rents(RENT_ABAN, "3")
    rent_tir = load_rents(RENT_TIR, None)
    districts = sorted(sales, key=int)

    panel: List[Dict[str, Any]] = []
    for district in districts:
        sale = sales[district]
        level = sale["levels"].get(SALE_LEVEL_WINDOW)
        aban = rent_aban.get(district, {})
        tir = rent_tir.get(district, {})

        row: Dict[str, Any] = {
            "district_number": district,
            "area_name_fa": sale["area_name_fa"],
            "sale_level_1405_toman_per_sqm": level,
            "sale_1401_toman_per_sqm": sale["levels"].get("1401"),
            "sale_1402_toman_per_sqm": sale["levels"].get("1402"),
            "sale_1403_toman_per_sqm": sale["levels"].get("1403"),
            "sale_1404_toman_per_sqm": sale["levels"].get("1404"),
            "sale_p25_1405_toman_per_sqm": sale["p25"],
            "sale_p75_1405_toman_per_sqm": sale["p75"],
            "sale_cumulative_1401_1405_pct": sale["cumulative_pct"],
            "rent_side_rows_conflicting_district": aban.get("conflicts", 0) + tir.get("conflicts", 0),
        }
        for label, snapshot in (("1404_08", aban), ("1404_04", tir)):
            row[f"rent_snapshot_{label}_listings"] = snapshot.get("listings")
            row[f"rent_snapshot_{label}_monthly_toman"] = snapshot.get("monthly")
            row[f"rent_snapshot_{label}_per_sqm_toman"] = snapshot.get("per_sqm")
            row[f"rent_snapshot_{label}_deposit_toman"] = snapshot.get("deposit")
            row[f"rent_snapshot_{label}_median_area_sqm"] = snapshot.get("median_area")

        for label, snapshot in (("1404_08", aban), ("1404_04", tir)):
            per_sqm = snapshot.get("per_sqm")
            row[f"gross_yield_{label}_pct"] = (12 * per_sqm / level * 100) if (per_sqm and level) else None

        deposit = aban.get("deposit")
        area = aban.get("median_area")
        row["deposit_to_value_1404_08_pct"] = (
            deposit / (level * area) * 100 if (deposit and level and area) else None
        )
        row["rent_change_1404_08_vs_1404_04_pct"] = (
            (aban["per_sqm"] / tir["per_sqm"] - 1) * 100 if (aban.get("per_sqm") and tir.get("per_sqm")) else None
        )
        panel.append(row)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "district_sale_rent_panel.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(PANEL_FIELDS), lineterminator="\n")
        writer.writeheader()
        for row in panel:
            writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in PANEL_FIELDS})

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = {
        "generated_at": generated_at,
        "district_count": len(panel),
        "sale": {
            "label": "فروش — قیمت پیشنهادی هر متر مربع",
            "unit": "تومان/م²",
            "source": "Kilid — 22 districts × 60 months (1400-06…1405-05), W1405 window = 1404-06…1405-05",
            "windows": [label for label, _ in SALE_WINDOWS],
            "level_window": SALE_LEVEL_WINDOW,
            "confidence": "OBSERVED (Kilid asking prices) · CALCULATED (window medians)",
        },
        "rent": {
            "label": "اجاره — اجاره‌بهای پیشنهادی آپارتمان میان‌متراژ",
            "unit": "تومان بر متر مربع در ماه",
            "snapshots": [
                {"id": label, "label_fa": label_fa, "note": note}
                for label, label_fa, note in RENT_SNAPSHOTS
            ],
            "source": "دنیای اقتصاد (Donya-e-Eqtesad) asking-rent tables, transcribed by the owner",
            "confidence": "OBSERVED (asking rents, listing-based) · two months only",
        },
        "ratio": {
            "label": "نسبت اجاره به قیمت (بازده ناخالص)",
            "unit": "% در سال",
            "definition": "۱۲ × اجارهٔ ماهانهٔ هر متر مربع ÷ قیمت فروش هر متر مربع",
            "note": "comparison of two observed series — never a conversion of one into the other",
        },
        "districts": [
            {
                "d": int(row["district_number"]),
                "name_fa": row["area_name_fa"],
                "sale": {label: sales[row["district_number"]]["levels"].get(label) for label, _ in SALE_WINDOWS},
                "sale_cum_pct": row["sale_cumulative_1401_1405_pct"],
                "sale_p25": row["sale_p25_1405_toman_per_sqm"],
                "sale_p75": row["sale_p75_1405_toman_per_sqm"],
                "rent": {
                    "1404_08": {
                        "monthly": row["rent_snapshot_1404_08_monthly_toman"],
                        "per_sqm": row["rent_snapshot_1404_08_per_sqm_toman"],
                        "deposit": row["rent_snapshot_1404_08_deposit_toman"],
                        "area": row["rent_snapshot_1404_08_median_area_sqm"],
                        "listings": row["rent_snapshot_1404_08_listings"],
                        "yield_pct": row["gross_yield_1404_08_pct"],
                        "deposit_to_value_pct": row["deposit_to_value_1404_08_pct"],
                    },
                    "1404_04": {
                        "monthly": row["rent_snapshot_1404_04_monthly_toman"],
                        "per_sqm": row["rent_snapshot_1404_04_per_sqm_toman"],
                        "deposit": row["rent_snapshot_1404_04_deposit_toman"],
                        "area": row["rent_snapshot_1404_04_median_area_sqm"],
                        "listings": row["rent_snapshot_1404_04_listings"],
                        "yield_pct": row["gross_yield_1404_04_pct"],
                        "deposit_to_value_pct": (
                            row["rent_snapshot_1404_04_deposit_toman"]
                            / (level * row["rent_snapshot_1404_04_median_area_sqm"])
                            * 100
                        )
                        if (row["rent_snapshot_1404_04_deposit_toman"] and level and row["rent_snapshot_1404_04_median_area_sqm"])
                        else None,
                    },
                },
                "rent_change_pct": row["rent_change_1404_08_vs_1404_04_pct"],
                "rent_district_conflicts": row["rent_side_rows_conflicting_district"],
            }
            for row in panel
        ],
        "caveats": {
            "sale": [
                "قیمت‌های پیشنهادی آگهی‌ها (Kilid)، نه معاملات ثبت‌شده.",
                "همه ارقام اسمی‌اند؛ سری تورم مخزن تا ۱۴۰۱ است، پس تعدیل تورمی برای ۱۴۰۲–۱۴۰۵ محاسبه نشده.",
                "منطقه ۲۰ هشت ماه مدل‌سازی‌شده در پنجرهٔ ۱۴۰۵ دارد.",
            ],
            "rent": [
                "اجاره‌بهای پیشنهادی از جدول‌های دنیای اقتصاد — فقط دو ماه (تیر و آبان ۱۴۰۴)، پس روند اجاره نداریم.",
                "آپارتمان‌های میان‌متراژ؛ رقم اجاره جدای از ودیعه است.",
            ],
            "ratio": [
                "از مقایسهٔ دو سری مشاهده‌شده ساخته شده، نه تبدیل یکی به دیگری.",
                "سمت اجاره (تیر/آبان ۱۴۰۴) و سمت فروش (پنجرهٔ ۱۴۰۴-۰۶ تا ۱۴۰۵-۰۵) ماه‌های متفاوتی دارند.",
                "هر دو سمت «پیشنهادی» هستند؛ این نسبت بازده واقعی بازار نیست.",
            ],
        },
        "inputs": {
            "kilid_monthly": str(KILID_MONTHLY.relative_to(REPO_ROOT)),
            "rent_aban_1404": str(RENT_ABAN.relative_to(REPO_ROOT)),
            "rent_tir_1404": str(RENT_TIR.relative_to(REPO_ROOT)),
            "hashes": {
                str(path.relative_to(REPO_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()[:16]
                for path in (KILID_MONTHLY, RENT_ABAN, RENT_TIR)
            },
        },
    }
    with open(out_dir / "switch_data.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    template = (Path(__file__).resolve().parent / "rent_vs_sale_template.html").read_text(encoding="utf-8")
    html = template.replace("/*__DATA__*/", json.dumps(payload, ensure_ascii=False))
    with open(out_dir / "explorer.html", "w", encoding="utf-8") as handle:
        handle.write(html)

    yields = [row["gross_yield_1404_08_pct"] for row in panel if row["gross_yield_1404_08_pct"]]
    print(f"districts      : {len(panel)} (sale levels + rent snapshots)")
    print(f"gross yield    : median {st.median(yields):.2f}%  range {min(yields):.2f}..{max(yields):.2f}%")
    print(f"sale 1401→1405 : median {st.median([r['sale_cumulative_1401_1405_pct'] for r in panel]):.0f}%")
    print(f"outputs        : {out_dir}/district_sale_rent_panel.csv, switch_data.json, explorer.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
