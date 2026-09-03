# To-Do — Interactive Article: Gasoline, Housing & Spatial Inequality in Iran

Source docs read:
- `gasoline_housing_dataset_handoff.md` (datasets / evidence rules)
- `gasoline_housing_interactive_article_handoff.docx` (editorial + tech handoff)

Status of docs: **Ready for desktop-first prototype** · Target: **publish on GitHub Pages**

---

## Phase 0 — Project & data foundation

- [ ] Create a GitHub repository for the project (needed before GitHub Pages deploy)
- [ ] Scaffold folder structure:
  - `index.html` (single self-contained article page)
  - `data/` with `annual.csv`, `tehran_rent_district.csv`, `periphery.csv`, `sources.csv`, `assumptions.json`
  - `js/` (or inline structured modules) for narrative, data, calculations, visualizations, source metadata
  - `assets/` for lightweight SVG/GeoJSON geometry
- [ ] Extract & inspect the Ali Tayebi rent dataset (github.com/alitayebi/maps/tree/master/rent)
  - document exact variable names, units, quarterly definitions, geographic identifiers (22 districts)
  - decide wage assumptions & affordability threshold (rent-burden %) and apartment-size assumption
  - output cleaned `data/tehran_rent_district.csv` (1388–1400)
- [ ] Encode annual series into `data/annual.csv` with `source_id` + units for every variable:
  - gasoline daily consumption (1382–1402)
  - Tehran house price / m² (1382–1400, treat Esfand 1402 81.44 as spot, NOT annual)
  - Tehran rent / m² (1390–1401)
  - minimum wage (1382–1402)
  - population / periphery built-up growth 2010–2020 (Tehran +4.8% vs Pardis +244.8%, etc.)
- [ ] Build `data/sources.csv` — every number/claim maps to a source_id, title, URL, date, definition, confidence tier
- [ ] Build `data/assumptions.json` — fuel efficiency 7/9/12 L/100km, 22 workdays, commute distance (50 km one-way default), gasoline-price scenarios. **No unexplained constants in JS.**
- [ ] Design the data-status layer: every figure tagged OBSERVED / CALCULATED / ESTIMATED (exposed via footnotes/tooltips)

## Phase 1 — Core build: Scenes 1–3 (desktop prototype)

> Per handoff §14: do not code the whole article at once. Ship these three first as one continuous argument.

- [ ] Set up article shell / component model: `ArticleShell → NarrativeSection → StickyVisual → Chart/Map/Calculator → SourceNote`; immutable global data store; scene-local interaction state
- [ ] **Scene 1 — Gasoline opening:** national chart 56 → 120 million L/day (1382–1402), flag 1399 COVID dip
- [ ] **Scene 2 — Tehran affordability map:**
  - SVG/GeoJSON of 22 municipal districts
  - time control 1388–1400; income selector (1×/2×/3× minimum wage)
  - color = affordable rent burden (not raw rent); callout contrasts "expensive city" vs "shrinking affordable geography"
- [ ] **Scene 3 — Parand commute + fuel calculator:**
  - show Parand representative route to Tehran; label distance as scenario/estimate (~35–50 km one-way, ~100 km/day round trip; 30–40k daily travelers = reported estimate)
  - calculator: one-way distance, workdays, fuel efficiency (7/9/12 presets), gasoline price, wage → km/month, L/month, fuel cost/month, fuel cost as % of wage
- [ ] Sticky-scroll narrative with causality-driven transitions (housing → outward displacement → commute → fuel)
- [ ] Wire every visual to `sources.csv` / `assumptions.json`; footnote OBSERVED vs CALCULATED vs ESTIMATED subtly

## Phase 2 — Extended scenes

- [ ] **Scene 3b — Periphery expansion:** map/animate peripheral built-up growth (Pardis, Pakdasht, Shahriar, Robat Karim, etc.) alongside affordability story
- [ ] **Scene 4 — Price-shock interaction:** gasoline-price slider/steps (baseline → 2×/3×), commute fixed; optional "work becomes unattractive" threshold clearly labeled illustrative
- [ ] **Scene 5 — 1398:** show why a fuel-price shock bites when housing & jobs are spatially separated (do NOT claim protest causation)
- [ ] **Scene 6 — Policy / public transport:** shift question to "reduce distance forced to travel"; transit as mechanism. Skip "26% of Tehran uses transit" until definition verified

## Phase 3 — Polish, verification & quality gates

- [ ] Enforce the "do NOT claim" rules from handoff (no causality claims; no DII-as-commuters; no minimum wage = average income; etc.)
- [ ] No hover-only interactions — every essential fact reachable by click/tap or visible text
- [ ] Respect `prefers-reduced-motion`
- [ ] Large editorial typography, dark/neutral palette, restrained accent color; clean legible maps
- [ ] Acceptance criteria pass:
  - thesis understandable without touching any control
  - housing scene shows *spatial* affordability, not just rising prices
  - Parand scene connects housing location → commute distance
  - calculator legible in seconds
  - every number has a source or is visibly calculated/estimated
- [ ] Verify all figures against sources; resolve any D-tier items before they appear

## Phase 4 — GitHub Pages deployment

- [ ] Initialize local Git repo + first commit
- [ ] Connect to the GitHub repository created in Phase 0; push `main`
- [ ] Configure GitHub Pages:
  - option A: deploy from `main` (static site, no build step) — works for single self-contained HTML
  - option B: GitHub Actions workflow building `dist/` and deploying to `gh-pages`
- [ ] Confirm relative asset paths work on Pages (no `/`-root assumptions if not using project site)
- [ ] Verify the live URL loads, all scenes render, interactions work on desktop
- [ ] (Post-launch) mobile-responsive adaptation — phase 2 per handoff

---

## Out of scope for v1 (per handoffs)
- Backend / server-side anything (page is fully static)
- National OD commuting matrix (raw data not publicly available yet — use Parand-style transparent scenario model instead)
- Mobile layout (after desktop acceptance)
