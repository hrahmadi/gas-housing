# Math / Data Verification Handoff — Gas–Housing article

**Status:** AUDIT — nothing in the article/code has been changed yet.
**Date:** 2026-09-06 (Iranian ۱۴۰۵-۰۶-۱۵)
**Prepared for:** fresh-eyes independent check before publication.

**Where this file lives:** `docs/math_verification_handoff.md`
(full path: `/Users/hamidreza/Documents/AI-Projects/Gas-Housing/docs/math_verification_handoff.md`)

Every number below was recomputed from the repo's own CSVs
(`data/annual.csv`, `data/tehran_rent_district.csv`, `data/rent_wage_index.csv`,
`data/periphery.csv`, `data/assumptions.json`) by mirroring the formulas in
`js/views.js`. Recomputation script logic is documented inline per row.

Legend: ✅ internally consistent · ⚠️ needs a decision/source · ❌ mismatch or risk

---

## 0. Author decisions (2026-09-06)

- **A** (rent series) — *resolved:* the figure under question is the **live** rent-wage
  line chart (شکل ۲ «رشد اجاره در برابر حداقل دستمزد»); it is **not** commented out.
  What *is* commented out is the older interactive affordability **map** (شکل ۲ · تعامل
  with `#map-svg`), which is absent from the rendered DOM. Findings A and B below apply
  only to the live static rent-wage chart. Author to decide which series is authoritative
  (district-derived vs S12 official) — **decision still open**; see §2.
- **B** (۱۴۰۰ partial-year point) — applies to the **same live rent-wage chart (شکل ۲)**,
  which is a static (non-interactive) figure. Not the commented map. Decision open: drop
  the point, label it «تا تابستان ۱۴۰۰» on the axis, or annualise. See §2.
- **C** (shock wage) — *recommendation 1 accepted*: label the wage as «حداقل دستمزد ۱۴۰۵
  (۲۲ میلیون تومان/ماه)» in fig-cap + chips + `shock-note`, and add a source/assumption
  entry for the ۱۴۰۵ figure. (Rec 2–3 to follow when implementing.)
- **D** («بیش از ۳۲۵ هزار نفر») — **keep as-is.**
- **E** («۸۲ درصد مدارس دو شیفته») — **keep as-is.**
- **F** (gas legend «اوج مصرف از ۱۴۰») — **keep as-is.**
- **G** (hero) — change wording from «تقریبا دو برابر شده» → **«بیشتر از دو برابر شده»**
  (۵۶→۱۲۹ is 2.30×).

---

## 0b. Quick summary of the things most worth a second look

| # | Where | Issue | Severity |
|---|-------|-------|----------|
| A | Rent–wage chart (شکل ۲ — live) | Two different rent series live in the repo and they tell **opposite** stories about whether rent outpaced the minimum wage by ۱۴۰۰. The visible chart uses the district-derived series; an "official" series (S12) also in the data says the opposite. (Not the commented map.) | 🔴 |
| B | Rent chart ۱۴۰۰ point (live شکل ۲) | ۱۴۰۰ has only ۲ quarters (spring+summer); all other years have ۴. The last rent point is a partial-year average. | 🟠 |
| C | Shock figure wage | `minWage: 22` (million toman) = **۱۴۰۵ statutory minimum wage per author**. The bundled min-wage series (S3) stops at ۱۴۰۲ ≈ ۵.۳M toman, so 22M is *not derivable* from repo data. **Decision: label it explicitly as ۱۴۰۵ + add source note.** | 🟠 |
| D | «بیش از ۳۲۵ هزار نفر از تهران خارج شدند» (۱۳۹۰–۱۳۹۵) | External claim; no source row in `data/sources.csv`. Bundled census (C1) shows Tehran city population *rising* ۸.۱۵M→۸.۶۹M over that window. **Decision: keep as-is.** | 🔴 → keep |
| E | «۸۲ درصد مدارس کمال‌شهر دو شیفته» (۱۳۹۷) | External claim; no source row in the repo. **Decision: keep as-is.** | 🟠 → keep |
| F | Gas legend «روزهای اوج مصرف از ۱۴۰ میلیون لیتر در روز نیز گذشته است» | Claim is above the chart's own max (۱۴۰۴ = ۱۲۹). Real peak-day record exists but is not in the bundled series. **Decision: keep as-is.** | 🟠 → keep |
| G | Hero «تقریبا دو برابر شده» | ۵۶→۱۲۹ is ۲.۳۰× — more than double. **Decision: change wording to «بیشتر از دو برابر شده».** | 🟡 → fix |

---

## 1. Gasoline national series (شکل ۱ + hero)

**Source:** `annual.csv` variable `gasoline` (S5 to ۱۴۰۲, S11 for ۱۴۰۳/۱۴۰۴).

| Claim | Data | Check |
|---|---|---|
| ۱۳۸۲ ≈ ۵۶ M L/day | 1382 = 56 | ✅ |
| ۱۴۰۴ ≈ ۱۲۹ M L/day | 1404 = 129 | ✅ (S11, project-supplied — verify externally) |
| Ratio ۵۶→۱۲۹ | 129/56 = **2.30×** | ✅ (wording change approved: «بیشتر از دو برابر شده» — G) |
| ۱۴۰۳ ≈ ۱۲۴ | 1403 = 124 | ✅ (S11) |
| افت ۱۳۹۹ / کرونا | 1399 = 75 (down from 89 in 1398) | ✅ |
| Legend: «اوج مصرف از ۱۴۰ گذشته» | max in series = 129 | ⚠️ see F above |

Computed series (M L/day): 1382=56 … 1399=75, 1400=88, 1401=105, 1402=120, 1403=124, 1404=129.

---

## 2. Rent vs minimum-wage (شکل ۲ — live, NOT commented) — ⚠️ highest-attention item

> Scope clarification (from inspection): the **interactive affordability map** (old
> «شکل ۲ · تعامل», `#map-svg`) is commented out and absent from the rendered DOM. The
> **rent-wage line chart** discussed here is a **separate, live, static figure**
> («رشد اجاره در برابر حداقل دستمزد», `#rent-wage-chart`), numbered شکل ۲. All findings
> in this section concern that live chart.

The chart in `js/views.js` (`drawRentWageIndex`) builds the **rent** line from the
*district-derived* citywide index (equal-weight mean of the 22 municipal-district
annual averages, base ۱۳۸۸ = 100) and the **wage** line from the statutory minimum-wage
series (S3), also base ۱۳۸۸ = 100.

Recomputed district citywide rent index (equal mean of 22 districts, base 1388=100):

| Year | rent index | wage index (from S3) | S12 "official" rent index |
|------|-----------|----------------------|---------------------------|
| 1388 | 100.0 | 100.0 | 100 |
| 1390 | 139.3 | 125.3 | 146 |
| 1392 | 226.1 | 184.9 | 191 |
| 1394 | 273.8 | 270.3 | 226 |
| 1396 | 346.5 | 352.9 | 276 |
| 1398 | 596.0 | 575.6 | 495 |
| 1399 | 837.3 | 696.5 | 650 |
| 1400 | **1146.1** | **1007.7** | **819** |

Wage index recomputed from S3 matches the S12 wage column within rounding
(e.g. ۱۴۰۰: 1007.7 vs 1006; ۱۴۰۲: 2014.4 vs 2014). ✅

**The problem (A):** the *district* series puts rent (1146) **above** wage (1008) at
۱۴۰۰ — supporting the article's claim that rent outpaced the minimum wage. The
*official-style* series already present in the repo (`rent_wage_index.csv`, source S12,
note says "definition differs from the district-level series used in Figure 2") puts
official rent (819) **below** wage (1006) at ۱۴۰۰ — the opposite conclusion.
`rent_wage_index.csv`/S12 is loaded into `data.js` but is not used by any visible view.

**Decision needed:** state explicitly which series is authoritative and why, and/or
reconcile the two. If the official index is the right one for "did rent outpace the
minimum wage?", the current figure may be showing the more favourable of two series.

**Partial-year issue (B):** ۱۴۰۰ contains only quarters 49–50 (بهار/تابستان) in all 22
districts; every other year has all four quarters. In ۱۳۹۸–۱۳۹۹ the spring+summer
average is ~94–96% of the full-year average, so a 2-quarter ۱۴۰۰ point is not strictly
comparable to the full-year points around it. Options: drop ۱۴۰۰ from the rent line,
label it «تا تابستان ۱۴۰۰» on the axis, or annualise with a seasonal factor. (The
existing footnote already says "تا تابستان ۱۴۰۰".)

---

## 3. Periphery built-up growth (شکل ۳ + prose)

**Source:** `periphery.csv` metric `built_up_growth_2010_2020` (S6).

| Place | Data % | Prose | Map label | Check |
|---|---|---|---|---|
| Pardis (پردیس) | 244.8 | «حدود ۲۴۵» | ۲۴۴.۸٪ | ✅ |
| Pakdasht (پاکدشت) | 162.3 | «حدود ۱۶۲» | ۱۶۲.۳٪ | ✅ |
| Robat Karim (رباط کریم) | 138.5 | «حدود ۱۳۹» | ۱۳۸.۵٪ (shown on پرند) | ✅ (138.5 ≈ "حدود ۱۳۹") |
| Tehran | 4.8 | «فقط حدود ۵» | — | ✅ |
| Pishva | 187.8 | — | ۱۸۷.۸٪ | ✅ (map only) |
| Shahriar | 82.9 | — | ۸۲.۹٪ | ✅ |
| Rey | 58.0 | — | ۵۸.۰٪ | ✅ |

Note: پرند's dot on the map uses Robat Karim county's figure (138.5) because Parand is a
new town inside that county — this is explicitly labelled in the figure. ✅

---

## 4. National-scale thought experiment (شکل ۴)

**Source/params:** `assumptions.json` `nationalCommute`
(employed 24.822M = S15 project-supplied; eff 9 L/100km; baseline ۱۴۰۰ = 88;
production ceiling ≈ 120 M L/day — `dailyProductionMillionLitresPerDay`; km options 5/10/15/20).

Formula (as coded in `natSeries`):
`value(year_i) = 88 + 24.822 × (2 × km × i) × 9/100`, i = years since ۱۴۰۰.

Verified (km = 10):

| Year | i | formula | recomputed | chart label |
|------|---|---------|-----------|-------------|
| 1400 | 0 | 88 | 88.0 | 88 (baseline, not labelled) |
| 1401 | 1 | 88+24.822·20·0.09 | 132.7 | ۱۳۳ |
| 1402 | 2 | 88+24.822·40·0.09 | 177.4 | ۱۷۷ |
| 1403 | 3 | … | 222.0 | ۲۲۲ |
| 1404 | 4 | … | 266.7 | ۲۶۷ |
| 1405 | 5 | … | **311.4** | **۳۱۱** |

Headline: ۱۴۰۵ = ۳۱۱, «۲۲۳ میلیون لیتر بیشتر از نقطه شروع» → 311.4−88 = 223.4 ≈ ۲۲۳. ✅
Legend base (۸۸) = actual ۱۴۰۰ gasoline (annual.csv 1400=88) ✅.

**Fig-4 dashed line (2026-09-06 change):** the blue dashed reference is now the
**daily production ceiling ≈ ۱۲۰ M L/day** (assumption `dailyProductionMillionLitresPerDay`),
replacing the previous «مصرف واقعی ≈ ۱۲۹» reference. Legend reads «تولید روزانه ≈ ۱۲۰».
Captions updated accordingly. (The old consumption reference at 129 came from S11; the
production figure ≈120 is an estimate — keep the "verify before publication" note.)

⚠️ Conceptual note for reviewers: the model takes the *actual* ۱۴۰۰ consumption (88) as
the "everyone lives near work" baseline, then adds incremental commute distance on top.
Since 88 already contains real commuting, this is a marginal/counterfactual exercise
(clearly labelled «آزمایش ذهنی» in the piece) — acceptable, but the caption could note
that 88 is not a no-commute baseline.

⚠️ S15 (employed 24.822M) and the production figure (≈120) are project-supplied; the
fig-cap already says they must be verified — keep that warning until publication.

---

## 5. Parand commute (شکل ۵ + fuel card)

**Sources/params:** `periphery.csv` (S9): one-way 35–50 km; daily travelers 30–40k;
assumption: 100 km/day round trip; 9 L/100 km; 22 work days/month.

| Output | Formula | Value | Check |
|---|---|---|---|
| Daily round trip | assumption | ~100 km | ✅ |
| Monthly distance @22 d | 22×100 | 2,200 km | ✅ |
| Monthly fuel @9L/100km | 2200×9/100 | 198 L | ✅ (fuel card shows ۱۹۸) |
| Travelers | S9 | 30–40k | ✅ (prose «۳۰ تا ۴۰ هزار») |
| Distance to Tehran | S9 | 35–50 km | ✅ |

Prose says «حدود ۳۵ کیلومتر» (low end of the 35–50 band) — fine with «حدود», and the
fig-cap gives the 35–50 range. ✅

---

## 6. Price-shock interaction (شکل ۶)

**Params:** fixed 100 km/day × 22 days = 2,200 km/month; eff 9 L/100km → 198 L/month;
wage = `minWage × mult` (million toman); share = 198×price / (wage×1e6) × 100.

Verified at mult = 1, wage = 22 (million toman/month):

| Price (toman/L) | Monthly cost (toman) | Share of 22M | Chart |
|---|---|---|---|
| 3,000 | 594,000 | 2.7% | ✅ |
| 5,000 | 990,000 | 4.5% | ✅ |
| 10,000 | 1,980,000 | 9.0% | ✅ |
| 25,000 | 4,950,000 | 22.5% | ✅ |
| 50,000 | 9,900,000 | 45.0% | ✅ |
| 100,000 | 19,800,000 | 90.0% | ✅ |
| 300,000 | 59,400,000 | 270% (overflow, capped display at 120) | ✅ |

Internal arithmetic is consistent.

⚠️ **Wage basis (C):** `SHOCK.minWage = 22` is labelled «۱ برابر حداقل دستمزد (۲۲ میلیون
تومان/ماه)». **Per the author, 22M toman = the ۱۴۰۵ statutory minimum wage** (not ۱۴۰۰).
The bundled S3 min-wage series ends at ۱۴۰۲ ≈ ۵.۳M toman, so 22M cannot be derived from
repo data. **Decision (rec-1 accepted):** when implementing, add an explicit year —
«حداقل دستمزد ۱۴۰۵ (۲۲ میلیون تومان/ماه)» in the fig-cap, the chips label, and the
`shock-note` string — and add a source/assumption entry for the ۱۴۰۵ figure. (Also
reconcile with the methodology note that implies ≈5.5M toman for ۱۴۰۲; a ~4× jump to 22M
by ۱۴۰۵ should be intentional and sourced.)

---

## 7. Water / factual historical claims in prose (no numeric model)

| Claim | Check |
|---|---|
| آبان ۱۳۹۸: سهمیه‌ای ۱۰۰۰→۱۵۰۰، آزاد ۱۰۰۰→۳۰۰۰ تومان | ✅ well-documented 2019 facts |
| «بیش از ۳۲۵ هزار نفر از تهران خارج شدند» (۱۳۹۰–۱۳۹۵) | ❌ no source in repo; see D |
| «۸۲ درصد مدارس … دو شیفته» (کمال‌شهر، ۱۳۹۷) | ⚠️ no source in repo; see E |

---

## 8. Open questions for the fresh-eyes reviewer

1. **(A)** Which rent series should the public chart use — district-derived (rent>wage by
   ۱۴۰۰) or the official index already in the repo (wage>rent by ۱۴۰۰)? Document the choice.
2. **(B)** Should the ۱۴۰۰ rent point (2 quarters only) stay, be dropped, or be labelled
   «تا تابستان» on the axis?
3. **(C)** Confirm & source the ۱۴۰۵ minimum wage = 22M toman; label the year everywhere in
   the shock figure; reconcile with the ۱۴۰۲-based methodology note.
4. **(D)** Source for the 325k out-migration claim (which group/geography/period), and how
   it squares with the bundled C1 census (Tehran population grew 1390→1395).
5. **(E)** Source for the 82% double-shift schools figure.
6. **(F)** Source (dated) for the «اوج مصرف از ۱۴۰ M L/day» gas legend claim.
7. **(G)** Wording: 2.30× — «تقریبا دو برابر» vs «بیش از دو برابر».
8. Confirm S11 (۱۴۰۳=۱۲۴, ۱۴۰۴=۱۲۹) and S15 (24.822M employed) externally before publish
   (already flagged inside the article itself).

---

## 9. Files used (all read-only)

- `data/annual.csv` (gasoline / min_wage / house_price / tehran_rent)
- `data/tehran_rent_district.csv` (22 districts, quarterly)
- `data/rent_wage_index.csv` (S12 official-style index; loaded, **not** used by any view)
- `data/periphery.csv`
- `data/assumptions.json`
- `data/sources.csv`
- `js/views.js` (drawGas, drawRentWageIndex, drawPeriMap, drawNationalCommuteScale,
  buildParandScene/renderParandOutput, drawShock)
- `index.html` (prose claims)
