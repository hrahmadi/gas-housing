# Handoff — شکل «مقیاس ملی» (national-scale commute/fuel thought experiment): plan, open questions & advice needed

**Date:** 2026-09-04
**For:** fresh-eyes review (same reviewer who wrote the Figure 4 brief and the national-scale handoff)
**Author note:** The **data layer is already prepared and committed** (assumptions + S15 + rebuilt `data.js`). The **figure itself is NOT built yet** — this doc is the pre-build advice pass so we settle structure/labels/numbering before touching `index.html`/`js/views.js`.

---

## 0. TL;DR — what I need a ruling on

1. **Numbering / chapter placement.** Where this figure physically sits (right before the Parand case study) collides with the existing «بخش سوم · نمونه پرند» chapter and «شکل ۴» figure labels. I need a decision on the *chapter* scheme (insert a new «بخش …» and shift the later ones? or a sub‑chapter?) and on the *figure* label (the user will do final numeration themselves, but I need a provisional scheme that reads cleanly on the live page now). Options are spelled out in §3.1–§3.2.
2. **Small arithmetic flag in the spec.** The handoff’s milestone table says **+۳۰ km / ۱۰٪ → «~۴.۹ میلیون لیتر در روز»**, but the formula as written (× ۲۶۴/۳۶۵) yields **~۴.۸۵ → rounds to ۴.۸ (or ۴.۹ if you round ۴.۸۴۷ up)**. Only that one row is affected; every other milestone matches. I need to know which rounding the reviewer intends so the default-state headline is right (§3.3).
3. **A few editorial/UX confirmations** that are cheaper to settle now than after a build: two-control-only rule, fixed-9L note, wording of the scenario vs. «مصرف اضافی واقعی», and the reduced-motion/animation trigger (which I can’t fully test locally — see §3.8).

---

## 1. Where this sits in the article (current state, unchanged numbering)

Narrative order on the page today:

| # | Section | Chapter kicker | Figure index |
|---|---|---|---|
| 1 | مقدمه | *(none)* | شکل ۱ · تعامل (gas chart) |
| 2 | مسکن | بخش اول · مسکن | شکل ۲ · تعامل (map) + rent-wage panel (README: شکل ۲-ب) |
| 3 | جغرافیا / پیرامون | بخش دوم · جغرافیا | شکل ۳ · تعامل (peri-map) |
| 4 | **نمونه پرند (Parand)** | **بخش سوم · نمونه پرند** | **شکل ۴ · تعامل** |
| 5 | انرژی (money calc) | بخش چهارم · انرژی | شکل ۵ · تعامل |
| 6 | سیاست قیمت | بخش پنجم · سیاست قیمت | *(none)* |
| 7 | شوک قیمت | بخش ششم · شوک قیمت | شکل ۶ · تعامل |
| 8 | آبان ۱۳۹۸ | بخش هفتم · ۱۳۹۸ | *(none)* |
| 9 | نتیجه | بخش هشتم · نتیجه | *(none)* |
| 10 | جمعبندی | جمعبندی | *(none)* |

The new figure is a **national-scale thought experiment** and belongs **between the periphery discussion (جغرافیا, §3) and the detailed Parand case study (§4)** — it is the bridge: «خانههای پیرامونی → رفتوآمد طولانیتر → × میلیونها شاغل → میلیونها لیتر سوخت → سپس نمونه پرند». The current §3 ends with the pull «و این فاصله باید هر روز طی شود.» — the natural seam.

**Anchor to keep intact:** Section 5 (energy) carries `id="fig5"` and Parand’s «#parand-next» link scrolls to `href="#fig5"`. Whatever we do, that anchor must keep working.

---

## 2. What is already done (data layer — committed)

- `data/assumptions.json` → new `nationalCommute` block:
  ```json
  "employedMillion": 24.822,          // S15
  "fuelLitresPer100km": 9,
  "workdaysPerMonth": 22,
  "daysPerYear": 365,
  "baseline": { "nationalDailyMillionLitres": 129, "status": "OBSERVED" },  // S11
  "status": "SCENARIO"
  ```
- `data/sources.csv` → **S15** appended (employed population ≈ 24.822 M, 1404, project-supplied — flagged «verify before publication»).
- `data/data.js` regenerated; `window.ARTICLE_DATA.assumptions.nationalCommute` present; gas 1404 = 129.0; S15 present. Verified with Python.
- Baseline `129 M L/day` already flagged (S11) from earlier rounds.

**Not yet built:** HTML section, `drawNational()` renderer, CSS, boot wiring, README entry, cache-bump, push.

---

## 3. The figure the handoff asks for (recap) + open questions

### 3.1 Chapter numbering — which scheme? (MAIN OPEN QUESTION)

The handoff says «insert after the housing/periphery discussion and before the detailed Parand case study», and a clarifying answer chose a **new labeled chapter** between جغرافیا and نمونه پرند. Two ways to do that:

- **Option A — shift everything after the seam by one:**
  New chapter becomes «بخش سوم · مقیاس ملی»; Parand → «بخش چهارم · نمونه پرند»; انرژی → «بخش پنجم»; سیاست قیمت → «بخش ششم»; شوک → «بخش هفتم»; ۱۳۹۸ → «بخش هشتم»; نتیجه → «بخش نهم». Pro: the chapter sequence stays monotonic. Con: touches many kickers (a reviewer usually dislikes churn in sections that were already reviewed).
- **Option B — keep later chapters untouched, insert a distinct sub-chapter:**
  e.g. keep «بخش دوم · جغرافیا» and «بخش سوم · نمونه پرند» as-is, and give the new section a label that does not collide (e.g. «بخش ۲-ب · مقیاس ملی» as a sub-chapter of جغرافیا, mirroring the rent-wage «شکل ۲-ب» precedent in README). Con: «بخش ۲-ب» may read as secondary despite being a big standalone figure.

Since the user said *«I’ll handle numeration later»*, either is acceptable as a provisional — but I want the reviewer’s read on which **final** structure is cleaner so I don’t build a label I’ll immediately tear out.

### 3.2 Figure label — same collision, plus rent-wage precedent

The new figure physically precedes Parand, but Parand is already «شکل ۴» and the user said **do not renumber شکل ۴/۵/۶**. So the new figure can’t be «شکل ۴». Project precedent already uses a letter-suffix for a companion figure (rent-wage = «شکل ۲-ب» in README, rendered as a second panel inside the شکل ۲ scene).

Options for the provisional figure index:
- **A.** «شکل ۳-ب · تعامل» (companion to the periphery figure it follows — consistent with the rent-wage convention).
- **B.** Give the new figure its own full chapter AND number (e.g. it becomes «شکل ۴», Parand «شکل ۵»…) — but this is exactly the renumbering the user said to avoid.
- **C.** No figure index; render it as an unnumbered «آزمایش ذهنی» interstitial between chapters.

I lean **A** as the least-churn provisional (user will do the final pass). Reviewer’s preference?

### 3.3 Arithmetic check on the default headline (small but important)

Formula in handoff/assumptions:
**litres/day (annual-average) = affected workers × additional round-trip km × 0.09 × (۲۲×۱۲)/۳۶۵**

At the settled default **+۳۰ km / ۱۰٪**:

```
workers affected = 24.822 M × 0.10 = 2.4822 M
× 30 km × 0.09 L/km = 6.70194 M L  (if every day were a workday)
× (264/365 = 0.7232876) = 4.8472 M L/day
share of 129 M = 3.757 % ≈ 3.8%
```

The handoff’s milestone table says **+۳۰ → «~۴.۹ M»**; my computation is **۴.۸۵ → ۴.۸ (or ۴.۹ if rounded up)**. All other rows match the handoff (±0.1): +۱۰→۱.۶, +۲۰→۳.۲, +۴۰→۶.۵, +۵۰→۸.۱, +۶۰→۹.۷. So only the flagship default number is ambiguous. **Please confirm:** display «حدود ۴.۸» or «حدود ۴.۹» million L/day (and ۳.۸٪)? (I’ll hard-code display rounding only if needed; otherwise it’s computed live from the assumptions.)

### 3.4 Two controls only + fixed assumptions row

Per handoff §UX: exactly **two controls** (additional round-trip km; % of workers). Do **not** add a third (fuel-efficiency) slider. Fixed row under the controls: «۲۴.۸ میلیون شاغل · مصرف خودرو ۹ لیتر در ۱۰۰ کیلومتر · ۲۲ روز کاری در ماه» with a small expandable note that 9 L/100km is an assumption and Figure 5/6 already explore 7–12 L. No open question — just confirming I will not expose a third slider.

### 3.5 Wording rules I will enforce (please sanity-check the exact strings)

- **Never** «مصرف اضافی واقعی کشور»; use «مصرف اضافی در این سناریو» / «بنزین مورد نیاز برای این فاصله اضافی».
- Distance control label must say **«مسافت رفت و برگشت روزانه»**, not «فاصله تا محل کار».
- Small qualifier under subtitle: «این یک سناریوی محاسباتی است، نه آمار واقعی رفت و آمد شاغلان.»
- Fixed disclaimer near the big number: «این عدد مصرف واقعی رفت و آمد شغلی نیست؛ یک محاسبه سناریویی برای نشان دادن مقیاس مسئله است.»
- Figure title: «فاصله تا محل کار چقدر بنزین مصرف میکند؟» — subtitle: «یک آزمایش ذهنی با ۲۴.۸ میلیون شاغل ایران».

Any wording objections before I bake them in?

### 3.6 The ۲۴.۸ میلیون «crowd» visual — abstraction level

24.8 M workers can’t be drawn literally. The handoff asks for a large visual of «۲۴.۸ میلیون شاغل» + a repeated-worker crowd where the selected % lights up, + a distance arrow «+۰ km → +۶۰ km» + count-up to the litres number + a comparison bar vs ۱۲۹ M. Concrete questions:
- Is a **stylised crowd** (e.g. a grid/block of worker glyphs where `pct%` light up amber, the rest dim) acceptable, with the exact affected-worker count shown as text («۱۰٪ ≈ ۲.۵ میلیون نفر»)? Or does the reviewer want an explicit-but-simplified scale bar instead of a crowd?
- Show affected workers as a *separate* secondary number (e.g. ۱۰٪ = ۲.۵M, ۶۰٪ = ۱۴.۹M) — the handoff lists those values. Confirm we should show both the litres number (primary) and the worker count (secondary).

### 3.7 Comparison bar vs ۱۲۹ M — visual honesty at ~3.8%

At default the scenario is ~3.8% of the 129 M baseline — a thin sliver. I plan a full-width reference bar labelled «مصرف روزانه کشور ≈ ۱۲۹ میلیون لیتر» with the scenario share drawn as a proportionally *tiny* highlighted segment plus a «۳.۸٪» callout (not a deceptive second axis). Confirm this is the desired treatment.

### 3.8 Animation & the local-test limitation (same caveat as Figure 4)

Handoff wants a ~2–3 s entrance on first viewport entry: ۲۴.۸M shown → % lights up → commute arrow → multiply across workers → count-up → % bar draws; `prefers-reduced-motion` shows the final state immediately. As with Figure 4, **the local browser preview cannot scroll the page viewport**, so the IntersectionObserver/scroll-triggered entrance can’t be fully verified locally — it must be checked on the live GitHub Pages build. I’ll include the same triggers used for Figure 4 (IntersectionObserver + scroll listener + fallback). Just confirming that’s an accepted, known limitation for this round too.

### 3.9 Transition prose (before/after) — where it goes

Per handoff:
- **Before** the figure (seam into §3’s «هر روز طی شود» pull): «ما نمیدانیم دقیقا چه مقدار از مصرف بنزین کشور مربوط به رفت و آمد شغلی است… ایران حدود ۲۴.۸ میلیون نفر شاغل دارد…»
- **After** the figure: «حتی اگر فقط بخشی از شاغلان… فقط نشان میدهد که اندازه مسئله بالقوه چقدر است.»
- Then the handoff’s transition into Parand: «این محاسبه فقط یک آزمایش ذهنی بود… برای دیدن شکل واقعیتر این مسئله، یک مورد مشخص را بررسی کنیم.» → «پرند».

Question: should the «→ پرند» handoff live at the **end of the new section** (as a closing pull / link) or as the **opening line of the Parand section** (replacing its current first sentence «اما رشد شهرهای پیرامونی فقط به این معنی نیست…»)? Current Parand opening would need a light edit either way so we don’t repeat the transition twice.

### 3.10 Verification flags (carried from data layer)

S15 (24.822 M employed, 1404) and S11 (129 M baseline) are both **project-supplied** and marked «verify before publication». The figure is explicitly SCENARIO, so this is acceptable for now — but I’ll surface both IDs in the fig-cap/note so the reviewer can chase them. Confirm that’s sufficient (vs. blocking the build).

---

## 4. Files I plan to touch (after advice)

- `index.html` — new labeled chapter between §3 (جغرافیا) and §4 (نمونه پرند): prose → fig-scene (title/subtitle/qualifier, crowd, distance control, share control, fixed assumptions row, big litres output, comparison bar, dynamic sentence, disclaimer) → fig-cap → after-prose + «→ پرند» transition. Keep `id="fig5"` anchor working.
- `js/views.js` — new `drawNational()` (and small helpers), exported on `G.views`.
- `js/article.js` — call `V.drawNational()` in boot.
- `css/style.css` — styles for the crowd visual, controls row, output, comparison bar (reuse `.panel`, `.chips`, `.ctrl-*`, `.fig-cap`, `.map-note` conventions).
- `README.md` — add the figure to the «وضعیت شکلها» list (status SCENARIO).
- Cache-buster `v21 → v22`; commit & push to `main`.

---

## 5. Open items the reviewer should answer (copy-paste block)

1. Chapter scheme: **A** (shift sections after the seam: new = بخش سوم …) or **B** (sub-chapter, e.g. بخش ۲-ب, leave others untouched)? Or is chapter numbering also deferred to the user’s final numeration pass?
2. Provisional figure label: **A** «شکل ۳-ب · تعامل», **B** full renumber, or **C** no index / interstitial?
3. Default headline rounding: «حدود ۴.۸» or «حدود ۴.۹» میلیون لیتر در روز (at +۳۰/۱۰٪, formula gives ۴.۸۵)?
4. Crowd visual: stylised worker-crowd with % lighting up + affected-worker count text — OK? Show worker count as a secondary number?
5. Comparison bar: proportionally-tiny sliver + «۳.۸٪» callout vs 129 M — OK?
6. «→ پرند» transition: close of new section vs. reworked opening of Parand section?
7. Wording strings in §3.5 — objections?
8. Known local limitation on the entrance animation (§3.8) — accepted for this round?
9. S15/S11 verification flags in fig-cap — sufficient, or block the build?

---

## 6. Where things live (orientation)

- Figure 4 (Parand) scene + its advice doc: `index.html` §4, `js/views.js` (`drawParandRoute`/scene helpers), `docs/fig4_commute_redesign_advice.md`.
- Figure 2 map consultation: `docs/map_redesign_handoff.md`.
- Scene framing / claims limits: `docs/consultation_status.md`, `docs/gasoline_housing_scene2_revised_handoff.md`.
- National-scenario data (already committed): `data/assumptions.json` (`nationalCommute`), `data/sources.csv` (S15), `data/data.js`.

**Bottom line:** the data is ready and the build is small and well-contained. The genuinely open items are (a) numbering/chapter scheme, (b) the one rounding discrepancy in the flagship default number, and (c) a handful of editorial confirmations. Answer §5 and I’ll implement, bump `v21 → v22`, and push.

---

## 7. Reviewer rulings — APPLIED (2026-09-04)

| # | Ruling | Applied |
|---|---|---|
| 1 | Chapter scheme **A**: new section = «بخش سوم · مقیاس ملی», later chapters shifted by one (پرند → بخش چهارم … نتیجه → بخش نهم) | Yes |
| 2 | Figure label **C**: no figure number — «آزمایش ذهنی · مقیاس ملی» as fig-index (not «شکل N») | Yes |
| 3 | Default headline: display «حدود ۴.۸ میلیون لیتر در روز» (full precision 4.8472 kept internally) + ۳.۸٪ | Yes |
| 4 | Crowd visual: abstract repeated-worker grid, affected share illuminates; worker count secondary («۱۰٪ = حدود ۲.۵ میلیون شاغل») | Yes |
| 5 | Comparison bar: proportional tiny segment vs ۱۲۹ M, no inflation | Yes |
| 6 | «→ پرند» transition lives at end of the national-scale section; Parand section starts directly with the Parand story (old periphery recap sentence removed) | Yes |
| 7 | Wording approved (title/subtitle/qualifier/distance control/disclaimer) | Yes |
| 8 | Animation: IO + scroll + fallback; reduced-motion skips to final; local scroll-trigger still unverifiable → check on live GH Pages | Yes |
| 9 | S15/S11: surface in fig-cap, do not block build; upgrade to “confirmed” before publication | Yes (flagged in fig-cap) |
| + | Distance control = **additional** round-trip km («مسافت اضافه رفتوبرگشت روزانه», ۰→۶۰, default +۳۰) | Yes |

**Build status:** implemented (`index.html`, `js/views.js` `drawNational()`, `js/article.js` boot, `css/style.css`), README updated, cache-buster `v21 → v22`, committed & pushed.

---

## 8. Second-round redesign — layout feedback APPLIED (2026-09-04)

Reviewer feedback on the first build (see chat): the figure had **three competing quantities** and felt like a calculator. Redesign rulings:

| # | Feedback | Applied |
|---|---|---|
| 1 | Make the causal chain **visually explicit and vertical**: ۲۴.۸M → ۱۰٪ → ۲.۵M نفر → +۳۰ km/روز → +۴.۸M لیتر/روز | Yes — panel is now a vertical chain of `nat-seq` blocks |
| 2 | **One distance control, one number, one meaning** — no detached value pill, no extra tiny ruler | Yes — slider with end labels (۰/۶۰ km) + single big readout «+۳۰ کیلومتر در روز» + sub-sentence; old `nat-rule` removed |
| 3 | **Worker percentage second** as its own step, stacked (not beside distance) | Yes — chips in own step, answer «حدود ۲.۵ میلیون نفر» below |
| 4 | **Shrink the crowd ~20–30%**; it is the denominator, not the focus; semantic label for affected group | Yes — `.nat-ctx` smaller; worker count shown as the step-1 answer |
| 5 | **Result card:** explicit label «بنزین مورد نیاز برای این فاصله اضافی» + big number + % underneath; **no orange giant card** | Yes — plain number is the focal point, card removed |
| 6 | Share-control wording → «چند درصد شاغلان این فاصله اضافه را تجربه کنند؟» | Yes |
| 7 | Editorial scenario sentence above the result («فرض کنیم فقط ۱۰٪ شاغلان …») | Yes (`nat-scenario`) |
| 8 | Comparison bar: numbers together («۴.۸ میلیون لیتر از ۱۲۹ میلیون لیتر مصرف روزانه کشور») with bar below and **۳.۸٪ on the highlighted segment** | Yes |
| 9 | Animation: reveal the exact causal chain (denominator → % lights up → distance → multiply → result count-up → bar), not abstract events | Yes — staged `natRender(e)` reveals each block in order |
| 10 | Typography: consistent «میلیون»/«لیتر در روز» (no ملیون / mixed glyphs) | Yes |
| + | Percent chips now **۵٪ → ۵۰٪** (default ۱۰٪); ۶۰٪ dropped per reviewer choice | Yes — `NAT_PCTS = [5,10,20,30,40,50]` |
| + | Post-figure prose merged into the panel as the closing narrative (no duplication) | Yes |

**Second-round status:** redesigned & verified locally via DOM/interaction checks (no console errors); cache-buster `v22 → v23`. Entrance animation still only fully verifiable on live GitHub Pages (local preview cannot scroll).
