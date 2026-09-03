# Project Status & Consultation Brief — «بنزین، مسکن و نابرابری فضایی»

**Date:** 2026-09-03
**Status:** Desktop prototype complete, all interactions working, local Git commits ready, **not yet published**.
**Intended audience:** data journalist / urban economist / front-end reviewer (fresh eyes).

---

## 1. What was accomplished

A single static, Persian RTL, interactive data-article is built from the two original handoffs
(dataset handoff + article handoff) plus the actual article text (`article.rtf`) and the revised
Scene-2 direction (`docs/gasoline_housing_scene2_revised_handoff.md`).

### Deliverables

| Item | Location |
|---|---|
| Article page (all narrative + 6 figures) | `index.html` |
| Styles (dark, editorial, RTL, Vazirmatn) | `css/style.css` |
| Logic (formatters / renderers / boot) | `js/util.js`, `js/views.js`, `js/article.js` |
| Source-of-truth data | `data/annual.csv`, `data/periphery.csv`, `data/sources.csv`, `data/assumptions.json`, `data/tehran_rent_district.csv` |
| Generated runtime data | `data/data.js`, `assets/geo/tehran_districts.js` |
| Data build script | `scripts/build_data.py` |
| Run/publish notes | `README.md` |

### Interactive figures (all client-side, no backend)

1. **شکل ۱ — Gasoline line chart (1382–1402):** 56 → 120 million L/day, COVID-1399 dip annotated, hover-on-point readouts. *(OBSERVED)*
2. **شکل ۲ — Tehran affordability map (22 municipal districts):** real district geometry; quarterly district rents (Spring 1388 → Summer 1400); year slider; income = 1×/2×/3×/5× of that year’s statutory minimum wage; apartment size and rent-share sliders; click-a-district detail; disclaimer that it shows *approximate affordability geography, not actual residence*. *(CALCULATED model)*
3. **شکل ۲-ب — Rent index vs. minimum-wage index (1388 = 100):** supporting context showing the non-monotonic relationship. *(OBSERVED, indexed)*
4. **شکل ۳ — Metropolitan-region built-up growth 2010–2020:** Pardis ≈ 245%, Pishva ≈ 188%, Pakdasht ≈ 162%, Robat Karim ≈ 139%, Shahriar ≈ 83%, Rey ≈ 58%, Tehran ≈ 5% (schematic proportional-symbol map, click for values). *(OBSERVED — single study)*
5. **شکل ۴ — Parand route stepper:** one-way 35–50 km → ~100 km/day round trip → 2,200 km/month (22 workdays); animated route; clearly labeled as reported estimates. *(ESTIMATED/REPORTED)*
6. **شکل ۵ — Commute fuel calculator:** distance × workdays → km/month; 7/9/12 L per 100 km → 154/198/264 L/month; price × liters → monthly cost; cost ÷ wage → % of income; burden bar. *(CALCULATED/SCENARIO)*
7. **شکل ۶ — Fuel-price shock sensitivity:** price steps ×1–×10 (base 3,000 toman/L scenario), fuel-efficiency chips, income slider → monthly commuting cost and % of income. *(CALCULATED/SCENARIO)*

Every figure carries an OBSERVED / CALCULATED / ESTIMATED label in its caption (per the handoffs’ requirement).

### Revisions from the fresh-eyes review — already applied
- Map reframed from “affordable Tehran steadily shrank” → “affordability has a geography” (the data does not support monotonic decline; minimum wage roughly tracked official rents, ~10× vs ~11× over 1388–1400).
- Disclaimer added; 1×-minimum-wage result phrased as a model result, not a claim about where min-wage workers live.
- Added the rent-vs-wage index context chart.
- Job-centre overlay kept **qualitative** (no unverified “districts 6/7/11/12 = employment centres” labeling).
- Scene 3 (peripheral growth) treated as the stronger evidence of **peripheral expansion associated with housing-affordability pressure** (documented spatial pattern, not an established causal mechanism).

### Verification performed
- All six figures render with **zero console errors** (tested in Chromium via Playwright).
- Interactions spot-checked for correct arithmetic, e.g.:
  - 100 km/day × 22 days = 2,200 km/month;
  - 2,200 km × 9 L/100 km = 198 L/month; ×12 → 264 L/month;
  - 198 L × 3,000 toman/L ≈ 594k toman/month ≈ 9.9% of a 6M-toman wage;
  - at 15,000 toman/L the same commute ≈ 49.5% of that wage;
  - affordable districts at default (1388, 2×, 35 m², 35%) = districts 15, 18, 19, 20 — the genuinely low-rent south/east districts, i.e., geographically plausible.
- Local Git repo initialized on `main`; 2 commits ready to push to `https://github.com/hrahmadi/gas-housing`.

---

## 2. Data foundation (and its caveats)

Sources are enumerated with ids/URLs in `data/sources.csv`. Key datasets:

- **District-level rents (main map input):** Iran Statistics Center quarterly rent per m² per municipal district (Spring 1388–Summer 1400), obtained through the open Ali Tayebi project (`github.com/alitayebi/maps/.../rent`). Values are rials/m²; /10 → toman/m².
- **Annual series (`annual.csv`):** gasoline consumption, Tehran house price/m², statutory minimum wage, CBI citywide rent.
- **Periphery growth:** single metropolitan-region research study (housing transactions + satellite built-up, 2010–2020).
- **Parand commute:** reported figures only (30–40k daily travellers; 35–50 km one-way). No public origin–destination matrix found — per the revised handoff, version 1 proceeds without one.

**Caveats a reviewer should weigh:**
1. District rent series **ends Summer 1400** — the post-1400 (1401–1403) surge in market rents is not in the map data, so the map may understate current pressure.
2. Two different rent definitions exist (SCI district rents vs CBI citywide series) and differ modestly.
3. Minimum wage is a **floor**, not median income; all affordability is therefore conservative and scenario-based.
4. The 1402 house-price point (81.44 M toman/m², Esfand) is a spot value, not an annual average; not used as such.
5. Parand and periphery numbers rest on reported/single-study evidence (labeled ESTIMATED / confidence B).

---

## 3. Open problems & issues (please advise)

### Already resolved (external review, 2026-09-03 — implemented)
1. **Map framing & controls** → resolved: map = *spatial affordability* (no temporal-shrink claim); income selector retained (no extra “two-earner household” presets); the default scenario is now explicitly a fictional household («سناریوی خانوار فرضی: درآمد ۲ برابر حداقل دستمزد…») and the caption points out the 4 default-affordable districts are *not* random — they cluster in the cheaper south/south-east.
2. **Income yardstick** → resolved: statutory minimum wage retained; UI labels income as «چند برابر حداقل دستمزد قانونی» (scenario, NOT average income); no median-wage hunt for Scene 2.
3. **Post-1400 gap** → resolved: no extrapolation; a visible caveat under the map states district-level rent data ends Summer 1400; later years are covered only by the independent citywide rent series in prose.
4. **Income anchors across figures** → resolved: map labelled a *historical affordability model*; calculator/shock labelled *illustrative contemporary scenario* (sample income 6M toman/month); the “≈1.1× min wage of 1402” relation moved to the methodology footnote.
5. **1398 scene** → resolved: distributional-exposure framing only (no protest-causation claim).
10. **Raw geometry committed** → resolved: raw inputs vendored under `data/raw/regions8800.geojson` + `data/raw/infl.json` (source note in `data/raw/README.md`); `scripts/build_data.py` now defaults to them, so a fresh clone runs `python3 scripts/build_data.py` with no external download.

### Still open
6. **Periphery figure is schematic** (approximate county positions), not real county polygons. Acceptable for v1 as long as it visibly says “schematic” (it does)? True choropleth is a later upgrade, not a blocker. (Growth numbers are from a single study — confidence B.)
7. **No employment-density layer.** Job-centre relationship stays qualitative/prose. Any low-cost, defensible proxy? (Functional-area indicators in `periphery.csv` are NOT commuter headcounts.)
8. **Map accessibility:** SVG districts are clickable with `<title>` tooltips but have no keyboard selection path. Chips/sliders are native. Is keyboard parity required for this publication?
9. **Mobile/responsive:** desktop-first per handoff; inline layout degrades but isn’t polished for small screens. Fix before public launch, or is desktop-first acceptable?
11. **Gasoline-price baseline (3,000 toman/L)** is a scenario anchored to ~1402 policy, not a sourced “current price.” A current-price citation is needed if the piece must speak to the present.
12. **Version cache-buster** (`?v=N` on script tags) is manual — harmless, but would be replaced if a build step is ever added.

---

## 3.5 What this article does NOT establish

This article does **not** estimate what percentage of Iran’s gasoline consumption is caused by housing costs. It does **not** establish a causal relationship between Tehran rent increases and national gasoline demand.

It demonstrates a **plausible and observable mechanism at the metropolitan and household level**:
- housing affordability can affect *where* workers live;
- peripheral residence can increase necessary work travel;
- that additional distance has a measurable energy and financial cost.

This statement lives in the repository (see also the Persian caveat box at the end of `index.html`) so that a future editor/developer cannot accidentally “strengthen” the copy into an overclaim.

---

## 4. If you can share better data, highest value upgrades

1. Any **municipality-level work-trip / OD** tables (2016 census, RMTO, Tehran transport-plan matrices) → would let Scene 4/5 become observed rather than scenario.
2. **Employment/establishment counts by district** → enables a defensible job-centre overlay for the map.
3. **A rent or income series 1401–1403+** → extends the map’s end date.
4. **County boundary GeoJSON** for Tehran province → true choropleth for the periphery figure.

---

## 5. How to reproduce

```bash
# serve locally
python3 -m http.server 8901
# open http://localhost:8901/

# regenerate data (only if data/*.csv or assumptions change)
python3 scripts/build_data.py   # reads data/raw/regions8800.geojson + data/raw/infl.json
```

Publish: `git remote add origin https://github.com/hrahmadi/gas-housing.git && git push -u origin main`,
then GitHub → Settings → Pages → Deploy from branch `main` / `(root)`.
