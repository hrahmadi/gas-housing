# Handoff — problem for outside advice: Tehran affordability map vs. the data

**Project:** Interactive Persian data-article «ارتباط بین مصرف بنزین و هزینه بالای مسکن» (gasoline consumption ↔ housing cost / spatial inequality in Iran), to be published as a single static page on GitHub Pages.

**Author of this note:** GitHub Copilot (building the page) — **looking for an independent, fresh-eyes design/analytics opinion.**

---

## 1. What the article claims (narrative-first)

Iran’s gasoline consumption roughly doubled in two decades (56 → 120 million L/day, 1382–1402). The article’s thesis: part of that fuel is not “joyriding”; it is the **energy cost of spatial inequality** — housing unaffordability pushes workers toward cheaper housing on the periphery of Tehran, so the distance between affordable housing and employment grows, and the daily commute becomes a fixed energy cost.

The article must **not** claim a national causal coefficient, and must keep OBSERVED vs CALCULATED vs ESTIMATED clearly separated. Scene 2 is supposed to make the housing-side mechanism concrete.

## 2. The centerpiece interaction (Scene 2) and the problem

**Figure design (already built):** choropleth of Tehran’s 22 municipal districts (real district geometry + real quarterly district-level rent per m², Spring 1388 → Summer 1400, from Iran Statistics Center via the open “Tehran rent/affordability” project). Controls:
- year slider 1388–1400
- household income = 1×/2×/3×/5× of that year’s statutory minimum wage
- apartment size (m²), rent-share standard (% of income)

A district is “affordable” when `rent/m² × size ≤ min_wage(year) × multiple × share`.

**The problem I found while calibrating the figure:**

When you compare these official district rents to the official *minimum wage*, the number of affordable districts does **not** decline monotonically from 1388 to 1400. It fluctuates and often rises in the middle years. Real measured counts of affordable districts (of 22):

| params | 1388 | 1389 | 1390 | 1391 | 1392 | 1393 | 1394 | 1395 | 1396 | 1397 | 1398 | 1399 | 1400 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2× min wage, 35 m², 35% | 4 | 5 | 4 | 2 | 3 | 5 | 6 | 6 | 6 | 6 | 6 | 5 | 5 |
| 2× min wage, 30 m², 35% | 9 | 11 | 6 | 4 | 6 | 6 | 10 | 12 | 12 | 9 | 8 | 6 | 6 |
| 3× min wage, 30 m², 35% | 19 | 18 | 17 | 13 | 14 | 18 | 18 | 18 | 18 | 18 | 17 | 15 | 17 |
| 3× min wage, 40 m², 30% | 9 | 9 | 6 | 4 | 4 | 6 | 7 | 10 | 10 | 9 | 7 | 6 | 6 |
| 1× min wage, any size | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Why:** statutory minimum wage grew *about in step* with these official rents (rent ~11×, min wage ~10×, 1388→1400). The dips line up with sharp wage decisions (1391–92, 1399). Meanwhile the *popular* claim — and the article’s prose — says “affordable geography shrank and households were pushed out.” The official numbers don’t show an aggregate collapse on a minimum-wage yardstick.

## 3. What I need advice on (please pick any)

1. **Framing.** Given the data above, what is the most honest and still-powerful way to use this district map to support “affordable housing and jobs are becoming spatially separated”? The map’s real, defensible content seems to be: (a) at any fixed income there is a strong *spatial* pattern (which districts are affordable, and where they sit relative to job centres); and (b) whether the *set* of affordable districts changes location over time. Should we drop the “shrinking over time” reading entirely, or reframe it?

2. **Income yardstick.** Is comparing rent to the *statutory minimum wage* the right reference, or misleading? (Min wage is a floor, not the median; middle/real wages likely lagged more, but we have no defensible median-income series — inventing one risks overclaiming, which the article forbids.) Alternatives we considered:
   - (A) keep “multiple of that year’s min wage” (current), accept no temporal collapse, emphasize spatial pattern;
   - (B) anchor income in 1400 money and deflate backwards by official wage growth (the approach of the original source project) — mathematically ≈ same as (A), so probably won’t change the conclusion;
   - (C) switch the figure to show **real rent per district** (rent deflated by a wage/CPI index) rather than a pass/fail affordability test;
   - (D) use *house purchase* price per m² vs wages as the “shrink” visual instead of rent (but purchase prices are not the lived experience of a worker renting);
   - (E) add a second, smaller panel showing rent-vs-min-wage index nationally to set context, and keep the map as the spatial figure only.

3. **Job-centre overlay.** To make “spatial separation” visible we want to mark where jobs are. We don’t have an employment-density layer for the 22 districts. Reasonable proxies: central-CBD districts (e.g., 6, 7, 11, 12) drawn as an outline, or a statement in prose. Any better low-cost overlay idea that stays honest?

4. **Periphery figure.** Scene 3 shows built-up-area growth 2010–2020: Tehran ~5% vs Pardis 245%, Pishva 188%, Pakdasht 162%, Robat Karim 139%, etc. (metropolitan-region study). This *does* clearly support outward displacement and is our strongest spatial evidence. Should the article lean more on this and treat Scene 2’s map as supporting context only?

5. **Anything that would make a reviewer (data journalist / urban economist) object** to the current figures? Which claims are at risk of overreach?

## 4. Constraints we must respect

- No claim of causal, quantified national effect of housing on gasoline.
- OBSERVED / CALCULATED / ESTIMATED must be visible per figure (we label chips/footnotes).
- Parand commute figures (30–40k travellers/day; 35–50 km one-way; ~100 km/day) are **reported estimates**, not an official OD matrix — must stay labeled as such.
- Rent series definitions: Iran Statistics Center district rents (monthly rent + 3% deposit per m²) vs Central Bank citywide rent series differ slightly; 1401+ not in the district data; the 1402 Esfand house-price point (81.44 M toman/m²) is a spot value, not an annual average.
- Single static HTML page, Persian RTL, no server, must run on GitHub Pages; all figures render client-side.

## 5. Quick orientation for the advisor

- The district rent dataset: `data/tehran_rent_district.csv` (long format) and the affordability model in `js/views.js` (`buildMap`, `ratioFor`, `mapBudget`).
- Annual series (gasoline, min wage, rents, house prices): `data/annual.csv`; assumptions: `data/assumptions.json`.
- Source workbook handoff: `gasoline_housing_dataset_handoff.md` (tiers A–D and “what not to claim”).

**Bottom line question:** With the numbers above, what is the strongest *defensible* visual treatment for “where can a worker afford to live in Tehran, and why does that push them away from work?” We’d rather make the figure smaller and true than big and overstated.
