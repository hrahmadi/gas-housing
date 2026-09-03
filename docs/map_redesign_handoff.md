# Handoff — شکل ۲ (Tehran affordability map): redesign decisions & open questions

**Date:** 2026-09-03
**For:** fresh-eyes review (same reviewer who advised on Scene-2 framing)
**Author note:** orientation bug is already fixed & verified; the UX redesign below is **proposed, not yet implemented** — awaiting your advice before building.

---

## 1. Context

Figure 2 is the centerpiece of the housing section. It shows Tehran’s 22 municipal districts and, for a chosen year (1388–1400), which districts a household **can afford to rent** given: rent/m² per district, income = 2× statutory minimum wage, apartment size (m²), and a max rent-share of income.

The data layer is done and validated. An end-user review raised these problems:

1. **The map renders upside down** (projection sign bug — **FIXED**: geometry regenerated, verified north-up; district 1/shimiran at top, district 20/south at bottom).
2. Too many controls; confusing; controls sit **below** the map.
3. Default view shows the answer immediately — a first-time reader may not realize the piece is interactive at all.
4. Map too tall; the figure reads as a calculator, not an argument.
5. The caption at the bottom does too much (mixing headline, scenario, and disclaimer).

---

## 2. Agreed redesign (proposed implementation)

### 2.1 Controls
- Move controls **above the map**.
- **Remove the income-multiplier selector.** Household income is fixed at **2× statutory minimum wage** (clearly labelled as an assumption).
- Keep three controls: **سال (year)**, **متراژ خانه (m²)**, **سقف سهم اجاره (% of income)**.
- Fixed default scenario: year 1388, 35 m², 35% share.

### 2.2 Idle / activation state
- On first paint the map is **greyed out** with an overlay CTA:

  > «این نقشه تعاملی است — برای روشن شدن، یکی از کنترلهای بالا را تغییر بده یا اینجا را بزن.»

- First control change (or click on the overlay / a district) **activates** it; it then stays active. Colours only appear after activation.
- **Goal:** make interactivity obvious and let the user “light the map up” themselves.

### 2.3 Height & layout
- Reduce the rendered map height by ~20–25% (scale the SVG down, centred) so the narrative line below sits closer and the panel feels editorial, not like a dashboard.

### 2.4 Dynamic narrative (make it an argument)
Below the map a **dynamic line** explains *why the pattern matters*, driven by the current state:
- Default affordable set ⊆ south/south-east band:

  > «این مناطق عمدتا در جنوب و جنوب شرق تهران قرار دارند؛ فاصله آنها با بسیاری از مراکز اشتغال شهری بیشتر است.»

- When a scenario also makes **central/middle** districts affordable:

  > «با گسترش فرضها (سال، متراژ یا سهم اجاره)، گزینههایی در بخشهای مرکزی و میانی شهر هم اضافه میشوند — همانجا که تمرکز بیشتری از فعالیتهای شهری است.»

- When nothing is affordable:

  > «در این سناریو هیچ منطقهای داخل توان نیست؛ با سال، متراژ یا سهم اجاره بازی کن.»

### 2.5 Editorial hierarchy (separate data from model)
Top → bottom inside the figure:
1. **Heading (above viz):** «کجا میتوانم زندگی کنم؟» + small sub «با فرض درآمد خانوار = ۲ برابر حداقل دستمزد قانونی»
2. **Controls** (year / m² / rent-share)
3. **Map** with an **in-map badge**: «۴ از ۲۲ منطقه» (updates live)
4. **Dynamic narrative sentence** (2.4)
5. **Tiny footnote** (data vs model, one line):
   > «سبز = داخل توان اجاره · خاکستری = خارج از توان · راهراه = فاقد داده. محاسبه تقریبی بر اساس اجاره منطقهای، حداقل دستمزد و سهم فرضی از درآمد؛ داده مناطق تا تابستان ۱۴۰۰. این نقشه محل سکونت واقعی را پیشبینی نمیکند.»

Optional: click-a-district tooltip for details (kept small; never required to read the figure).

---

## 3. Open questions for you (please advise on any)

1. **Idle-grey vs. the “no interaction needed” acceptance criterion.** The original handoff required: *“A reader can understand the thesis without touching any control.”* An all-grey map until interaction arguably violates that — a passive reader sees nothing. Is the grey-then-activate pattern the right call, or should the map instead **start active** with the default scenario coloured and a small “کنترلها را تغییر بده” hint? (Middle option: start at 50% opacity, full colour + hint after first scroll into view.)
2. **Removing the income selector.** We lose the “income changes the geography of options” teaching moment. Is that acceptable for the narrative (Scene 2 just establishes spatial affordability), or should income be shown as a *static toggle in prose* (“if this household earned 3×, more central districts open up”) rather than a control?
3. **Is “2× minimum wage” the right fixed household income?** Minimum wage is a floor, not the median. 2× is arbitrary-ish; would 3× (closer to a two-earner min-wage household) be more representative/defensible for the article’s “کارمند/کارگر” framing? Or keep 2× and let the reader change year/size/share?
4. **Height reduction + layout.** Scaling the map down and centering it is simplest. Is that fine, or would you place the **dynamic narrative beside the map** on wide screens (map left, text right in RTL) and only stack on narrow?
5. **The dynamic sentence references “مراکز اشتغال شهری”** (job centres) **qualitatively.** We have no employment-density layer (per earlier advice we must NOT label specific districts as job centres). Is the phrasing above safe, or do you want it even weaker (e.g., «...فاصله بیشتری با هسته پرتراکم فعالیتهای شهری»)? And is the “south/south-east” band (districts 15–20) the right geographic claim, given we only detect the affordable-set is a subset of those districts?
6. **Badge wording «۴ از ۲۲ منطقه»** — fine as an in-map stat, or does it re-introduce a “calculator/KPI” feel you’d avoid? (Alternative: badge only shows on activation, which we already plan.)
7. **Activation UX:** is an overlay CTA over a greyed map the clearest, or would a simple visible “شروع کن/بازی کن” chip above the map be better for accessibility (keyboard focus) and reduced-motion users?

---

## 4. Where this lives (for orientation)

- Map render + model: `js/views.js` (`buildMap`, `syncMapControls`, `ratioFor`, `paintMap`, `updateMap*`)
- Figure markup: `index.html` (بخش ۱ · مسکن, «شکل ۲ · تعامل»)
- Map styles: `css/style.css` (`.map-wrap`, `#map-svg`, `.map-detail`, etc.)
- District geometry + data build: `scripts/build_data.py` → `data/data.js`, `assets/geo/tehran_districts.js`
- Earlier framing decisions & “what the article does NOT establish”: `docs/consultation_status.md`, `docs/gasoline_housing_scene2_revised_handoff.md`

**Bottom line question:** With the requirements “must be obvious it’s interactive,” “must still read without interaction,” and “must feel like an argument, not a calculator” — what is your recommended treatment for activation state, the fixed-income choice, and the dynamic narrative wording?
