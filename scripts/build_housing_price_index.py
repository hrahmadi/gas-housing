#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""قیمت مسکن در برابر ارز و تورم — شاخص فصلی با پایهٔ مشترک.

Three quarterly series on one axis, all indexed to the same base quarter (100) and all three
covering exactly the same 21 quarters (تابستان ۱۴۰۰ … تابستان ۱۴۰۵):

* **housing** — Kilid asking sale price per m², Tehran, 22 municipal districts;
* **FX** — free-market toman per US dollar;
* **CPI** — official consumer price index (base 1400 = 100).

Inputs:

* ``kilid/kilid_data/normalized/kilid_tehran_sale_price_monthly.csv`` — 22 districts × 60
  consecutive months, ``1400-06`` … ``1405-05``. This is the *only* Kilid series in the repo
  that covers a city completely for the whole window (22/22 areas, 60/60 months, 8 modelled
  months out of 1,320 rows), which is why the housing line is Tehran and not a national blend.
  The other nine cities are ragged (43–678 rows, up to 42% ``MODELED``, start dates from
  ``1399-12`` to ``1401-09``), so a national line would mix coverage with price.
* ``data/housing_price/fx_cpi_quarterly.csv`` — the owner's quarterly FX and CPI table,
  hand-entered and approximate; kept in the repo as a file rather than a constant in code.
  It starts at ``1400-06`` too, which is what makes the three-way comparison symmetric.

Method (each step is reproducible from the two inputs):

1. every month is mapped to a Jalali quarter: ``Q = (month - 1) // 3 + 1`` (۱=بهار … ۴=زمستان);
2. per district per quarter: the **median of that district's monthly medians** in the quarter;
3. per quarter: the **median across the 22 districts** — one district, one vote, so a single
   expensive district cannot move the city line;
4. ``index = level / level(base) × 100`` with the base fixed at **1400 Q2**, the first quarter
   Kilid and the macro table both cover, applied identically to all three series so the lines
   share a base; nothing is backfilled or interpolated.

Outputs (``data/housing_price/``):

    quarterly_index.csv   one row per quarter — levels, indices, quality columns
    index_data.json       the same, shaped for the page (raw levels; the page re-bases live)
    README.md             how to read it, and what it does not say
    housing-price.html    self-contained page at the repo root (template: scripts/housing_price_template.html)

Usage:
    python3 scripts/build_housing_price_index.py
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
DEFAULT_HOUSING_INPUT = REPO_ROOT / "kilid" / "kilid_data" / "normalized" / "kilid_tehran_sale_price_monthly.csv"
DEFAULT_MACRO_INPUT = REPO_ROOT / "data" / "housing_price" / "fx_cpi_quarterly.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "housing_price"
DEFAULT_PAGE = REPO_ROOT / "housing-price.html"
TEMPLATE = Path(__file__).resolve().parent / "housing_price_template.html"

QUARTER_FA: Dict[int, str] = {1: "بهار", 2: "تابستان", 3: "پائیز", 4: "زمستان"}

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

#: The base quarter of the comparison: the first quarter Kilid covers (شهریور ۱۴۰۰ = تابستان),
#: which is also the first quarter the owner's macro table covers — so all three series span
#: exactly the same 21 quarters and no line is shorter than another.
BASE_QUARTER: Tuple[int, int] = (1400, 2)

FIELDS: Tuple[str, ...] = (
    "quarter_code",
    "jalali_year",
    "jalali_quarter",
    "quarter_label_fa",
    "months_observed",
    "months_first",
    "months_last",
    "districts_present",
    "modeled_months",
    "median_sample_size",
    "housing_price_psm_toman",
    "housing_index",
    "fx_toman_per_usd",
    "fx_index",
    "fx_approx",
    "cpi_official_1400_100",
    "cpi_index",
    "cpi_approx",
    "housing_quality",
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quarter_of(period_code: str) -> Tuple[int, int]:
    """``"1400-06"`` -> ``(1400, 2)``."""
    year_text, month_text = period_code.split("-")
    month = int(month_text)
    return int(year_text), (month - 1) // 3 + 1


def quarter_code(year: int, quarter: int) -> str:
    return f"{year}-{quarter}"


def quarter_label(year: int, quarter: int) -> str:
    return f"{QUARTER_FA[quarter]} {year}".translate(FA_DIGITS)


def median(values: List[float]) -> Optional[float]:
    return st.median(values) if values else None


# --------------------------------------------------------------------------- inputs

def load_housing(path: Path) -> List[Dict[str, Dict[str, Any]]]:
    """Kilid monthly rows -> one entry per (year, quarter), districts separated."""
    buckets: Dict[Tuple[int, int], Dict[str, List[Dict[str, str]]]] = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = quarter_of(row["period_code"])
            buckets.setdefault(key, {}).setdefault(row["district_number"], []).append(row)

    quarters: List[Dict[str, Dict[str, Any]]] = []
    for key in sorted(buckets):
        districts = buckets[key]
        city_parts: List[float] = []
        month_codes: set[str] = set()
        samples: List[float] = []
        modeled = 0
        for rows in districts.values():
            prices = [float(r["price_psm_median_toman"]) for r in rows]
            district_median = median(prices)
            if district_median is not None:
                city_parts.append(district_median)
            month_codes.update(r["period_code"] for r in rows)
            samples.extend(float(r["sample_size"]) for r in rows)
            modeled += sum(1 for r in rows if r["trust"] != "DIRECT")

        months = sorted(month_codes)
        quarters.append(
            {
                "key": key,
                "level": median(city_parts),
                "months_observed": len(months),
                "months_first": months[0],
                "months_last": months[-1],
                "districts_present": len(districts),
                "modeled_months": modeled,
                "median_sample_size": median(samples),
            }
        )
    return quarters


def load_macro(path: Path) -> Dict[str, Dict[str, Any]]:
    """Owner's FX/CPI table -> ``{"1400-2": {...}}``."""
    macro: Dict[str, Dict[str, Any]] = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = quarter_code(int(row["jalali_year"]), int(row["jalali_quarter"]))
            macro[key] = {
                "label_fa": row["quarter_label_fa"],
                "fx": float(row["fx_toman_per_usd"]),
                "fx_approx": row["fx_approx"] == "1",
                "cpi": float(row["cpi_official_1400_100"]),
                "cpi_approx": row["cpi_approx"] == "1",
                "source": row["source"],
            }
    return macro


def rebase(value: Optional[float], base_value: Optional[float]) -> Optional[float]:
    if value is None or base_value in (None, 0):
        return None
    return value / base_value * 100.0


# --------------------------------------------------------------------------- assembly

def build_quarters(housing: List[Dict[str, Any]], macro: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Every quarter for which at least one of the three series exists, oldest first."""
    keys = {row["key"] for row in housing} | {
        (int(code.split("-")[0]), int(code.split("-")[1])) for code in macro
    }
    by_housing = {row["key"]: row for row in housing}

    quarters: List[Dict[str, Any]] = []
    for key in sorted(keys):
        year, quarter = key
        code = quarter_code(year, quarter)
        shelter = by_housing.get(key)
        market = macro.get(code)
        quarters.append(
            {
                "code": code,
                "year": year,
                "quarter": quarter,
                "label_fa": quarter_label(year, quarter),
                "quarter_fa": QUARTER_FA[quarter],
                "housing": shelter["level"] if shelter else None,
                "fx": market["fx"] if market else None,
                "cpi": market["cpi"] if market else None,
                "housing_approx": False,
                "fx_approx": bool(market and market["fx_approx"]),
                "cpi_approx": bool(market and market["cpi_approx"]),
                "quality": {
                    "districts_present": shelter["districts_present"] if shelter else 0,
                    "months_observed": shelter["months_observed"] if shelter else 0,
                    "months_first": shelter["months_first"] if shelter else None,
                    "months_last": shelter["months_last"] if shelter else None,
                    "modeled_months": shelter["modeled_months"] if shelter else 0,
                    "median_sample_size": shelter["median_sample_size"] if shelter else None,
                },
                "source": {
                    "housing": "kilid/kilid_data/normalized/kilid_tehran_sale_price_monthly.csv" if shelter else None,
                    "macro": market["source"] if market else None,
                },
            }
        )

    for quarter in quarters:
        quarter["housing_index"] = rebase(quarter["housing"], base_value(quarters, BASE_QUARTER, "housing"))
        quarter["fx_index"] = rebase(quarter["fx"], base_value(quarters, BASE_QUARTER, "fx"))
        quarter["cpi_index"] = rebase(quarter["cpi"], base_value(quarters, BASE_QUARTER, "cpi"))
        quarter["housing_quality"] = housing_quality(quarter)
    return quarters


def base_value(quarters: List[Dict[str, Any]], base: Tuple[int, int], series: str) -> Optional[float]:
    code = quarter_code(*base)
    for quarter in quarters:
        if quarter["code"] == code:
            return quarter[series]
    return None


def housing_quality(quarter: Dict[str, Any]) -> str:
    if quarter["housing"] is None:
        return "NO DATA (before Kilid coverage)"
    notes = [f"OBSERVED (Kilid listing prices), {quarter['quality']['districts_present']}/22 districts"]
    if quarter["quality"]["months_observed"] < 3:
        notes.append(f"ONLY {quarter['quality']['months_observed']} MONTH(S)")
    if quarter["quality"]["modeled_months"]:
        notes.append(f"{quarter['quality']['modeled_months']} MODELED months")
    if quarter["quality"]["median_sample_size"] is not None and quarter["quality"]["median_sample_size"] < 100:
        notes.append(f"THIN SAMPLES (median {quarter['quality']['median_sample_size']:.0f})")
    return ", ".join(notes)


def build_payload(
    quarters: List[Dict[str, Any]],
    housing_input: Path,
    macro_input: Path,
    housing_rows: int,
) -> Dict[str, Any]:
    covered = [quarter for quarter in quarters if quarter["housing"] is not None]
    return {
        "meta": {
            "title_fa": "قیمت مسکن، ارز و تورم — تهران",
            "base_default": quarter_code(*BASE_QUARTER),
            "housing_window": {
                "first": covered[0]["code"],
                "last": covered[-1]["code"],
                "first_label_fa": covered[0]["label_fa"],
                "last_label_fa": covered[-1]["label_fa"],
            },
            "macro_window": {
                "first": quarters[0]["code"],
                "last": quarters[-1]["code"],
                "first_label_fa": quarters[0]["label_fa"],
                "last_label_fa": quarters[-1]["label_fa"],
            },
            "inputs": {
                "housing": {
                    "path": str(housing_input.relative_to(REPO_ROOT)),
                    "sha256": sha256_of(housing_input),
                    "rows": housing_rows,
                    "districts": 22,
                },
                "macro": {
                    "path": str(macro_input.relative_to(REPO_ROOT)),
                    "sha256": sha256_of(macro_input),
                },
            },
            "method": [
                "هر ماه به فصل شمسی نگاشت می‌شود: فصل = (ماه − ۱) ÷ ۳ + ۱ (بهار تا زمستان).",
                "برای هر منطقه در هر فصل، میانهٔ میانه‌های ماهانهٔ همان منطقه گرفته می‌شود.",
                "شاخص شهر در هر فصل = میانهٔ ۲۲ مقدار منطقه‌ای (هر منطقه یک رأی) — نه میانگین وزنی‌شده با حجم.",
                "شاخص = مقدار ÷ مقدارِ فصل پایه × ۱۰۰؛ پایه به‌طور یکسان روی هر سه سری اعمال می‌شود.",
            ],
        },
        "series": [
            {
                "key": "housing",
                "label_fa": "قیمت مسکن — تهران (کیلیک)",
                "unit_fa": "تومان در هر متر مربع — قیمت پیشنهادی فروش",
                "level_label_fa": "قیمت پیشنهادی فروش هر متر مربع",
                "level_digits": 0,
                "approx": False,
                "trust_label_fa": "منبع کم‌اعتماد",
                "trust_note_fa": "سری کیلیک در اردیبهشت ۱۴۰۲ یک شکست سطحی دارد (هر ۲۲ منطقه در یک ماه ۳۱٪ تا ۷۸٪ جهش می‌کنند) و منطقهٔ ۱ در بهمن ۱۴۰۱ تا فروردین ۱۴۰۲ خراب است؛ به همین دلیل به‌طور پیش‌فرض خاموش است.",
                "hidden_default": True,
            },
            {
                "key": "fx",
                "label_fa": "نرخ ارز آزاد",
                "unit_fa": "تومان در هر دلار — تقریبی",
                "level_label_fa": "نرخ دلار آزاد",
                "level_digits": 0,
                "approx": True,
            },
            {
                "key": "cpi",
                "label_fa": "شاخص تورم (CPI)",
                "unit_fa": "شاخص کل CPI، پایهٔ ۱۴۰۰ = ۱۰۰ — بخشی تقریبی",
                "level_label_fa": "شاخص CPI (۱۴۰۰=۱۰۰)",
                "level_digits": 1,
                "approx": True,
            },
        ],
        "quarters": quarters,
        "caveats": [
            "هر سه سری دقیقاً بازهٔ یکسانی دارند (۲۱ فصل، تابستان ۱۴۰۰ تا تابستان ۱۴۰۵)؛ هیچ خطی بلندتر یا کوتاه‌تر از دیگری نیست و هیچ مقداری درون‌یابی یا جعل نشده است.",
            "هشدار سری مسکن — شکست سطحی در اردیبهشت ۱۴۰۲: بین فروردین و اردیبهشت ۱۴۰۲، هر ۲۲ منطقه در یک ماه ۳۱٪ تا ۷۸٪ جهش می‌کنند (منطقهٔ ۱ حدود ۳۲۶٪) و تعداد آگهی‌ها هم در همان ماه تقریباً دو برابر می‌شود. جهش یک‌ماههٔ سراسری با این اندازه، تغییر پوشش/روش کیلیک است، نه حرکت بازار. پس پلهٔ بهار ۱۴۰۲ و «تخت‌شدنِ» پس از آن دو روی یک سکه‌اند.",
            "هشدار سری مسکن — منطقهٔ ۱: در بهمن ۱۴۰۱ تا فروردین ۱۴۰۲ میانهٔ این منطقه ۳۰ تا ۳۱ میلیون است در حالی که p75 خودش ۱۱۰ تا ۱۲۵ میلیون است (نسبت میانه به p25 حدود ۴٫۳ برابر، در برابر حداکثر ۲٫۵ برابر برای بقیهٔ مناطق)؛ یعنی میانه بین دو تودهٔ قیمتی جابه‌جا می‌شود، نه اینکه قیمت را دنبال کند. سری کل شهر از این خطا تقریباً مصون است (اثر بر میانهٔ شهر: ۲٫۶٪−)، ولی خود این منطقه تا خرداد ۱۴۰۲ بی‌اعتبار است.",
            "هشدار سری مسکن — پرش حجم: آذر ۱۴۰۱ فقط ۱۸٬۲۱۶ آگهی در کل شهر دارد در برابر ۶۱٬۰۹۹ آگهی در ماه قبلش؛ سری از نظر حجم فهرست هم پیوسته نیست.",
            "پیامد در جای دیگر مخزن: پروندهٔ data/tehran_annual_price_increases پنجرهٔ ۱۲ماههٔ «۱۴۰۲» را روی همین شکست می‌سازد (۱۴۰۱-۰۶ تا ۱۴۰۲-۰۵)، پس سطح ۱۴۰۲ منطقهٔ ۱ عددی بی‌مرجع است و تغییر «۱۴۰۳ نسبت به ۱۴۰۲» آنجا ۸۷٪+ گزارش می‌شود، در حالی که رشد واقعی همان دوره حدود ۱۵٪ است.",
            "دادهٔ مسکن «قیمت پیشنهادی» آگهی‌های کیلیک است، نه قیمت معامله‌شده و نه آمار مرکز آمار؛ سطح آن با شاخص رسمی مسکن یکی نیست.",
            "فصل پایه (تابستان ۱۴۰۰) برای مسکن فقط یک ماه دارد (شهریور ۱۴۰۰)، چون سری کیلیک از همان ماه آغاز می‌شود؛ بقیهٔ فصل‌ها سه‌ماهه‌اند.",
            "ارز و تورم جدول دستی کارفرماست. فقط پنج فصل CPI دقیق است (تابستان ۱۴۰۲، زمستان ۱۴۰۳، زمستان ۱۴۰۴، بهار ۱۴۰۵، تابستان ۱۴۰۵) و بقیهٔ فصل‌های CPI گردشده‌اند؛ همهٔ ارقام ارز تقریبی‌اند. نقاط تقریبی در راهنما با «≈» نشان داده می‌شوند.",
            "شاخص CPI روی پایهٔ ۱۴۰۰ = ۱۰۰ گزارش شده و مقدار فصل پایه هم «≈۱۰۰» است؛ پس خط پایهٔ تورم خودش قطعی نیست و بازمحاسبه (rebase) روی همین عدد سوار می‌شود.",
            "کیلیک سری را با پنجرهٔ سه‌ماهه هموار می‌کند (windowMonths=3)، پس میانه‌های فصلی روی پنجره‌های هم‌پوشان ساخته می‌شوند.",
            "منطقهٔ ۲۰ در ۱۴۰۴–۱۴۰۵ هشت ماه trust=MODELED دارد — کل دوره هشت ماه از ۱٬۳۲۰ ردیف؛ این ماه‌ها حذف نشده‌اند، فقط در ستون کیفیت شمرده می‌شوند.",
            "این نمودار نسبت‌ها را نشان می‌دهد، نه علت‌ها: هم‌زمانی سه خط، علیت میان ارز، تورم و قیمت مسکن را اثبات نمی‌کند.",
        ],
        "sources": [
            "مسکن: کیلیک، سری ماهانهٔ قیمت پیشنهادی فروش، ۲۲ منطقهٔ تهران، ۱۴۰۰-۰۶ تا ۱۴۰۵-۰۵ (kilid/kilid_data).",
            "ارز و تورم: جدول فصلی درون‌مخزنی data/housing_price/fx_cpi_quarterly.csv (تقریبی، دستی؛ پایهٔ مشترک تابستان ۱۴۰۰ = ۱۰۰).",
        ],
    }


# --------------------------------------------------------------------------- outputs

def write_csv(path: Path, quarters: List[Dict[str, Any]]) -> None:
    def index(value: Optional[float]) -> Optional[float]:
        """Rebasing adds binary-float noise (110.00000000000001); keep the file readable."""
        return None if value is None else round(value, 6)

    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for quarter in quarters:
            row = {
                "quarter_code": quarter["code"],
                "jalali_year": quarter["year"],
                "jalali_quarter": quarter["quarter"],
                "quarter_label_fa": quarter["label_fa"],
                "months_observed": quarter["quality"]["months_observed"],
                "months_first": quarter["quality"]["months_first"] or "",
                "months_last": quarter["quality"]["months_last"] or "",
                "districts_present": quarter["quality"]["districts_present"],
                "modeled_months": quarter["quality"]["modeled_months"],
                "median_sample_size": quarter["quality"]["median_sample_size"],
                "housing_price_psm_toman": quarter["housing"],
                "housing_index": index(quarter["housing_index"]),
                "fx_toman_per_usd": quarter["fx"],
                "fx_index": index(quarter["fx_index"]),
                "fx_approx": 1 if quarter["fx_approx"] else "",
                "cpi_official_1400_100": quarter["cpi"],
                "cpi_index": index(quarter["cpi_index"]),
                "cpi_approx": 1 if quarter["cpi_approx"] else "",
                "housing_quality": quarter["housing_quality"],
            }
            writer.writerow({key: ("" if row[key] is None else row[key]) for key in FIELDS})


def write_readme(path: Path, payload: Dict[str, Any], quarters: List[Dict[str, Any]]) -> None:
    meta = payload["meta"]
    base = meta["base_default"]
    covered = [q for q in quarters if q["housing"] is not None]
    first, last = covered[0], covered[-1]
    lines = [
        "# قیمت مسکن در برابر ارز و تورم — شاخص فصلی",
        "",
        f"سه سری فصلی روی یک محور، همه با پایهٔ مشترک **{first['label_fa']} = ۱۰۰**:",
        "",
        "| سری | منبع | بازه |",
        "| --- | --- | --- |",
        f"| قیمت مسکن (تهران) | کیلیک، قیمت پیشنهادی فروش هر متر مربع، ۲۲ منطقه | {first['label_fa']} … {last['label_fa']} |",
        f"| نرخ ارز آزاد | جدول دستی کارفرما | {meta['macro_window']['first_label_fa']} … {meta['macro_window']['last_label_fa']} |",
        f"| شاخص تورم (CPI) | جدول دستی کارفرما (پایهٔ ۱۴۰۰=۱۰۰) | {meta['macro_window']['first_label_fa']} … {meta['macro_window']['last_label_fa']} |",
        "",
        "هر سه سری بازهٔ یکسانی دارند، پس هر سه خط هم‌طول‌اند و هیچ فصلی یک سری را بدون دیگری نشان نمی‌دهد.",
        "",
        "صفحه: `housing-price.html` در ریشهٔ مخزن (داده درون‌صفحه، بدون سرور).",
        "",
        "## روش",
        "",
        *[f"{index}. {step}" for index, step in enumerate(meta["method"], start=1)],
        "",
        f"پایه **{first['label_fa']} = ۱۰۰** است — نخستین فصلی که هم کیلیک و هم جدول ارز/تورم پوشش می‌دهند.",
        "صفحه پایه را تغییر نمی‌دهد و خط مسکن به‌طور پیش‌فرض خاموش است (منبع کم‌اعتماد)؛ با کلیک روی هر سری در راهنما",
        "می‌توان آن را روشن/خاموش کرد. شاخص‌ها روی دادهٔ خام محاسبه و در همان سند ثابت می‌شوند.",
        f"نمودار از **{first['label_fa']}** تا **{last['label_fa']}** ادامه دارد — بازه‌ای که هر سه سری در آن داده دارند.",
        "",
        "## بازهٔ مشترک (پایه تا آخرین فصل پوشش‌داده‌شده)",
        "",
        "| سری | مقدار در پایه | مقدار در آخرین فصل | ضریب رشد |",
        "| --- | ---: | ---: | ---: |",
    ]
    for series in payload["series"]:
        key = series["key"]
        start, end = first[key], last[key]
        lines.append(
            f"| {series['label_fa']} | {start:,.0f} | {end:,.0f} | ×{end / start:,.2f} |"
        )
    lines += [
        "",
        "## ستون‌های `quarterly_index.csv`",
        "",
        "* `housing_price_psm_toman` — سطح قیمت شهر در آن فصل (میانهٔ ۲۲ میانهٔ منطقه‌ای)، تومان بر متر مربع؛",
        "* `housing_index` / `fx_index` / `cpi_index` — شاخص‌ها با پایهٔ تابستان ۱۴۰۰ = ۱۰۰؛",
        "* `fx_approx` / `cpi_approx` — ۱ یعنی آن فصل تقریبی/گردشده است (همهٔ ارز و بیشتر CPI)؛ پنج فصل CPI دقیق‌اند:",
        "  تابستان ۱۴۰۲، زمستان ۱۴۰۳، زمستان ۱۴۰۴، بهار ۱۴۰۵، تابستان ۱۴۰۵.",
        "* `months_observed`, `months_first`, `months_last` — چند ماه از فصل در سری کیلیک حاضر است",
        "  (فصل‌های ابتدایی و پایانی کامل نیستند)؛",
        "* `districts_present`, `modeled_months`, `median_sample_size`, `housing_quality` — پرچم‌های کیفیت.",
        "",
        "## آنچه این فایل نمی‌گوید",
        "",
        *[f"* {caveat}" for caveat in payload["caveats"]],
        "",
        "برای بازتولید، این اسکریپت را اجرا کنید: `python3 scripts/build_housing_price_index.py`.",
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
    parser.add_argument("--housing-input", default=str(DEFAULT_HOUSING_INPUT))
    parser.add_argument("--macro-input", default=str(DEFAULT_MACRO_INPUT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--page", default=str(DEFAULT_PAGE))
    args = parser.parse_args(argv)

    housing_input = Path(args.housing_input)
    macro_input = Path(args.macro_input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(housing_input, encoding="utf-8", newline="") as handle:
        housing_rows = sum(1 for _ in csv.DictReader(handle))

    housing = load_housing(housing_input)
    macro = load_macro(macro_input)
    quarters = build_quarters(housing, macro)
    payload = build_payload(quarters, housing_input, macro_input, housing_rows)

    write_csv(out_dir / "quarterly_index.csv", quarters)
    with open(out_dir / "index_data.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    write_readme(out_dir / "README.md", payload, quarters)
    render_page(TEMPLATE, Path(args.page), payload)

    covered = [q for q in quarters if q["housing"] is not None]
    first, last = covered[0], covered[-1]
    print(f"housing rows   : {housing_rows}")
    print(f"quarters       : {len(quarters)} ({quarters[0]['label_fa']} … {quarters[-1]['label_fa']})")
    print(f"housing window : {first['label_fa']} … {last['label_fa']} ({len(covered)} quarters)")
    print(f"base           : {first['label_fa']} = 100")
    for series in payload["series"]:
        key = series["key"]
        print(f"  {key:8} ×{last[key] / first[key]:.2f}  ({first[key]:,.0f} -> {last[key]:,.0f})")
    print(f"outputs        : {out_dir}/quarterly_index.csv, index_data.json, README.md")
    print(f"page           : {args.page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
