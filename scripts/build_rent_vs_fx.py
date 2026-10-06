#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اجاره در برابر ارز — تولید `rent-vs-fx.html`.

چهار سری روی یک نمودار دوبار محوره، سالانه، ۱۳۹۰ تا ۱۴۰۰:

* **نرخ ارز آزاد** (محور چپ، شاخص) — ورودی کارفرما، `data/rent_vs_fx/fx_inflation_annual.csv`
* **شاخص تورم (CPI)** (محور چپ، شاخص) — از زنجیرهٔ `inflation_pct` ساخته می‌شود، نه ورودی مستقیم
* **اجارهٔ تهران** (محور چپ، شاخص) — `data/annual.csv`، متغیر `tehran_rent` (منبع S2)
* **اجاره به دلار** (محور راست، دلار بر متر مربع) — اجاره ÷ نرخ ارز، محاسبه‌شده

Inputs:

* ``data/annual.csv`` — ردیف‌های ``tehran_rent`` (تومان بر متر مربع در ماه، بانک مرکزی).
* ``data/rent_vs_fx/fx_inflation_annual.csv`` — سری سالانهٔ ارز آزاد و تورم سالانه (S16،
  project-supplied). این فایل ورودی دستی است و ویرایشش فقط از راه همین فایل مجاز است.

Method (هر گام از همین دو ورودی بازتولیدپذیر است):

1. هر دو سری به بازهٔ مشترک ۱۳۹۰…۱۴۰۰ بریده و روی سال‌ها **کامل** تطبیق داده می‌شوند؛ اگر سالی در
   یک سری نباشد، اسکریپت با خطا متوقف می‌شود — هیچ درون‌یابی یا صفرگذاری‌ای انجام نمی‌شود؛
2. ``*_index = مقدار ÷ مقدار ۱۳۹۰ × ۱۰۰`` برای ارز و اجاره؛
3. ``cpi_index`` زنجیرهٔ ``inflation_pct`` است: ``cpi[y] = cpi[y-1] x (1 + inflation[y])``،
   پایهٔ ۱۳۹۰ = ۱۰۰، و هر گام به **یک رقم اعشار** گرد می‌شود. (این ستون در سند تحویل اشتباه بود:
   گام ۱۳۹۱ با تورم ۱۳۹۰ ساخته شده بود و کل ستون را حدود ۷٪ کم‌برآورد می‌کرد.)
4. ``rent_usd_m2 = rent_toman_m2 / fx_toman_usd`` — نسبت میان دو سری مشاهده‌شده، نه تبدیل یکی به دیگری.

Outputs (``data/rent_vs_fx/``):

    rent_annual.csv    نمای فقط‌اجاره (قالب قبلی، دست‌نخورده)
    panel_annual.csv   پنل کامل ۱۱ سال — سطح، شاخص، رشد
    rent_data.json     همان داده، به‌شکل مصرفی صفحه
    README.md          روش، منبع، و آنچه این نمودار نمی‌گوید
    rent-vs-fx.html    صفحهٔ مستقل در ریشهٔ مخزن (قالب: scripts/rent_vs_fx_template.html)

Usage:
    python3 scripts/build_rent_vs_fx.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics as st
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RENT_INPUT = REPO_ROOT / "data" / "annual.csv"
DEFAULT_MACRO_INPUT = REPO_ROOT / "data" / "rent_vs_fx" / "fx_inflation_annual.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "rent_vs_fx"
DEFAULT_PAGE = REPO_ROOT / "rent-vs-fx.html"
TEMPLATE = Path(__file__).resolve().parent / "rent_vs_fx_template.html"

#: The annual Tehran rent series inside data/annual.csv.
RENT_VARIABLE = "tehran_rent"
FIRST_YEAR = 1390
LAST_YEAR = 1400

#: The index base is the first year of the window — the page never re-bases.
BASE_YEAR = FIRST_YEAR

#: Axis domains from the handoff. The chart widens them if a visible value overflows.
LEFT_DOMAIN: Tuple[float, float] = (0.0, 2500.0)
RIGHT_DOMAIN: Tuple[float, float] = (0.0, 12.0)

#: Contextual markers from the handoff. Editorial context, not data.
ANNOTATIONS: Tuple[Dict[str, Any], ...] = (
    {"year": 1397, "n": 1, "label_fa": "خروج آمریکا از برجام"},
    {"year": 1399, "n": 2, "label_fa": "کرونا و انتخابات آمریکا"},
)

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

RENT_FIELDS = (
    "year",
    "year_label_fa",
    "rent_toman_m2",
    "rent_index_1390",
    "yoy_pct",
    "gap_years",
    "source_id",
)

PANEL_FIELDS = (
    "year",
    "year_label_fa",
    "rent_toman_m2",
    "rent_index_1390",
    "rent_yoy_pct",
    "fx_toman_usd",
    "fx_index_1390",
    "fx_yoy_pct",
    "inflation_pct",
    "cpi_index_1390",
    "rent_usd_m2",
    "rent_usd_yoy_pct",
    "source_id_rent",
    "source_id_fx",
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fa(number: Any) -> str:
    return str(number).translate(FA_DIGITS)


def round1(value: float) -> float:
    """One-decimal rounding, so 20.45 does not print as 20.4."""
    return float(round(value + 1e-9, 1))


def load_rent(path: Path) -> Tuple[Dict[int, float], Optional[str], int]:
    """``data/annual.csv`` -> ({year: rent}, unit, rows in the file)."""
    levels: Dict[int, float] = {}
    unit: Optional[str] = None
    rows = 0
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows += 1
            if row["variable"] != RENT_VARIABLE:
                continue
            year = int(row["year"])
            if not FIRST_YEAR <= year <= LAST_YEAR:
                continue
            if year in levels:
                raise ValueError(f"duplicate {RENT_VARIABLE} row for {year} in {path}")
            levels[year] = float(row["value"])
            unit = unit or row["unit"]
    if not levels:
        raise ValueError(f"no {RENT_VARIABLE} rows in {FIRST_YEAR}…{LAST_YEAR} in {path}")
    return levels, unit, rows


def load_macro(path: Path) -> Tuple[Dict[int, Dict[str, Any]], int]:
    """``fx_inflation_annual.csv`` -> ({year: {fx, inflation, source_id}}, rows in the file)."""
    macro: Dict[int, Dict[str, Any]] = {}
    rows = 0
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows += 1
            year = int(row["year"])
            if not FIRST_YEAR <= year <= LAST_YEAR:
                continue
            if year in macro:
                raise ValueError(f"duplicate macro row for {year} in {path}")
            macro[year] = {
                "fx": float(row["fx_toman_usd"]),
                "inflation": float(row["inflation_pct"]),
                "source_id": row["source_id"],
            }
    if not macro:
        raise ValueError(f"no macro rows in {FIRST_YEAR}…{LAST_YEAR} in {path}")
    return macro, rows


def build_panel(rent: Dict[int, float], macro: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One row per year with every derived column. No interpolation, no gap filling."""
    years = sorted(set(rent) | set(macro))
    missing_rent = [y for y in years if y not in rent]
    missing_macro = [y for y in years if y not in macro]
    if missing_rent:
        raise ValueError(f"rent is missing for {missing_rent}; every year must exist on both sides")
    if missing_macro:
        raise ValueError(f"fx/inflation is missing for {missing_macro}; every year must exist on both sides")

    fx = {year: macro[year]["fx"] for year in years}
    rent_usd = {year: rent[year] / fx[year] for year in years}
    rent_base, fx_base = rent[BASE_YEAR], fx[BASE_YEAR]

    def yoy(series: Dict[int, float], year: int) -> Optional[float]:
        previous = series.get(year - 1)
        return None if previous is None else round1((series[year] / previous - 1) * 100)

    # the CPI index is a chain of inflation_pct, rounded to one decimal at each step
    cpi: Dict[int, float] = {BASE_YEAR: 100.0}
    for year in years:
        if year != BASE_YEAR:
            cpi[year] = round1(cpi[year - 1] * (1 + macro[year]["inflation"] / 100))

    panel: List[Dict[str, Any]] = []
    for year in years:
        panel.append(
            {
                "year": year,
                "label_fa": fa(year),
                "rent": rent[year],
                "rent_index": rent[year] / rent_base * 100,
                "rent_yoy_pct": yoy(rent, year),
                "fx": fx[year],
                "fx_index": fx[year] / fx_base * 100,
                "fx_yoy_pct": yoy(fx, year),
                "inflation_pct": macro[year]["inflation"],
                "cpi_index": cpi[year],
                "rent_usd": rent_usd[year],
                "rent_usd_yoy_pct": yoy(rent_usd, year),
                "source_id_rent": "S2",
                "source_id_fx": macro[year]["source_id"],
            }
        )
    return panel


def growth_stats(panel: List[Dict[str, Any]]) -> Dict[str, Any]:
    first, last = panel[0], panel[-1]
    fx_multiple = last["fx_index"] / first["fx_index"]
    cpi_multiple = last["cpi_index"] / first["cpi_index"]
    rent_multiple = last["rent_index"] / first["rent_index"]
    cheapest = min(panel, key=lambda entry: entry["rent_usd"])
    return {
        "first_year": first["year"],
        "last_year": last["year"],
        "span_years": last["year"] - first["year"],
        "first": {
            "fx": first["fx"], "fx_index": first["fx_index"], "cpi_index": first["cpi_index"],
            "rent": first["rent"], "rent_index": first["rent_index"], "rent_usd": first["rent_usd"],
        },
        "last": {
            "fx": last["fx"], "fx_index": last["fx_index"], "cpi_index": last["cpi_index"],
            "rent": last["rent"], "rent_index": last["rent_index"], "rent_usd": last["rent_usd"],
        },
        "fx_multiple": fx_multiple,
        "cpi_multiple": cpi_multiple,
        "rent_multiple": rent_multiple,
        # how far FX has pulled away from general inflation — the width of the "scissors"
        "fx_over_cpi": fx_multiple / cpi_multiple,
        "rent_usd_multiple": last["rent_usd"] / first["rent_usd"],
        # rent against general inflation: negative means rent rose slower than CPI
        "rent_vs_cpi_pct": (rent_multiple / cpi_multiple - 1) * 100,
        "rent_usd_drop_pct": (last["rent_usd"] / first["rent_usd"] - 1) * 100,
        "min_rent_usd": cheapest["rent_usd"],
        "min_rent_usd_year": cheapest["year"],
        "min_rent_usd_year_label_fa": cheapest["label_fa"],
        "median_inflation_pct": round1(st.median([entry["inflation_pct"] for entry in panel])),
    }


def build_payload(
    panel: List[Dict[str, Any]],
    rent_input: Path,
    macro_input: Path,
    rent_rows: int,
    macro_rows: int,
    rent_unit: Optional[str],
) -> Dict[str, Any]:
    years = [
        {
            "year": entry["year"],
            "label_fa": entry["label_fa"],
            "values": {
                "fx": entry["fx_index"],
                "cpi": entry["cpi_index"],
                "rent": entry["rent_index"],
                "usd": entry["rent_usd"],
            },
            "levels": {"fx": entry["fx"], "rent": entry["rent"]},
            "inflation_pct": entry["inflation_pct"],
            "yoy_pct": {
                "fx": entry["fx_yoy_pct"],
                "rent": entry["rent_yoy_pct"],
                "usd": entry["rent_usd_yoy_pct"],
            },
            "source_id": {"fx": entry["source_id_fx"], "rent": entry["source_id_rent"]},
        }
        for entry in panel
    ]
    return {
        "meta": {
            "title_fa": "اجاره در برابر ارز — تهران",
            "base_year": BASE_YEAR,
            "base_label_fa": fa(BASE_YEAR),
            "window": {
                "first_year": panel[0]["year"],
                "last_year": panel[-1]["year"],
                "count": len(panel),
                "first_label_fa": panel[0]["label_fa"],
                "last_label_fa": panel[-1]["label_fa"],
            },
            "rent_unit": rent_unit,
            "left_axis": {
                "label_fa": f"شاخص ({fa(BASE_YEAR)} = ۱۰۰)",
                "domain": list(LEFT_DOMAIN),
                "tick": 500.0,
            },
            "right_axis": {
                "label_fa": "اجاره به دلار (دلار بر متر مربع در ماه)",
                "domain": list(RIGHT_DOMAIN),
                "tick": 2.0,
            },
            "inputs": {
                "rent": {
                    "path": str(rent_input.relative_to(REPO_ROOT)),
                    "sha256": sha256_of(rent_input),
                    "rows_in_file": rent_rows,
                    "variable": RENT_VARIABLE,
                    "years_used": len(panel),
                    "source_id": "S2",
                },
                "macro": {
                    "path": str(macro_input.relative_to(REPO_ROOT)),
                    "sha256": sha256_of(macro_input),
                    "rows_in_file": macro_rows,
                    "years_used": len(panel),
                    "source_id": panel[0]["source_id_fx"],
                },
            },
            "annotations": [dict(annotation) for annotation in ANNOTATIONS],
            "method": [
                "اجاره از data/annual.csv (متغیر tehran_rent، بانک مرکزی، S2) و ارز و تورم از data/rent_vs_fx/fx_inflation_annual.csv (S16) خوانده می‌شود.",
                f"هر دو سری به بازهٔ {fa(FIRST_YEAR)}…{fa(LAST_YEAR)} بریده و سال‌به‌سال تطبیق داده می‌شوند؛ اگر سالی در یک سری نباشد اسکریپت متوقف می‌شود — نه صفرگذاری و نه درون‌یابی.",
                f"شاخص = مقدار ÷ مقدار {fa(BASE_YEAR)} × ۱۰۰، با پایهٔ ثابت {fa(BASE_YEAR)} برای ارز و اجاره؛ صفحه این پایه را تغییر نمی‌دهد.",
                "شاخص تورم زنجیرهٔ تورم سالانه است: cpi[y] = cpi[y−۱] × (۱ + تورم[y])، با گردکردن یک‌رقمی در هر گام.",
                "اجاره به دلار = اجاره (تومان بر متر مربع) ÷ نرخ ارز؛ نسبتی میان دو سری مشاهده‌شده، نه تبدیل یکی به دیگری.",
            ],
            "stats": growth_stats(panel),
        },
        "series": [
            {
                "key": "fx",
                "label_fa": "نرخ ارز آزاد",
                "axis": "left",
                "dash": "",
                "width": 3,
                "level_label_fa": "نرخ دلار آزاد",
                "level_digits": 0,
                "level_suffix_fa": "تومان",
                "source_id": panel[0]["source_id_fx"],
            },
            {
                "key": "cpi",
                "label_fa": "شاخص تورم",
                "axis": "left",
                "dash": "6 4",
                "width": 2,
                "level_label_fa": "تورم سالانه",
                "level_digits": 1,
                "level_suffix_fa": "٪",
                "source_id": panel[0]["source_id_fx"],
            },
            {
                "key": "rent",
                "label_fa": "اجارهٔ تهران",
                "axis": "left",
                "dash": "",
                "width": 2,
                "level_label_fa": "اجارهٔ ماهانهٔ هر متر مربع",
                "level_digits": 0,
                "level_suffix_fa": "تومان",
                "source_id": "S2",
            },
            {
                "key": "usd",
                "label_fa": "اجاره به دلار",
                "axis": "right",
                "dash": "2 3",
                "width": 2,
                "level_label_fa": "اجاره به دلار",
                "level_digits": 1,
                "level_suffix_fa": "دلار بر متر مربع",
                "source_id": "S2 ÷ S16",
            },
        ],
        "years": years,
        "sources": [
            "بانک مرکزی ایران (S2) — میانگین اجارهٔ ماهانهٔ هر متر مربع در تهران؛ ارقام از research workbook پروژه.",
            "نرخ ارز آزاد و تورم سالانه (S16) — project-supplied، تحویل‌شده ۲۰۲۶-۱۰-۰۶؛ تعریف نرخ ارز در سند تحویل نیامده.",
            "شناسه و یادداشت منابع: data/sources.csv",
        ],
        "caveats": [
            "تعریف سری ارز در سند تحویل نیامده: نه «میانگین سالانه» است و نه به‌صراحت «پایان سال». ارقام با نرخ‌های پایان‌سال آزاد سازگارند. اگر مبنا میانگین سالانه باشد، ضریب رشد ارز از ×۲۳٫۳ به حدود ×۱۵ تغییر می‌کند و پهنای شکاف هم با آن — پیش از انتشار باید تعریف تأیید شود.",
            "ستون شاخص CPI در سند تحویل با ستون تورم خودش نمی‌ساخت: گام ۱۳۹۱ با تورم ۱۳۹۰ (۲۱٫۵٪) ساخته شده بود و کل ستون حدود ۷٪ کم‌برآورد می‌شد (۱۴۰۰: ۸۰۴٫۳ در برابر ۸۶۳٫۸). این صفحه شاخص را از خود تورم بازمی‌سازد؛ ستون تورم دست‌نخورده مانده است.",
            "«اجاره به دلار» نسبت دو سری مشاهده‌شده است، نه تبدیل اجاره از تومان به دلار. افت آن می‌تواند از رشد ارز بیاید، از کندی اجاره، یا از هر دو؛ نمودار سهم هر کدام را جدا نمی‌کند.",
            "اجاره و ارز دو سری مستقل با دو منبع مستقل‌اند و هیچ‌جا به هم تبدیل نشده‌اند؛ «اجاره به دلار» فقط نسبت آن دو است.",
            "این سری ارز با جدول ارز/تورم پروژه در data/housing_price/fx_cpi_quarterly.csv یکی نیست: آن جدول از تابستان ۱۴۰۰ آغاز می‌شود و نرخ‌هایش فصلی و گردشده‌اند (زمستان ۱۴۰۰ آنجا ۲۶٬۰۰۰ است که با میزان پایان‌سال این سری می‌خواند، ولی مسیر میانی دو سری یکی نیست).",
            "سری اجاره «میانگین تهران» بانک مرکزی است (S2)، نه سری فصلی ۲۲ منطقه (مرکز آمار/طیبی، data/tehran_rent_district.csv که در شکل ۲ صفحهٔ اصلی به کار رفته). سطح این دو یکی نیست و سری بانک مرکزی حدود ۱٫۲ تا ۱٫۴۵ برابر سری منطقه‌ای است.",
            "علامت‌های ۱۳۹۷ و ۱۳۹۹ روی نمودار زمینهٔ تفسیری‌اند، نه داده: از سری‌ها استخراج نشده‌اند و هم‌زمانی، علیت نیست. جهش ارز می‌تواند دلایل دیگری هم داشته باشد.",
            "همهٔ ارقام سالانه‌اند: نوسان درون‌سال دیده نمی‌شود و «سال» یعنی یک عدد در هر سال. ارز و اجاره نامی‌اند و شاخص‌هایشان تورم را کنار نمی‌گذارد؛ تنها مقایسهٔ حقیقی روی صفحه، کارت «اجاره در برابر تورم» است که شاخص اجاره را با شاخص CPI می‌سنجد.",
            "ارقام ارز و تورم از سند تحویل پروژه آمده‌اند و پیش از انتشار عمومی باید با گزارش رسمی بانک مرکزی مقابله شوند.",
        ],
    }


def write_rent_csv(path: Path, panel: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RENT_FIELDS), lineterminator="\n")
        writer.writeheader()
        for entry in panel:
            writer.writerow(
                {
                    "year": entry["year"],
                    "year_label_fa": entry["label_fa"],
                    "rent_toman_m2": f"{entry['rent']:g}",
                    "rent_index_1390": f"{entry['rent_index']:.1f}",
                    "yoy_pct": "" if entry["rent_yoy_pct"] is None else f"{entry['rent_yoy_pct']:.1f}",
                    "gap_years": "",
                    "source_id": entry["source_id_rent"],
                }
            )


def write_panel_csv(path: Path, panel: List[Dict[str, Any]]) -> None:
    def blank(value: Optional[float]) -> str:
        return "" if value is None else f"{value:.1f}"

    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(PANEL_FIELDS), lineterminator="\n")
        writer.writeheader()
        for entry in panel:
            writer.writerow(
                {
                    "year": entry["year"],
                    "year_label_fa": entry["label_fa"],
                    "rent_toman_m2": f"{entry['rent']:g}",
                    "rent_index_1390": f"{entry['rent_index']:.1f}",
                    "rent_yoy_pct": blank(entry["rent_yoy_pct"]),
                    "fx_toman_usd": f"{entry['fx']:g}",
                    "fx_index_1390": f"{entry['fx_index']:.1f}",
                    "fx_yoy_pct": blank(entry["fx_yoy_pct"]),
                    "inflation_pct": f"{entry['inflation_pct']:.1f}",
                    "cpi_index_1390": f"{entry['cpi_index']:.1f}",
                    "rent_usd_m2": f"{entry['rent_usd']:.3f}",
                    "rent_usd_yoy_pct": blank(entry["rent_usd_yoy_pct"]),
                    "source_id_rent": entry["source_id_rent"],
                    "source_id_fx": entry["source_id_fx"],
                }
            )


def write_readme(path: Path, payload: Dict[str, Any], panel: List[Dict[str, Any]]) -> None:
    meta = payload["meta"]
    stats = meta["stats"]
    first, last = stats["first"], stats["last"]
    lines = [
        "# اجاره در برابر ارز — واگرایی ۱۳۹۰–۱۴۰۰",
        "",
        "چهار سری روی یک نمودار، سالانه، از "
        f"**{meta['window']['first_label_fa']}** تا **{meta['window']['last_label_fa']}** "
        f"({fa(meta['window']['count'])} نقطه):",
        "",
        "| سری | محور | منبع |",
        "| --- | --- | --- |",
        "| نرخ ارز آزاد (شاخص) | چپ | S16 — project-supplied |",
        "| شاخص تورم CPI (شاخص) | چپ | S16 — زنجیرهٔ تورم سالانه |",
        "| اجارهٔ تهران (شاخص) | چپ | S2 — بانک مرکزی |",
        "| اجاره به دلار | راست | نسبت S2 ÷ S16 |",
        "",
        "صفحه: `rent-vs-fx.html` در ریشهٔ مخزن (داده درون‌صفحه، بدون سرور).",
        "",
        "## شکاف قیچی‌ای",
        "",
        "| سری | ۱۳۹۰ | ۱۴۰۰ | ضریب رشد |",
        "| --- | ---: | ---: | ---: |",
        f"| نرخ ارز آزاد | {first['fx_index']:,.1f} | {last['fx_index']:,.1f} | ×{stats['fx_multiple']:,.2f} |",
        f"| شاخص تورم | {first['cpi_index']:,.1f} | {last['cpi_index']:,.1f} | ×{stats['cpi_multiple']:,.2f} |",
        f"| اجارهٔ تهران | {first['rent_index']:,.1f} | {last['rent_index']:,.1f} | ×{stats['rent_multiple']:,.2f} |",
        f"| اجاره به دلار | {first['rent_usd']:,.1f} | {last['rent_usd']:,.1f} | ×{stats['rent_usd_multiple']:,.2f} |",
        "",
        f"ارز **{stats['fx_over_cpi']:,.2f} برابر** تورم رشد کرده است؛ اجاره در همین بازه "
        f"**{abs(stats['rent_vs_cpi_pct']):,.0f}٪ کمتر** از تورم رشد کرده، یعنی اجارهٔ حقیقی در برابر تورم عمومی "
        f"عقب افتاده. اجاره به دلار از {first['rent_usd']:,.1f} به {last['rent_usd']:,.1f} دلار رسیده "
        f"({stats['rent_usd_drop_pct']:,.0f}٪)؛ کمترین مقدارش {stats['min_rent_usd']:,.1f} دلار در "
        f"{stats['min_rent_usd_year_label_fa']} بوده است.",
        "",
        "## روش",
        "",
        *[f"{index}. {step}" for index, step in enumerate(meta["method"], start=1)],
        "",
        "## جدول سال‌به‌سال",
        "",
        "| سال | ارز (تومان) | شاخص ارز | تورم | شاخص CPI | اجاره (تومان/م²) | شاخص اجاره | اجاره (دلار/م²) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for entry in panel:
        lines.append(
            f"| {entry['label_fa']} | {entry['fx']:,.0f} | {entry['fx_index']:,.1f} | {entry['inflation_pct']:,.1f}٪ | "
            f"{entry['cpi_index']:,.1f} | {entry['rent']:,.0f} | {entry['rent_index']:,.1f} | {entry['rent_usd']:,.1f} |"
        )
    lines += [
        "",
        "## ستون‌های `panel_annual.csv`",
        "",
        "* `rent_toman_m2`, `rent_index_1390`, `rent_yoy_pct` — سری اجاره، شاخص و رشد سالانهٔ آن؛",
        "* `fx_toman_usd`, `fx_index_1390`, `fx_yoy_pct` — سری ارز، شاخص و رشد سالانهٔ آن؛",
        "* `inflation_pct` — تورم سالانهٔ ورودی (دست‌نخورده، همان‌طور که تحویل داده شده)؛",
        "* `cpi_index_1390` — شاخص ساخته‌شده از زنجیرهٔ همان تورم؛",
        "* `rent_usd_m2`, `rent_usd_yoy_pct` — نسبت اجاره به ارز و رشد سالانهٔ آن؛",
        "* `source_id_rent`, `source_id_fx` — شناسهٔ منبع هر سمت در `data/sources.csv`.",
        "",
        "`rent_annual.csv` نمای فقط‌اجاره است و قالب قبلی‌اش دست‌نخورده مانده.",
        "",
        "## آنچه این فایل نمی‌گوید",
        "",
        *[f"* {caveat}" for caveat in payload["caveats"]],
        "",
        "برای بازتولید، این اسکریپت را اجرا کنید: `python3 scripts/build_rent_vs_fx.py`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def render_page(template: Path, out_page: Path, payload: Dict[str, Any]) -> None:
    html = template.read_text(encoding="utf-8")
    out_page.write_text(
        html.replace("/*__DATA__*/", json.dumps(payload, ensure_ascii=False)),
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rent-input", default=str(DEFAULT_RENT_INPUT))
    parser.add_argument("--macro-input", default=str(DEFAULT_MACRO_INPUT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--page", default=str(DEFAULT_PAGE))
    args = parser.parse_args(argv)

    rent_input = Path(args.rent_input)
    macro_input = Path(args.macro_input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rent, rent_unit, rent_rows = load_rent(rent_input)
    macro, macro_rows = load_macro(macro_input)
    panel = build_panel(rent, macro)
    payload = build_payload(panel, rent_input, macro_input, rent_rows, macro_rows, rent_unit)

    write_rent_csv(out_dir / "rent_annual.csv", panel)
    write_panel_csv(out_dir / "panel_annual.csv", panel)
    with open(out_dir / "rent_data.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    write_readme(out_dir / "README.md", payload, panel)
    render_page(TEMPLATE, Path(args.page), payload)

    stats = payload["meta"]["stats"]
    print(f"rent    : {rent_input} ({RENT_VARIABLE}, {len(panel)} of {rent_rows} rows, source S2)")
    print(f"macro   : {macro_input} (fx + inflation, {len(panel)} of {macro_rows} rows, source {panel[0]['source_id_fx']})")
    print(f"years   : {len(panel)} ({panel[0]['label_fa']} … {panel[-1]['label_fa']}), base {fa(BASE_YEAR)} = 100")
    print(f"fx      : x{stats['fx_multiple']:.2f}  ({stats['first']['fx']:,.0f} -> {stats['last']['fx']:,.0f} toman)")
    print(f"cpi     : x{stats['cpi_multiple']:.2f}  (100 -> {stats['last']['cpi_index']:,.1f})")
    print(f"rent    : x{stats['rent_multiple']:.2f}  ({stats['first']['rent']:,.0f} -> {stats['last']['rent']:,.0f} toman/m2)")
    print(f"rent/usd: x{stats['rent_usd_multiple']:.2f}  ({stats['first']['rent_usd']:,.1f} -> {stats['last']['rent_usd']:,.1f} $/m2)")
    print(f"scissors: fx is {stats['fx_over_cpi']:.2f}x cpi; rent is {stats['rent_vs_cpi_pct']:+.1f}% vs cpi")
    print(f"outputs : {out_dir}/rent_annual.csv, panel_annual.csv, rent_data.json, README.md")
    print(f"page    : {args.page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
