#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a switchable sale ↔ rent dataset for the 22 districts of Tehran.

Inputs (both already in this repo):

* **sales** — Kilid district series, 22 districts × 60 months (``1400-06``…``1405-05``),
  asking price per m². Cut into five 12-month windows to give the sale side a time
  dimension, and also kept monthly so a rent month can be matched exactly;
* **rents** — three Donya-e-Eqtesad tables, each a snapshot of ordinary apartments with a
  monthly rent and a deposit: Aban 1404 and Tir 1404 (all 22 districts), and Shahrivar 1402
  (**district 22 only**).

What the switch can and cannot show:

* sales: a level per year (five windows) and a five-year change per district;
* rents: a level per snapshot per district — **three dates, so no continuous rent series**;
* the payoff of the switch: the **rent-to-price ratio** (gross yield) per district, computed by
  *comparing two observed series*, never by converting one into the other.

Two ratios are produced and kept apart on purpose: the ratio against the robust 1405 sale
window, and the ratio against Kilid's price in the rent table's **own month**. The second is a
same-month, same-district pairing with no window straddling.

The ratio is a comparison, not a valuation: the rent side is asking rent for a mid-size
apartment, the sale side is asking price per m², and both are listing figures. It is shipped as
indicative, with every input next to it.

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
ARCHIVE = REPO_ROOT / "data" / "raw" / "tehran_housing_market_data"
KILID_MONTHLY = REPO_ROOT / "kilid" / "kilid_data" / "normalized" / "kilid_tehran_sale_price_monthly.csv"
RENT_ABAN = ARCHIVE / "observations" / "rent_observations.csv"
RENT_TIR = ARCHIVE / "sources" / "donya-e-eqtesad_1404-04" / "rent_asking.csv"
RENT_SHAHRIVAR = ARCHIVE / "sources" / "donya-e-eqtesad_1402-06_district-22" / "rent_asking.csv"
RENT_KHORDAD = ARCHIVE / "sources" / "donya-e-eqtesad_1402-03_tehran" / "rent_asking.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "rent_vs_sale"

SALE_WINDOWS: Tuple[Tuple[str, str], ...] = (
    ("1401", "1400-06"),
    ("1402", "1401-06"),
    ("1403", "1402-06"),
    ("1404", "1403-06"),
    ("1405", "1404-06"),
)
SALE_LEVEL_WINDOW = "1405"          # the window used as the robust "current" level

#: Newest first. ``month`` is the Kilid month matched to this snapshot for the same-month ratio.
RENT_SOURCES: Tuple[Dict[str, Any], ...] = (
    {
        "key": "1404_08",
        "month": "1404-08",
        "label_fa": "آبان ۱۴۰۴",
        "note": "جدول آرشیو، مجموعه‌دادهٔ ۳ — هر ۲۲ منطقه",
        "path": RENT_ABAN,
        "dataset_id": "3",
    },
    {
        "key": "1404_04",
        "month": "1404-04",
        "label_fa": "تیر ۱۴۰۴",
        "note": "جدول دنیای اقتصاد، بازنویسی مالک — هر ۲۲ منطقه",
        "path": RENT_TIR,
        "dataset_id": None,
    },
    {
        "key": "1402_06",
        "month": "1402-06",
        "label_fa": "شهریور ۱۴۰۲",
        "note": "جدول دنیای اقتصاد — فقط منطقهٔ ۲۲",
        "path": RENT_SHAHRIVAR,
        "dataset_id": None,
    },
    {
        "key": "1402_03",
        "month": "1402-03",
        "label_fa": "خرداد ۱۴۰۲",
        "note": "جدول دنیای اقتصاد — نمونهٔ پراکنده در ۱۱ منطقه، نه گزارش منطقه‌به‌منطقه",
        "path": RENT_KHORDAD,
        "dataset_id": None,
    },
)

BASE_FIELDS: Tuple[str, ...] = (
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
)


def yield_pct(rent_per_sqm: Optional[float], sale_per_sqm: Optional[float]) -> Optional[float]:
    if not rent_per_sqm or not sale_per_sqm:
        return None
    return 12 * rent_per_sqm / sale_per_sqm * 100


def pct_change(before: Optional[float], after: Optional[float]) -> Optional[float]:
    if not before or not after:
        return None
    return (after / before - 1) * 100


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
            # kept monthly so a rent table's own month can be matched exactly
            "monthly": {month: float(row["price_psm_median_toman"]) for month, row in series.items()},
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


def build_panel() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    sales = load_sales()
    rents: Dict[str, Dict[str, Dict[str, Any]]] = {}
    skipped = 0
    for source in RENT_SOURCES:
        rents[source["key"]] = load_rents(source["path"], source["dataset_id"])
    keys = [s["key"] for s in RENT_SOURCES]
    months = {s["key"]: s["month"] for s in RENT_SOURCES}

    panel: List[Dict[str, Any]] = []
    for district in sorted(sales, key=int):
        sale = sales[district]
        level = sale["levels"].get(SALE_LEVEL_WINDOW)
        row: Dict[str, Any] = {
            "district_number": district,
            "area_name_fa": sale["area_name_fa"],
            "sale_level_1405_toman_per_sqm": level,
            "sale_p25_1405_toman_per_sqm": sale["p25"],
            "sale_p75_1405_toman_per_sqm": sale["p75"],
            "sale_cumulative_1401_1405_pct": sale["cumulative_pct"],
        }
        for label, _ in SALE_WINDOWS:
            row[f"sale_{label}_toman_per_sqm"] = sale["levels"].get(label)

        # which rent snapshots this district appears in, newest first
        present: List[str] = []
        for key in keys:
            snapshot = rents[key].get(district)
            if snapshot is None:
                continue
            present.append(key)
            same_month = sale["monthly"].get(months[key])
            row[f"rent_snapshot_{key}_listings"] = snapshot["listings"]
            row[f"rent_snapshot_{key}_monthly_toman"] = snapshot["monthly"]
            row[f"rent_snapshot_{key}_per_sqm_toman"] = snapshot["per_sqm"]
            row[f"rent_snapshot_{key}_deposit_toman"] = snapshot["deposit"]
            row[f"rent_snapshot_{key}_median_area_sqm"] = snapshot["median_area"]
            row[f"rent_snapshot_{key}_excluded_rows"] = snapshot["excluded_rows"]
            row[f"sale_same_month_{key}_toman_per_sqm"] = same_month
            row[f"gross_yield_{key}_pct"] = yield_pct(snapshot["per_sqm"], level)
            row[f"gross_yield_{key}_same_month_pct"] = yield_pct(snapshot["per_sqm"], same_month)

        for newer, older in zip(present, present[1:]):
            row[f"rent_change_{newer}_vs_{older}_pct"] = pct_change(
                rents[older][district]["per_sqm"], rents[newer][district]["per_sqm"]
            )

        aban = rents["1404_08"].get(district, {})
        deposit, area = aban.get("deposit"), aban.get("median_area")
        row["deposit_to_value_1404_08_pct"] = (
            deposit / (level * area) * 100 if (deposit and level and area) else None
        )
        row["rent_side_rows_conflicting_district"] = sum(
            rents[key].get(district, {}).get("conflicts", 0) for key in keys
        )
        panel.append(row)

    meta = {
        "sale_windows": [label for label, _ in SALE_WINDOWS],
        "rent_keys": keys,
        "rent_months": months,
        "excluded_rent_rows": {
            key: sum(s["excluded_rows"] for s in rents[key].values()) for key in keys
        },
    }
    return panel, meta


def panel_fields(panel: List[Dict[str, Any]]) -> List[str]:
    fields = list(BASE_FIELDS)
    seen = set(fields)
    for row in panel:
        for key in row:
            if key not in seen:
                fields.append(key)
                seen.add(key)
    return fields


def build_payload(panel: List[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, Any]:
    keys = meta["rent_keys"]
    months = meta["rent_months"]
    snapshots = []
    for source in RENT_SOURCES:
        key = source["key"]
        snapshots.append(
            {
                "id": key.replace("_", "-"),
                "key": key,
                "month": source["month"],
                "label_fa": source["label_fa"],
                "note": source["note"],
                "district_count": sum(
                    1 for row in panel if row.get(f"rent_snapshot_{key}_per_sqm_toman") is not None
                ),
            }
        )

    districts = []
    for row in panel:
        rent: Dict[str, Any] = {}
        for key in keys:
            if row.get(f"rent_snapshot_{key}_per_sqm_toman") is None:
                continue
            deposit = row.get(f"rent_snapshot_{key}_deposit_toman")
            area = row.get(f"rent_snapshot_{key}_median_area_sqm")
            level = row.get("sale_level_1405_toman_per_sqm")
            rent[key] = {
                "monthly": row.get(f"rent_snapshot_{key}_monthly_toman"),
                "per_sqm": row.get(f"rent_snapshot_{key}_per_sqm_toman"),
                "deposit": deposit,
                "area": area,
                "listings": row.get(f"rent_snapshot_{key}_listings"),
                "yield_pct": row.get(f"gross_yield_{key}_pct"),
                "yield_same_month_pct": row.get(f"gross_yield_{key}_same_month_pct"),
                "sale_same_month": row.get(f"sale_same_month_{key}_toman_per_sqm"),
                "deposit_to_value_pct": deposit / (level * area) * 100 if (deposit and level and area) else None,
            }
        changes = {}
        for newer, older in zip(keys, keys[1:]):
            value = row.get(f"rent_change_{newer}_vs_{older}_pct")
            if value is not None:
                changes[f"{newer}_vs_{older}"] = value
        districts.append(
            {
                "d": int(row["district_number"]),
                "name_fa": row["area_name_fa"],
                "sale": {label: row.get(f"sale_{label}_toman_per_sqm") for label, _ in SALE_WINDOWS},
                "sale_cum_pct": row["sale_cumulative_1401_1405_pct"],
                "sale_p25": row["sale_p25_1405_toman_per_sqm"],
                "sale_p75": row["sale_p75_1405_toman_per_sqm"],
                "rent": rent,
                "rent_changes": changes,
                "rent_district_conflicts": row["rent_side_rows_conflicting_district"],
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "district_count": len(panel),
        "sale": {
            "label": "فروش — قیمت پیشنهادی هر متر مربع",
            "unit": "تومان/م²",
            "source": "Kilid — ۲۲ منطقه × ۶۰ ماه (۱۴۰۰-۰۶ تا ۱۴۰۵-۰۵)؛ پنجرهٔ ۱۴۰۵ = ۱۴۰۴-۰۶ تا ۱۴۰۵-۰۵",
            "windows": meta["sale_windows"],
            "level_window": SALE_LEVEL_WINDOW,
            "confidence": "OBSERVED (Kilid asking prices) · CALCULATED (window medians)",
        },
        "rent": {
            "label": "اجاره — اجاره‌بهای پیشنهادی آپارتمان میان‌متراژ",
            "unit": "تومان بر متر مربع در ماه",
            "snapshots": snapshots,
            "source": "دنیای اقتصاد — چهار جدول اجاره: خرداد ۱۴۰۲، شهریور ۱۴۰۲، تیر ۱۴۰۴، آبان ۱۴۰۴",
            "confidence": "OBSERVED (asking rents, listing-based) · four dates only",
        },
        "ratio": {
            "label": "نسبت اجاره به قیمت (بازده ناخالص)",
            "unit": "% در سال",
            "definition": "۱۲ × اجارهٔ ماهانهٔ هر متر مربع ÷ قیمت فروش هر متر مربع",
            "note": "مقایسهٔ دو سری مشاهده‌شده، نه تبدیل یکی به دیگری. «هم‌ماه» یعنی قیمت فروش Kilid در همان ماهِ جدول اجاره.",
        },
        "districts": districts,
        "caveats": {
            "sale": [
                "قیمت‌های پیشنهادی آگهی‌ها (Kilid)، نه معاملات ثبت‌شده.",
                "همه ارقام اسمی‌اند؛ سری تورم مخزن تا ۱۴۰۱ است، پس تعدیل تورمی برای ۱۴۰۲–۱۴۰۵ محاسبه نشده.",
                "منطقه ۲۰ هشت ماه مدل‌سازی‌شده در پنجرهٔ ۱۴۰۵ دارد.",
            ],
            "rent": [
                "اجاره‌بها چهار تاریخ دارد: آبان ۱۴۰۴ و تیر ۱۴۰۴ برای هر ۲۲ منطقه، و دو جدول پراکنده در خرداد و شهریور ۱۴۰۲ که به‌ترتیب ۱۱ و ۱ منطقه را پوشش می‌دهند. روند پیوسته نیست — اتصال نقطه‌به‌نقطه نکنید.",
                "در جدول شهریور ۱۴۰۲، ۲۷ ردیف از ۴۵ ردیف اصلا اجاره نداشتند؛ میانهٔ اجارهٔ آن جدول روی ۱۷ ردیف است.",
                "در جدول خرداد ۱۴۰۲، ۱۸ ردیف از ۳۳ ردیف اجاره نداشتند و ردیف‌ها آگهی‌های پراکنده‌اند، نه میانگین منطقه.",
                "آپارتمان‌های میان‌متراژ؛ اجاره جدای از ودیعه است و سطح ودیعه بین جدول‌ها یکسان نیست.",
            ],
            "ratio": [
                "از مقایسهٔ دو سری مشاهده‌شده ساخته شده، نه تبدیل یکی به دیگری.",
                "دو جدول ۱۴۰۲ پراکنده‌اند و نسبت آن‌ها فقط روی همان مناطق محاسبه می‌شود: شهریور ۱۴۰۲ فقط منطقهٔ ۲۲، خرداد ۱۴۰۲ فقط ۷ منطقه از ۱۱ منطقه‌ای که در آن جدول آمده‌اند.",
                "هر دو سمت «پیشنهادی» هستند؛ این نسبت بازده واقعی بازار نیست.",
            ],
        },
        "inputs": {
            "kilid_monthly": str(KILID_MONTHLY.relative_to(REPO_ROOT)),
            "rent_snapshots": {s["key"]: str(s["path"].relative_to(REPO_ROOT)) for s in RENT_SOURCES},
            "hashes": {
                str(path.relative_to(REPO_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()[:16]
                for path in (KILID_MONTHLY, *[s["path"] for s in RENT_SOURCES])
            },
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    panel, meta = build_panel()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = panel_fields(panel)
    with open(out_dir / "district_sale_rent_panel.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in panel:
            writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in fields})

    payload = build_payload(panel, meta)
    with open(out_dir / "switch_data.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    template = (Path(__file__).resolve().parent / "rent_vs_sale_template.html").read_text(encoding="utf-8")
    with open(out_dir / "explorer.html", "w", encoding="utf-8") as handle:
        handle.write(template.replace("/*__DATA__*/", json.dumps(payload, ensure_ascii=False)))

    for snapshot in payload["rent"]["snapshots"]:
        key = snapshot["key"]
        window = [row[f"gross_yield_{key}_pct"] for row in panel if row.get(f"gross_yield_{key}_pct")]
        same = [
            row[f"gross_yield_{key}_same_month_pct"]
            for row in panel
            if row.get(f"gross_yield_{key}_same_month_pct")
        ]
        if same:
            print(
                f"  {snapshot['label_fa']:12} {snapshot['district_count']:2} districts"
                f"  same-month ratio {st.median(same):.2f}%"
                + (f"  (1405-window {st.median(window):.2f}%)" if window else "")
            )
    print(f"  panel columns: {len(fields)}")
    print(f"  outputs: {out_dir}/district_sale_rent_panel.csv, switch_data.json, explorer.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
