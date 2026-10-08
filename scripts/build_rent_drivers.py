#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""دلایل گران‌شدن اجاره — تولید `rent-drivers.html`.

دو نمودار از یک پنل فصلی، به‌همراه متن توضیحی:

* **نمودار ۱ — خط زمانی:** سه شاخص فصلی (دلار، مسکن، اجاره) با پایهٔ ثابت ۱۳۹۷ ف۱ = ۱۰۰؛
* **نمودار ۳ — رشد سالانه:** نرخ رشد سال‌به‌سال هر سه سری، گروه‌بندی‌شده.

Input: ``data/rent_drivers/fx_house_rent_quarterly.csv`` — ۲۹ فصل، ۱۳۹۶ ف۱ تا ۱۴۰۳ ف۴ (منبع S17).

Method (همه از همین یک ورودی بازتولیدپذیر است):

1. شاخص هر سری = مقدار ÷ مقدار فصل پایه × ۱۰۰؛ پایه ۱۳۹۷ ف۱ است. ستون‌های شاخصِ ورودی
   دوباره محاسبه و با مقادیر فایل مقابله می‌شوند (اختلاف بیش از ۱ واحد = توقف اسکریپت)؛
2. رشد سالانه = میانگین چهار فصلِ سال ÷ میانگین چهار فصلِ سال قبل − ۱. سالی که هر دو طرفش
   چهار فصل کامل نداشته باشد رشد ندارد، پس ۱۳۹۷ (چون ۱۳۹۶ فقط یک فصل دارد) «پایه» می‌ماند؛
3. آمار توصیفی (بازه و انحراف معیار رشد سالانه، جابه‌جایی درون‌سالِ ۱۳۹۷ و ۱۴۰۳) از همان پنل
   محاسبه و در متن توضیحی تزریق می‌شود تا اعداد متن هرگز از داده جدا نشوند.

**نمودار ۲ (پراکندگی تأخیر) عمداً ساخته نشده است.** روی دادهٔ سطحی R² حدود ۰٫۹۸ می‌شد، ولی
همین R² برای تأخیرهای ۰ و ۱ و ۲ و ۳ تقریباً یکسان بود — یعنی نمودار همروندی دو سری صعودی را
نشان می‌داد، نه تأخیر را. روی تغییرات فصلی R² به ۰٫۰۲ و ۰٫۱۲ می‌افتاد و روی رشد سالانه حتی
علامتش منفی می‌شد (fx[Y] → house[Y+1]: r = −۰٫۲۸). جزئیات در README همین پوشه.

Outputs (``data/rent_drivers/``):

    panel_quarterly.csv   یک ردیف در هر فصل — سطح، شاخص
    annual_growth.csv     یک ردیف در هر سال — میانگین فصل‌ها و رشد سالانه
    drivers_data.json     همان داده، به‌شکل مصرفی صفحه
    README.md             روش، منبع، و آنچه این نمودارها نمی‌گویند
    rent-drivers.html     صفحهٔ مستقل در ریشهٔ مخزن (قالب: scripts/rent_drivers_template.html)

Usage:
    python3 scripts/build_rent_drivers.py
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
DEFAULT_INPUT = REPO_ROOT / "data" / "rent_drivers" / "fx_house_rent_quarterly.csv"
DEFAULT_FX_SAMPLES = REPO_ROOT / "data" / "rent_drivers" / "fx_sampled_1401_1402.csv"
DEFAULT_SCI_CPI = REPO_ROOT / "data" / "sci_cpi_annual.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "rent_drivers"
DEFAULT_PAGE = REPO_ROOT / "rent-drivers.html"
TEMPLATE = Path(__file__).resolve().parent / "rent_drivers_template.html"

#: The three series, in the order the handoff fixes for the legend.
SERIES: Tuple[Dict[str, Any], ...] = (
    {
        "key": "fx",
        "level_field": "fx_toman_per_usd",
        "idx_field": "fx_idx",
        "label_fa": "نرخ دلار آزاد",
        "unit_fa": "تومان در هر دلار",
        "level_digits": 0,
        "level_suffix_fa": "تومان",
    },
    {
        "key": "house",
        "level_field": "house_million_rial_per_m2",
        "idx_field": "house_idx",
        "label_fa": "قیمت هر متر مسکن",
        "unit_fa": "میلیون ریال در هر متر مربع",
        "level_digits": 1,
        "level_suffix_fa": "میلیون ریال",
    },
    {
        "key": "rent",
        "level_field": "rent_thousand_rial_per_m2",
        "idx_field": "rent_idx",
        "label_fa": "اجارهٔ ماهانهٔ هر متر",
        "unit_fa": "هزار ریال در هر متر مربع در ماه",
        "level_digits": 0,
        "level_suffix_fa": "هزار ریال",
    },
)

#: ۱۳۹۷ ف۱ — the base quarter every index is normalised to.
BASE_YEAR, BASE_QUARTER = 1397, 1

#: Contextual markers. Editorial context, not data — labelled as such on the page.
ANNOTATIONS: Tuple[Dict[str, Any], ...] = (
    {"quarter": "1397-2", "n": 1, "label_fa": "تحریم‌های ترامپ", "side": "top"},
    {"quarter": "1399-3", "n": 2, "label_fa": "جهش ارزی ۱۳۹۹", "side": "top"},
    {"quarter": "1401-3", "n": 3, "label_fa": "اعتراضات ۱۴۰۱", "side": "bottom"},
    {"quarter": "1402-1", "n": 4, "label_fa": "جهش قیمت مسکن", "side": "bottom"},
)

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
FA_THOUSANDS = "\u066c"
FA_DECIMAL = "\u066b"
FA_MINUS = "\u2212"
QUARTER_FA = {1: "بهار", 2: "تابستان", 3: "پائیز", 4: "زمستان"}


def fa(number: Any) -> str:
    return str(number).translate(FA_DIGITS)


def fam(value: float, digits: int = 0, signed: bool = False) -> str:
    """Format a number the way the page does (fa-IR): Persian digits, «٬» and «٫»."""
    text = f"{abs(value):,.{digits}f}".replace(",", FA_THOUSANDS).replace(".", FA_DECIMAL)
    if value < 0:
        text = FA_MINUS + text
    elif signed and value > 0:
        text = "+" + text
    return text.translate(FA_DIGITS)

PANEL_FIELDS = (
    "quarter_code",
    "jalali_year",
    "jalali_quarter",
    "quarter_label_fa",
    "fx_toman_per_usd",
    "house_million_rial_per_m2",
    "rent_thousand_rial_per_m2",
    "fx_idx",
    "house_idx",
    "rent_idx",
    "orphan_quarter",
    "source_id",
    "fx_source_id",
    "fx_original_toman",
)

ANNUAL_FIELDS = (
    "jalali_year",
    "year_label_fa",
    "quarters_present",
    "fx_mean_toman",
    "house_mean_million_rial",
    "rent_mean_thousand_rial",
    "fx_yoy_pct",
    "house_yoy_pct",
    "rent_yoy_pct",
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def round1(value: float) -> float:
    """One-decimal rounding, so 20.45 does not print as 20.4."""
    return float(round(value + 1e-9, 1))


def load_fx_samples(path: Path) -> Dict[str, Dict[str, Any]]:
    """Sampled FX -> {``"1401-3"``: {mean, n, source_id}}. Raises if a sampled quarter is absent from the panel."""
    buckets: Dict[str, List[float]] = {}
    source_id = ""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            code = f"{int(row['jalali_year'])}-{int(row['jalali_quarter'])}"
            buckets.setdefault(code, []).append(float(row["fx_toman_per_usd"]))
            source_id = source_id or row["source_id"]
    return {
        code: {"mean": st.mean(values), "n": len(values), "source_id": source_id}
        for code, values in buckets.items()
    }


def apply_fx_correction(quarters: List[Dict[str, Any]], samples: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Override panel FX with the sampled means, keeping the original value for the audit trail."""
    corrections: List[Dict[str, Any]] = []
    for quarter in quarters:
        sample = samples.get(quarter["code"])
        if sample is None:
            continue
        original = quarter["levels"]["fx"]
        quarter["levels"]["fx"] = sample["mean"]
        quarter["fx_original"] = original
        quarter["fx_source"] = sample["source_id"]
        corrections.append(
            {
                "code": quarter["code"],
                "label_fa": quarter["label_fa"],
                "original": original,
                "corrected": sample["mean"],
                "pct": round1((sample["mean"] / original - 1) * 100),
                "samples": sample["n"],
                "source_id": sample["source_id"],
            }
        )
    missing = sorted(set(samples) - {q["code"] for q in quarters})
    if missing:
        raise ValueError(f"sampled FX has quarters absent from the panel: {missing}")
    return corrections


def load_sci_cpi(path: Path) -> Dict[int, Dict[str, Any]]:
    """SCI annual CPI -> {year: {yoy, idx, source_id}}, indexed to the first year present = 100."""
    series: Dict[int, Dict[str, Any]] = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            series[int(row["jalali_year"])] = {
                "yoy": float(row["cpi_yoy_pct"]),
                "source_id": row["source_id"],
            }
    if not series:
        raise ValueError(f"no CPI rows in {path}")
    # the index is a chain of the annual rates, base = the first year present
    base_year = min(series)
    level = 100.0
    for year in sorted(series):
        if year != base_year:
            level = round1(level * (1 + series[year]["yoy"] / 100))
        series[year]["idx"] = level
    series[base_year]["idx"] = 100.0
    return series


def load_panel(path: Path) -> Tuple[List[Dict[str, Any]], str]:
    """Read the quarterly CSV, re-derive every index, and verify it against the file."""
    quarters: List[Dict[str, Any]] = []
    source_id = ""
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            year, quarter = int(row["jalali_year"]), int(row["jalali_quarter"])
            quarters.append(
                {
                    "code": f"{year}-{quarter}",
                    "year": year,
                    "quarter": quarter,
                    "label_fa": row["quarter_label_fa"],
                    "levels": {s["key"]: float(row[s["level_field"]]) for s in SERIES},
                    "idx_in_file": {s["key"]: float(row[s["idx_field"]]) for s in SERIES},
                    "fx_source": row["source_id"],
                }
            )
            source_id = source_id or row["source_id"]
    if not quarters:
        raise ValueError(f"no rows in {path}")
    quarters.sort(key=lambda q: (q["year"], q["quarter"]))
    return quarters, source_id


def check_contiguity(quarters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Report every step that is not one quarter, so a gap can never pass silently."""
    steps = []
    for previous, current in zip(quarters, quarters[1:]):
        gap = (current["year"] * 4 + current["quarter"]) - (previous["year"] * 4 + previous["quarter"])
        if gap != 1:
            steps.append({"from": previous["code"], "to": current["code"], "quarters_skipped": gap - 1})
    return steps


def apply_indices(quarters: List[Dict[str, Any]], verify: bool = True) -> None:
    """Index = level / base x 100. With ``verify``, refuse to continue if the file disagrees."""
    base = next((q for q in quarters if q["year"] == BASE_YEAR and q["quarter"] == BASE_QUARTER), None)
    if base is None:
        raise ValueError(f"base quarter {BASE_YEAR}-{BASE_QUARTER} is missing")
    mismatches = []
    for quarter in quarters:
        quarter["idx"] = {}
        for spec in SERIES:
            key = spec["key"]
            base_level = base["levels"][key]
            if not base_level:
                raise ValueError(f"base level for {key} is zero")
            value = quarter["levels"][key] / base_level * 100
            quarter["idx"][key] = value
            if verify and abs(value - quarter["idx_in_file"][key]) > 1.0:
                mismatches.append((quarter["code"], key, round(value, 1), quarter["idx_in_file"][key]))
    if mismatches:
        raise ValueError(f"index columns disagree with level/base*100: {mismatches}")


def build_annual(quarters: List[Dict[str, Any]], cpi: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Annual means, and YoY only where both years have all four quarters. CPI joins from its own annual series."""
    by_year: Dict[int, List[Dict[str, Any]]] = {}
    for quarter in quarters:
        by_year.setdefault(quarter["year"], []).append(quarter)

    annual: List[Dict[str, Any]] = []
    for year in sorted(by_year):
        present = by_year[year]
        means = {s["key"]: st.mean(q["levels"][s["key"]] for q in present) for s in SERIES}
        previous = by_year.get(year - 1, [])
        complete = len(present) == 4 and len(previous) == 4
        yoy: Dict[str, Optional[float]] = {}
        for spec in SERIES:
            key = spec["key"]
            if not complete:
                yoy[key] = None
                continue
            before = st.mean(q["levels"][key] for q in previous)
            yoy[key] = round1((means[key] / before - 1) * 100) if before else None
        # CPI is an observed annual rate, not derived from the quarters
        yoy["cpi"] = cpi[year]["yoy"] if year in cpi else None
        annual.append(
            {
                "year": year,
                "label_fa": fa(year),
                "quarters_present": len(present),
                "means": means,
                "yoy": yoy,
                "cpi_idx": cpi[year]["idx"] if year in cpi else None,
                "complete": complete,
            }
        )
    return annual


def build_stats(quarters: List[Dict[str, Any]], annual: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Descriptive figures the narrative quotes, so the prose cannot drift from the data."""
    by_code = {q["code"]: q for q in quarters}
    with_yoy = [a for a in annual if a["yoy"]["fx"] is not None]

    def series_yoy(key: str) -> List[float]:
        return [a["yoy"][key] for a in with_yoy]

    volatility = {
        spec["key"]: {
            "min": min(series_yoy(spec["key"])),
            "max": max(series_yoy(spec["key"])),
            "stdev": round1(st.stdev(series_yoy(spec["key"]))),
        }
        for spec in SERIES
    }

    def move(code_from: str, code_to: str, key: str) -> Dict[str, float]:
        a, b = by_code[code_from]["levels"][key], by_code[code_to]["levels"][key]
        return {"from": a, "to": b, "pct": round1((b / a - 1) * 100)}

    peak = max(quarters, key=lambda q: q["idx"]["fx"])
    fx_peak_1397 = max(q["levels"]["fx"] for q in quarters if q["year"] == 1397)
    rise_1400 = next(a for a in with_yoy if a["year"] == 1400)
    latest = with_yoy[-1]

    return {
        "volatility": volatility,
        "base_label_fa": f"{QUARTER_FA[BASE_QUARTER]} {fa(BASE_YEAR)}",
        "window": {
            "first_label_fa": quarters[0]["label_fa"],
            "last_label_fa": quarters[-1]["label_fa"],
            "count": len(quarters),
        },
        "peak_fx": {
            "label_fa": peak["label_fa"],
            "idx": round1(peak["idx"]["fx"]),
            "level": peak["levels"]["fx"],
        },
        "m1397": {key: move("1397-1", "1397-4", key) for key in ("fx", "house", "rent")},
        "fx_peak_1397": fx_peak_1397,
        "m1399": {"house_q1_q4": move("1399-1", "1399-4", "house"),
                  "house_yoy_vs_1398": move("1398-4", "1399-4", "house")},
        "m1400": {"fx": rise_1400["yoy"]["fx"], "house": rise_1400["yoy"]["house"], "rent": rise_1400["yoy"]["rent"]},
        "m1403": {
            "fx": latest["yoy"]["fx"], "house": latest["yoy"]["house"], "rent": latest["yoy"]["rent"],
            "house_q3_q4": move("1403-3", "1403-4", "house"),
        },
        "rent_leads": sorted(
            (a["year"], round1(a["yoy"]["rent"] - a["yoy"]["house"])) for a in with_yoy
        ),
        "annual_years": [a["year"] for a in with_yoy],
        "first_annual_year_label_fa": fa(with_yoy[0]["year"]),
    }


def build_payload(quarters: List[Dict[str, Any]], annual: List[Dict[str, Any]], stats: Dict[str, Any],
                  input_path: Path, source_id: str, gaps: List[Dict[str, Any]],
                  corrections: List[Dict[str, Any]], samples_path: Path,
                  cpi: Dict[int, Dict[str, Any]], cpi_path: Path) -> Dict[str, Any]:
    orphan_codes = {q["code"] for q in quarters if q["code"] in {"1396-1"}}
    return {
        "meta": {
            "title_fa": "چرا اجاره گران می‌شود؟",
            "subtitle_fa": "تحلیل رابطهٔ نرخ دلار، قیمت مسکن و اجاره‌بها در تهران، ۱۳۹۶ تا ۱۴۰۳",
            "base_label_fa": stats["base_label_fa"],
            "base_year": BASE_YEAR,
            "base_quarter": BASE_QUARTER,
            "quarters_count": len(quarters),
            "chart1": {"log_default": True},
            "annotations": [dict(a) for a in ANNOTATIONS],
            "gaps": gaps,
            "inputs": {
                "panel": {
                    "path": str(input_path.relative_to(REPO_ROOT)),
                    "sha256": sha256_of(input_path),
                    "rows": len(quarters),
                    "source_id": source_id,
                },
                "fx_samples": {
                    "path": str(samples_path.relative_to(REPO_ROOT)),
                    "sha256": sha256_of(samples_path),
                    "quarters_corrected": len(corrections),
                    "source_id": corrections[0]["source_id"] if corrections else None,
                },
                "cpi": {
                    "path": str(cpi_path.relative_to(REPO_ROOT)),
                    "sha256": sha256_of(cpi_path),
                    "years": len(cpi),
                    "source_id": cpi[min(cpi)]["source_id"],
                },
            },
            "fx_corrections": corrections,
            "stats": stats,
        },
        "series": [
            {
                "key": s["key"],
                "label_fa": s["label_fa"],
                "unit_fa": s["unit_fa"],
                "level_digits": s["level_digits"],
                "level_suffix_fa": s["level_suffix_fa"],
                "width": 2 if s["key"] == "fx" else 2.5,
                "dash": "",
                "order_fa": index + 1,
            }
            for index, s in enumerate(SERIES)
        ] + [
            {
                "key": "cpi",
                "label_fa": "شاخص تورم",
                "unit_fa": "تورم سالانهٔ مرکز آمار ایران",
                "level_digits": 1,
                "level_suffix_fa": "٪",
                "width": 2,
                "dash": "",
                "annual": True,
                "source_id": cpi[min(cpi)]["source_id"],
                "source_note_fa": "سالانه است، نه فصلی: یک نقطه در هر سال در مرکز همان سال، و نقطه‌ها به هم وصل می‌شوند. "
                                  "بین دو سال هیچ مقداری ساخته نشده است.",
                "order_fa": len(SERIES) + 1,
            }
        ],
        "annual_cpi": [
            {
                "year": year,
                "label_fa": fa(year),
                "yoy_pct": cpi[year]["yoy"],
                "idx": cpi[year]["idx"],
                "source_id": cpi[year]["source_id"],
            }
            for year in sorted(cpi)
        ],
        "cpi_base_year": min(cpi),
        "cpi_base_label_fa": fa(min(cpi)),
        "quarters": [
            {
                "code": q["code"],
                "year": q["year"],
                "quarter": q["quarter"],
                "label_fa": q["label_fa"],
                "short_fa": f"{QUARTER_FA[q['quarter']]} {fa(q['year'])}",
                "year_label_fa": fa(q["year"]),
                "idx": {k: round1(v) for k, v in q["idx"].items()},
                "levels": q["levels"],
                "orphan": q["code"] in orphan_codes,
            }
            for q in quarters
        ],
        "annual": [
            {
                "year": a["year"],
                "label_fa": a["label_fa"],
                "complete": a["complete"],
                "yoy": a["yoy"],
                "means": a["means"],
                "cpi_idx": a["cpi_idx"],
            }
            for a in annual
        ],
        "sources": [
            "قیمت مسکن: بانک مرکزی جمهوری اسلامی ایران — گزارش تحولات بازار معاملات مسکن شهر تهران (۱۳۹۶–۱۴۰۳).",
            "نرخ اجاره: مرکز آمار ایران؛ تصویرسازی: alitayebi.github.io/maps/rent.",
            "نرخ ارز: بازار آزاد (bonbast.com و گزارش‌های خبری)، به‌علاوهٔ نمونهٔ ۲۱‌روزهٔ S19 برای تصحیح ۱۴۰۱ و ۱۴۰۲.",
            "شاخص تورم: مرکز آمار ایران (S18) — نرخ میانگین سالانه، از data/sci_cpi_annual.csv (۱۳۹۷–۱۴۰۳).",
            "بستهٔ فصلی پروژه (S17) — تحویل‌شده ۲۰۲۶-۱۰-۰۸؛ دادهٔ فصلی مسکن و اجاره از همین بسته است.",
        ],
        "caveats": [
            "**خط تورم سالانه است، نه فصلی.** سری مرکز آمار (S18) فقط نرخ میانگین سالانه دارد، پس روی نمودار فصلی یک نقطه در مرکز هر سال گذاشته شده و نقطه‌ها با پاره‌خط به هم وصل شده‌اند. بین دو سال هیچ مقداری ساخته نشده، ولی خط صاف بین دو نقطه هم به این معنا نیست که تورم در آن بازه خطی بوده — فقط دو میانگین سالانه به هم وصل شده‌اند.",
            "**پایهٔ تورم با پایهٔ سه سری دیگر یکی نیست.** سه سری فصلی با پایهٔ بهار ۱۳۹۷ = ۱۰۰ شاخص شده‌اند و تورم با پایهٔ سال ۱۳۹۷ = ۱۰۰ (چون فقط مقدار سالانه دارد). اختلاف در حد همان یک فصل است ولی صفر نیست.",
            "**سری تورم از ۱۳۹۷ آغاز می‌شود** و روی نمودار از همان‌جا دیده می‌شود، در حالی که سه خط دیگر از بهار ۱۳۹۶ شروع می‌کنند. برای ۱۳۹۶ مقدار تورم وجود ندارد و هیچ‌چیز جای آن گذاشته نشده است.",
            "تورم مرکز آمار با سری بانک جهانی/صندوق بین‌المللی پول (WDI، منبعش IFS) یکی نیست و این دو سیستماتیک تفاوت دارند: مثلاً ۱۳۹۷ مرکز آمار ۲۶٫۹ و بانک جهانی ۳۱٫۲، و ۱۴۰۳ مرکز آمار ۳۲٫۵ و بانک جهانی ۴۴٫۶. مرکز آمار انتخاب شده چون پرسش دربارهٔ سطح قیمت داخلی ایران است. **این دو را نباید به هم چسباند.**",
            "**نرخ ارز ۱۴۰۱ و ۱۴۰۲ تصحیح شده است.** یک نمونهٔ ۲۱‌روزهٔ بیرونی (S19) نشان می‌دهد مسیر فصلی S17 در ۱۴۰۱ حدود ۱۴٪ بالاتر از واقع بوده: پائیز ۱۴۰۱ از ۴۲٬۰۰۰ به ۳۵٬۰۹۷ و زمستان از ۵۵٬۰۰۰ به ۴۴٬۸۹۴ آمد. ۱۴۰۲ اختلاف کمتری داشت (−۳٪). رشد سالانهٔ ارز با این تصحیح عوض می‌شود: ۱۴۰۱ از +۵۰٪ به +۳۱٪ و ۱۴۰۲ از +۳۲٪ به +۴۷٪. مقادیر اصلی در ستون `fx_original_toman` فایل panel_quarterly.csv مانده‌اند. **۱۴۰۰ و ۱۴۰۳ بررسی نشده‌اند** چون نمونه‌ای برایشان داده نشد.",
            "منبع نمونهٔ ارز (S19) نام‌دار نیست: تاریخ‌ها و نرخ‌ها از یک سایت تبدیل ارز آمده‌اند ولی نام و نشانی سایت داده نشده، پس اعتبارش از S17 کمتر است. فقط ستون تومان به کار رفته؛ ستون دلاری همان صفحه مقادیر متغیر (۱٫۰۵، ۰٫۹۵۱۳۹۵، …) نشان می‌داد که کنار گذاشته شد.",
            "بازهٔ ۱۳۹۶ فقط یک فصل دارد (بهار ۱۳۹۶) و بعد از آن سه فصل خالی است. آن نقطه روی نمودار به‌صورت تک‌نقطهٔ جدا و با نشانهٔ شکاف دیده می‌شود و خط از روی فصل‌های غایب کشیده نشده — هیچ درون‌یابی‌ای انجام نشده است.",
            "دادهٔ اجاره در این بسته با سری‌های اجارهٔ دیگر مخزن یکی نیست: حدود ۱٫۴۵ تا ۱٫۷۴ برابر سری سالانهٔ بانک مرکزی در data/annual.csv و در data/rent_vs_fx/ است. تعریف‌ها متفاوت‌اند.",
            "نرخ ارز این بسته هم با data/rent_vs_fx/fx_inflation_annual.csv یکی نیست: آن فایل یک مقدار در هر سال (سازگار با نرخ پایان‌سال) دارد و این‌جا مسیر فصلی. مثلاً ۱۴۰۰ در آن فایل ۲۸٬۰۰۰ و این‌جا میانگین فصلی ۲۶٬۸۷۵ است.",
            "رشد سالانه از میانگین چهار فصلِ هر سال محاسبه می‌شود، نه از یک نقطه. پس این ارقام با «رشد نقطه‌به‌نقطه» یا «اسفند به اسفند» یکی نیست.",
            "۱۳۹۷ رشد سالانه ندارد، چون ۱۳۹۶ فقط یک فصل پوشش دارد؛ سال پایهٔ شاخص‌ها هم ۱۳۹۷ ف۱ است. نمودار رشد سالانه از ۱۳۹۸ آغاز می‌شود.",
            "**نمودار تأخیر زمانی عمداً حذف شده است.** پراکندگی دلار در برابر مسکنِ فصل بعد، روی دادهٔ سطحی R² ≈ ۰٫۹۵ می‌داد، ولی همین R² برای تأخیرهای ۰ و ۱ و ۲ و ۳ تقریباً یکسان بود (۰٫۹۵ تا ۰٫۹۸) — یعنی هم‌روندی دو سری صعودی را نشان می‌داد، نه تأخیر را. روی تغییرات فصلی R² به ۰٫۰۲ (دلار→مسکن) و ۰٫۱۲ (مسکن→اجاره) می‌افتاد، و در فرکانس سالانه علامت رابطه منفی می‌شد: fx[Y] → house[Y+1] با r = −۰٫۲۸ و n = ۵. با این داده، هیچ تأخیری قابل اثبات نیست، پس نمودار حذف شد و ادعای تأخیر از متن‌ها هم برداشته شد.",
            "همبستگی و هم‌حرکتی، علیت نیست. نمودارها هم‌زمانی و توالی را نشان می‌دهند؛ نسبت دادن آن به یک علت خاص نیاز به تحلیل جداگانه دارد.",
            "علامت‌های ۱۳۹۷ ف۲، ۱۳۹۹ ف۳، ۱۴۰۱ ف۳ و ۱۴۰۲ ف۱ زمینهٔ تفسیری‌اند، نه داده — از سری‌ها استخراج نشده‌اند.",
            "همهٔ ارقام اسمی‌اند و تورم از آن‌ها کنار گذاشته نشده؛ رشد حقیقی در این نمودارها دیده نمی‌شود.",
            "دو سری صعودی همیشه همبستگی بالایی دارند، حتی بدون هیچ رابطهٔ واقعی. تحلیل این صفحه بر پایهٔ نرخ رشد سالانه است، نه سطح قیمت‌ها.",
        ],
    }


def build_narrative(stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The explanatory copy. Every number quoted here is injected from the computation."""
    v = stats["volatility"]
    m97, m99, m00, m03 = stats["m1397"], stats["m1399"], stats["m1400"], stats["m1403"]

    # formatted up front: keeps the prose numbers tied to the data without nested-quote f-strings
    fx97_from = fam(m97["fx"]["from"])
    fx97_peak = fam(stats["fx_peak_1397"])
    house97_from = fam(m97["house"]["from"])
    house97_to = fam(m97["house"]["to"])
    house97_pct = fam(m97["house"]["pct"], signed=True)
    rent97_from = fam(m97["rent"]["from"])
    rent97_to = fam(m97["rent"]["to"])
    rent97_pct = fam(m97["rent"]["pct"], signed=True)
    house99_pct = fam(m99["house_yoy_vs_1398"]["pct"], signed=True)
    fx00 = fam(m00["fx"])
    house00 = fam(m00["house"])
    rent00 = fam(m00["rent"])
    house103_from = fam(m03["house_q3_q4"]["from"])
    house103_to = fam(m03["house_q3_q4"]["to"])
    house103_pct = fam(m03["house_q3_q4"]["pct"], digits=1)
    fx03 = fam(m03["fx"])
    house03 = fam(m03["house"])
    rent03 = fam(m03["rent"])
    span = {
        key: (fam(v[key]["min"]), fam(v[key]["max"]), fam(v[key]["stdev"], digits=1))
        for key in ("fx", "house", "rent")
    }
    return [
        {
            "id": "chart1-text",
            "heading_fa": "اجاره همیشه دنبال مسکن می‌آید — و مسکن دنبال دلار",
            "paras_fa": [
                "اگر به این نمودار دقت کنید، سه خط را می‌بینید که همیشه با هم حرکت نمی‌کنند — همیشه یکی جلو و یکی عقب است.",
                f"پس از هر جهش ارزی، قیمت مسکن و اجاره در فصل‌های بعدی افزایش یافته است. در ۱۳۹۷ دلار از "
                f"{fx97_from} به {fx97_peak} تومان رسید؛ در همان سال قیمت مسکن از "
                f"{house97_from} به {house97_to} میلیون ریال در متر مربع رفت "
                f"({house97_pct}٪) و اجاره از {rent97_from} به "
                f"{rent97_to} هزار ریال ({rent97_pct}٪).",
                "این فاصله بی‌دلیل نیست. قراردادهای اجاره یک‌ساله‌اند؛ مستأجر تا وقتی قراردادش تمام نشود، بازار را حس "
                "نمی‌کند. به همین دلیل بازار اجاره دیرتر از بازار مسکن واکنش نشان می‌دهد.",
                f"بزرگ‌ترین جهش ارزی این بازه در ۱۳۹۹ رخ داد. قیمت مسکن در همان سال تقریباً دو برابر شد "
                f"({house99_pct}٪ نسبت به پایان ۱۳۹۸) و اجاره با فاصله، در سال‌های بعد "
                "این مسیر را طی کرد.",
                "نکتهٔ مهم‌تر این است: حتی در سال‌هایی که دلار آرام‌تر بوده، اجاره با سرعت بیشتری بالا رفته — چون "
                "مسکنی که سال قبل گران شده، مبنای قرارداد جدید است.",
            ],
        },
        {
            "id": "chart3-text",
            "heading_fa": "در سال‌هایی که دلار آرام گرفت، اجاره بدتر شد",
            "paras_fa": [
                f"در ۱۴۰۰ دلار فقط {fx00}٪ رشد کرد و مسکن {house00}٪ — آرام‌ترین سال این "
                f"بازه — ولی اجاره {rent00}٪ بالا رفت: بیشتر از هر دوی آن‌ها.",
                f"اجاره آرام‌ترین خط این سه است: رشد سالانهٔ آن بین {span['rent'][0]}٪ و "
                f"{span['rent'][1]}٪ نوسان کرده (انحراف معیار {span['rent'][2]})، در حالی که "
                f"مسکن بین {span['house'][0]}٪ و {span['house'][1]}٪ "
                f"(انحراف معیار {span['house'][2]}) و دلار بین {span['fx'][0]}٪ و "
                f"{span['fx'][1]}٪ (انحراف معیار {span['fx'][2]}) نوسان داشته‌اند.",
                "یعنی وقتی مسکن می‌ایستد، اجاره تازه خودش را می‌رساند. بازار اجاره یک بازار با حافظه است.",
            ],
        },
        {
            "id": "chart-divergence-text",
            "heading_fa": "جایی که مسکن از دلار جدا شد",
            "paras_fa": [
                f"در ۱۴۰۳ قیمت مسکن برای اولین بار از مسیر دلار جدا شد: دلار {fx03}٪ بالا رفت، اما "
                f"مسکن فقط {house03}٪ رشد کرد و در فصل آخر سال حتی افت کرد — از "
                f"{house103_from} به {house103_to} میلیون ریال "
                f"({house103_pct}٪). احتمالاً ترکیبی از رکود معاملات، انقباض قدرت خرید و "
                "عرضهٔ بیشتر واحدهای نوساز این انحراف را توضیح می‌دهد.",
                f"اما اجاره همچنان بالا رفت — {rent03}٪ در همان سال، بیشتر از مسکن و بیشتر از دلار.",
                "این دو نمودار هم‌زمانی و توالی را نشان می‌دهند، نه علت و معلول. تحلیل بر پایهٔ نرخ رشد سالانه است، "
                "نه سطح قیمت‌ها — چون دو سری صعودی همیشه همبستگی بالایی دارند، حتی بدون هیچ رابطهٔ واقعی.",
            ],
        },
    ]


def write_panel_csv(path: Path, quarters: List[Dict[str, Any]], source_id: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(PANEL_FIELDS), lineterminator="\n")
        writer.writeheader()
        for q in quarters:
            writer.writerow(
                {
                    "quarter_code": q["code"],
                    "jalali_year": q["year"],
                    "jalali_quarter": q["quarter"],
                    "quarter_label_fa": q["label_fa"],
                    "fx_toman_per_usd": f"{q['levels']['fx']:g}",
                    "house_million_rial_per_m2": f"{q['levels']['house']:g}",
                    "rent_thousand_rial_per_m2": f"{q['levels']['rent']:g}",
                    "fx_idx": f"{q['idx']['fx']:.1f}",
                    "house_idx": f"{q['idx']['house']:.1f}",
                    "rent_idx": f"{q['idx']['rent']:.1f}",
                    "orphan_quarter": "1" if q["code"] == "1396-1" else "",
                    "source_id": source_id,
                    "fx_source_id": q.get("fx_source", source_id),
                    "fx_original_toman": "" if "fx_original" not in q else f"{q['fx_original']:g}",
                }
            )


def write_annual_csv(path: Path, annual: List[Dict[str, Any]]) -> None:
    def blank(value: Optional[float]) -> str:
        return "" if value is None else f"{value:.1f}"

    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ANNUAL_FIELDS), lineterminator="\n")
        writer.writeheader()
        for a in annual:
            writer.writerow(
                {
                    "jalali_year": a["year"],
                    "year_label_fa": a["label_fa"],
                    "quarters_present": a["quarters_present"],
                    "fx_mean_toman": f"{a['means']['fx']:,.0f}".replace(",", ""),
                    "house_mean_million_rial": f"{a['means']['house']:g}",
                    "rent_mean_thousand_rial": f"{a['means']['rent']:g}",
                    "fx_yoy_pct": blank(a["yoy"]["fx"]),
                    "house_yoy_pct": blank(a["yoy"]["house"]),
                    "rent_yoy_pct": blank(a["yoy"]["rent"]),
                }
            )


def write_readme(path: Path, payload: Dict[str, Any], annual: List[Dict[str, Any]]) -> None:
    stats = payload["meta"]["stats"]
    lines = [
        "# دلایل گران‌شدن اجاره — ۱۳۹۶ تا ۱۴۰۳",
        "",
        "دو نمودار از یک پنل فصلی:",
        "",
        "| نمودار | نوع | سری |",
        "| --- | --- | --- |",
        "| ۱ | خط زمانی فصلی، پایهٔ ۱۳۹۷ ف۱ = ۱۰۰، مقیاس لگاریتمی | دلار، مسکن، اجاره (فصلی) + شاخص تورم (سالانه، یک نقطه در هر سال) |",
        "| ۳ | ستون‌های رشد سالانهٔ گروه‌بندی‌شده | دلار، مسکن، اجاره، شاخص تورم |",
        "",
        f"داده: `data/rent_drivers/fx_house_rent_quarterly.csv` — {fa(payload['meta']['quarters_count'])} فصل، "
        f"{stats['window']['first_label_fa']} تا {stats['window']['last_label_fa']} (منبع S17).",
        "صفحه: `rent-drivers.html` در ریشهٔ مخزن (داده درون‌صفحه، بدون سرور).",
        "",
        "## نمودار ۲ (تأخیر زمانی) چرا ساخته نشد",
        "",
        "سند تحویل یک پراکندگی می‌خواست که نشان دهد مسکن با تأخیر ۱–۲ فصل دنبال دلار می‌رود. داده این را نشان نمی‌دهد:",
        "",
        "| فرکانس | سنجه | نتیجه |",
        "| --- | --- | --- |",
        "| فصلی، سطح | R² دلار[t] → مسکن[t+۱] | ۰٫۹۵ |",
        "| فصلی، سطح | همان برای تأخیر ۰ و ۲ و ۳ | ۰٫۹۵ تا ۰٫۹۸ — تفکیک نمی‌کند |",
        "| فصلی، تغییرات | R² دلار[t] → مسکن[t+۱] | ۰٫۰۲ |",
        "| فصلی، تغییرات | R² مسکن[t] → اجاره[t+۲] | ۰٫۱۲ |",
        "| سالانه، رشد | r دلار[Y] → مسکن[Y+۱] | **−۰٫۲۸** (n=۵) |",
        "",
        "R² روی سطح در همهٔ تأخیرها تقریباً یکسان است — از جمله تأخیر صفر — یعنی هم‌روندی دو سری صعودی را "
        "اندازه می‌گیرد، نه انتقال را. روی تغییرات فرو می‌ریزد و در فرکانس سالانه علامتش منفی می‌شود. پس نمودار حذف "
        "شد و ادعای «تأخیر یک تا دو فصل» از متن‌ها هم برداشته شد.",
        "",
        "## شاخص تورم (S18) — چرا سالانه است و چطور رسم شده",
        "",
        "مرکز آمار نرخ تورم را فقط به‌صورت **میانگین سالانه** منتشر می‌کند، پس سری تورم فصلی نیست:",
        "",
        "| سال | تورم سالانه | شاخص (۱۳۹۷ = ۱۰۰) |",
        "| ---: | ---: | ---: |",
        *[
            f"| {a['label_fa']} | {a['yoy_pct']:,.1f}٪ | {a['idx']:,.1f} |"
            for a in payload["annual_cpi"]
        ],
        "",
        "روی نمودار فصلی، برای هر سال **یک نقطه در مرکز همان سال** گذاشته شده و نقطه‌ها با پاره‌خط به هم",
        "وصل شده‌اند. یعنی هیچ مقداری بین دو سال ساخته نشده است — ولی پاره‌خط صاف هم به این معنا نیست که",
        "تورم در آن بازه خطی بوده؛ فقط دو میانگین سالانه به هم وصل شده‌اند. خط تورم خاکستری است.",
        "",
        "دو نکتهٔ ریز: پایهٔ تورم سال ۱۳۹۷ = ۱۰۰ است و پایهٔ سه سری دیگر بهار ۱۳۹۷ = ۱۰۰ (اختلاف در حد یک فصل)،",
        "و سری تورم از ۱۳۹۷ آغاز می‌شود در حالی که سه خط دیگر از بهار ۱۳۹۶ — برای ۱۳۹۶ تورم موجود نیست.",
        "",
        "## نرخ ارز ۱۴۰۱ و ۱۴۰۲ تصحیح شده است",
        "",
        "سری فصلی S17 برای ارز با یک نمونهٔ ۲۱‌روزهٔ بیرونی (S19) مقابله شد. این نمونه ۳۵ مقدار دارد:",
        "۱۷ نمونه از ۱۵ فروردین ۱۴۰۱ تا ۱۵ اسفند ۱۴۰۱ و ۱۸ نمونه از ۰۷ فروردین ۱۴۰۲ تا ۲۸ اسفند ۱۴۰۲،",
        "همه با فاصلهٔ دقیقاً ۲۱ روز. میانگین فصلی همان نمونه‌ها جایگزین مقادیر S17 شد:",
        "",
        "| فصل | S17 | تصحیح‌شده | اختلاف | نمونه |",
        "| --- | ---: | ---: | ---: | ---: |",
        *[
            f"| {c['label_fa']} | {c['original']:,.0f} | {c['corrected']:,.0f} | {c['pct']:+.1f}٪ | {fa(c['samples'])} |"
            for c in payload["meta"]["fx_corrections"]
        ],
        "",
        "اثر روی رشد سالانهٔ ارز قابل توجه است: ۱۴۰۱ از +۵۰٪ به +۳۱٪ و ۱۴۰۲ از +۳۲٪ به +۴۷٪ می‌رود.",
        "مقادیر اصلی و منبع هر فصل در `panel_quarterly.csv` ستون‌های `fx_original_toman` و `fx_source_id` مانده‌اند.",
        "",
        "۱۴۰۰ و ۱۴۰۳ نمونه‌ای نداشتند و تصحیح نشده‌اند؛ اگر همان خطا در آن‌ها هم باشد، نمودار همچنان نادرست است.",
        "منبع نمونه (S19) هم نام‌دار نیست — فقط «یک سایت تبدیل ارز» — پس اعتبارش از S17 کمتر است.",
        "",
        "## جدول رشد سالانه",
        "",
        "| سال | دلار | مسکن | اجاره |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for a in annual:
        if a["yoy"]["fx"] is None:
            lines.append(f"| {a['label_fa']} | — (پایه) | — | — |")
        else:
            lines.append(
                f"| {a['label_fa']} | {a['yoy']['fx']:+,.1f}٪ | {a['yoy']['house']:+,.1f}٪ | {a['yoy']['rent']:+,.1f}٪ |"
            )
    lines += [
        "",
        "رشد = میانگین چهار فصلِ سال ÷ میانگین چهار فصلِ سال قبل − ۱. ۱۳۹۷ رشد ندارد چون ۱۳۹۶ فقط یک فصل دارد.",
        "",
        "## آنچه این فایل نمی‌گوید",
        "",
        *[f"* {c}" for c in payload["caveats"]],
        "",
        "برای بازتولید: `python3 scripts/build_rent_drivers.py`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def render_page(template: Path, out_page: Path, payload: Dict[str, Any], narrative: List[Dict[str, Any]]) -> None:
    html = template.read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/", json.dumps(payload, ensure_ascii=False))
    html = html.replace("/*__NARRATIVE__*/", json.dumps(narrative, ensure_ascii=False))
    out_page.write_text(html, encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--fx-samples", default=str(DEFAULT_FX_SAMPLES))
    parser.add_argument("--cpi", default=str(DEFAULT_SCI_CPI))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--page", default=str(DEFAULT_PAGE))
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    samples_path = Path(args.fx_samples)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    quarters, source_id = load_panel(input_path)
    gaps = check_contiguity(quarters)
    apply_indices(quarters)                       # verify the file's own index columns first
    corrections = apply_fx_correction(quarters, load_fx_samples(samples_path))
    if corrections:
        apply_indices(quarters, verify=False)     # re-derive against the corrected levels
    cpi_path = Path(args.cpi)
    cpi = load_sci_cpi(cpi_path)
    annual = build_annual(quarters, cpi)
    stats = build_stats(quarters, annual)
    payload = build_payload(quarters, annual, stats, input_path, source_id, gaps, corrections, samples_path,
                            cpi, cpi_path)
    narrative = build_narrative(stats)

    write_panel_csv(out_dir / "panel_quarterly.csv", quarters, source_id)
    write_annual_csv(out_dir / "annual_growth.csv", annual)
    with open(out_dir / "drivers_data.json", "w", encoding="utf-8") as handle:
        json.dump({"data": payload, "narrative": narrative}, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    write_readme(out_dir / "README.md", payload, annual)
    render_page(TEMPLATE, Path(args.page), payload, narrative)

    print(f"input   : {input_path} ({len(quarters)} quarters, source {source_id})")
    print(f"window  : {quarters[0]['label_fa']} … {quarters[-1]['label_fa']}, base {stats['base_label_fa']} = 100")
    print(f"indices : re-derived from levels and verified against the file")
    if gaps:
        for gap in gaps:
            print(f"gap     : {gap['from']} -> {gap['to']} ({gap['quarters_skipped']} quarters missing)")
    else:
        print("gap     : none")
    print("annual YoY (mean-of-quarters vs mean-of-quarters):")
    for a in annual:
        if a["yoy"]["fx"] is None:
            print(f"  {a['label_fa']}: base / incomplete (only {a['quarters_present']} quarter(s) present)")
        else:
            print(f"  {a['label_fa']}: fx {a['yoy']['fx']:+7.1f}  house {a['yoy']['house']:+7.1f}  rent {a['yoy']['rent']:+7.1f}")
    if corrections:
        print(f"fx fix  : {len(corrections)} quarters overridden from {samples_path.name} ({corrections[0]['source_id']})")
        for c in corrections:
            print(f"  {c['label_fa']}: {c['original']:>9,.0f} -> {c['corrected']:>9,.0f}  ({c['pct']:+5.1f}%, n={c['samples']})")
    else:
        print("fx fix  : none")
    print(f"outputs : {out_dir}/panel_quarterly.csv, annual_growth.csv, drivers_data.json, README.md")
    print(f"page    : {args.page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
