# Handoff — شکل ۴ (Parand commute scene): redesign implemented, issues & open questions

**Date:** 2026-09-04 (updated after second review round)
**For:** fresh-eyes review (same reviewer who wrote the Figure 4 brief)
**Author note:** The reviewer’s second-round decisions were all applied (see §0) and pushed (`main`, cache-buster v20). Remaining open items: §3.1, §3.6, §3.9 (smaller).

---

## 0. Second-review decisions — APPLIED (2026-09-04)

| # | Decision | Applied |
|---|---|---|
| 1 | Keep **۲۲ days** as the settled default | Yes |
| 2 | **First-view animation steps ۱→۵→۱۰→۱۵→۲۲**, then settles on ۲۲ | Yes — auto-steps on first viewport entry after the commute cycle; manual click cancels the demo |
| 3 | **Heart line always visible** («این مسیر یک بار نیست…»), animation only illustrates it | Yes — no longer gated behind animation completion |
| 4 | **Auto-play on scroll: yes**, short & quiet (~1.2 s per leg); reduced-motion skips to final state | Yes |
| 5 | **Fuel output always visible & recalculated** (not gated to ۲۲); ۲۲-day result visually emphasised | Yes — ۱→۹L, ۵→۴۵L, ۱۰→۹۰L, ۱۵→۱۳۵L, ۲۲→۱۹۸L; `.peak` highlight at ۲۲ |
| 6 | Keep «تا حدود ۱۰۰ کیلومتر رفت و برگشت در روز» for reported distance; label the calc as **scenario**: «… × سناریوی ۱۰۰ کیلومتر رفتوبرگشت در روز» | Yes — fig-cap + output sub-line updated to separate reported range from scenario |
| 7 | Subtitle → «خانه ارزانتر است؛ اما برای رسیدن به محل کار باید هر روز این فاصله را طی کرد.»; «برای بعضی از ساکنان پرند…» moved to prose before the figure | Yes |
| 8 | Remove the trip-purpose evidence block from under Figure 4 (and S14 from `sources.csv`) unless the source is strong | Yes — block + S14 removed |
| 9 | Figure 4 ends at 2,200 km → 198 L; Figure 5 opens from 198 L and owns the **money** calc | Yes — Figure 5 prose now starts «…حالا ببینیم این ۱۹۸ لیتر برای یک کارگر یا کارمند چقدر هزینه دارد.» |
| 10 | Day-control label → «حالا این مسیر را چند روز در ماه تکرار کنیم؟» | Yes |

---

## 1. What changed (summary of the implementation)

Replaced the old "مسیر پرند تا تهران؛ از یکطرفه تا مسافت ماهانه" stepper (three numbered chips: one-way → daily → monthly) with an **accumulation scene**:

### 1.1 New markup (top → bottom inside the panel)
1. **Title:** «یک خانه در پرند، یک کار در تهران»
2. **Subtitle:** «خانه ارزانتر است؛ اما برای رسیدن به محل کار باید هر روز این فاصله را طی کرد.»
3. **Route visual (`#parand-route`):** SVG with 🏠 پرند (خانه) on one side, 💼 تهران (محل کار) on the other, a road between, and a small commuter dot.
4. **Cycle caption (`#parand-cycle`):** an auto-playing one-workday cycle — صبح (پرند→تهران) → در محل کار → عصر (تهران→پرند) → ends at «رفت و برگشت روزانه: تا حدود ۱۰۰ کیلومتر».
5. **Heart line (`#parand-heart`):** «این مسیر یک بار نیست؛ هر روز تکرار میشود.» (revealed after the cycle completes).
6. **One control (`#parand-days-chips`):** «چند روز در ماه سر کار میرود؟» — chips ۱ / ۵ / ۱۰ / ۱۵ / ۲۲ (default **۲۲**).
7. **Accumulation output (`#parand-out`):** at ۱ → «تا ۱۰۰ کیلومتر در روز · رفت و برگشت»; at ۲۲ → «۲٬۲۰۰ کیلومتر در ماه» with the factor note «۲۲ روز کاری × تا حدود ۱۰۰ کیلومتر در روز».
8. **Fuel reveal (`#parand-fuel`):** appears only when ۲۲ workdays are selected → «با مصرف فرضی ۹ لیتر در هر ۱۰۰ کیلومتر: **۱۹۸ لیتر بنزین در ماه**» (animated in), plus a small calc note.
9. **Continue link (`#parand-next`):** «هزینهاش چقدر میشود؟ ↓» → smooth-scrolls to Figure 5 (`#fig5`). Shown only at ۲۲ days.

### 1.2 Distance is on the route, not a bracket
- The blue engineering bracket was removed. The pill sits **on the road**: initially «۳۵–۵۰ km», and after the one-day cycle it reads «~۱۰۰ km» (round trip). The uncertainty is preserved as «تا حدود ۱۰۰ کیلومتر» in the caption, not a hard «۱۰۰ کیلومتر در روز».

### 1.3 Work-trips stat — REMOVED after second review
The trip-purpose evidence block (etemadonline) was originally added under the figure, then **removed** in the second round per the reviewer’s decision (§0, #8), because this figure’s example is explicitly a work commute and the block interrupted the rhythm. S14 was also removed from `data/sources.csv`. *(If the source is later verified as strong, it can return — but not directly under Figure 4.)*

### 1.4 Transitions tied to neighbours
- Sentence immediately before the figure (now the lead of the Parand section): «اما رشد شهرهای پیرامونی فقط به این معنی نیست که خانهها از تهران دورتر شدهاند. اگر شغل همانجا بماند، این فاصله باید هر روز طی شود.»
- Sentence immediately after: «و این تکرار روزانه همانجاست که فاصله جغرافیایی به مصرف انرژی تبدیل میشود.» → leads into Figure 5.

### 1.5 Files touched
- `index.html` — Section 4 markup + transitions + `id="fig5"` anchor; Figure 5 opening reworded to start from the 198 L established in Figure 4.
- `js/views.js` — replaced `drawParandRoute`/`renderParandStats` with the commute scene, cycle, auto-step, and continuous accumulation renderers (`buildParandScene`, `runParandCycle`, `p4AutoStep`, `p4SetDays`, `p4moveTo`, `renderParandOutput`).
- `css/style.css` — styles for the scene, chips row, output card, fuel (always visible, `.peak` emphasis at ۲۲), heart (always visible), evidence block (removed styles).
- `data/sources.csv` — S14 removed.

---

## 2. Verification done

- **Zero console errors** (checked in Chromium).
- Route SVG builds; chips render; heart is visible by default (opacity 1).
- Fuel output is **continuous**: ۱→۹L, ۵→۴۵L, ۱۰→۹۰L, ۱۵→۱۳۵L, ۲۲→۱۹۸L, with the ۲۲ result `.peak`-highlighted; continue link always present.
- Default state (۲۲ days) shows 2,200 km/month → 198 L immediately.
- Cache-buster bumped `v19 → v20`; committed & pushed to `hrahmadi/gas-housing`.

**What I could NOT fully verify in this environment:** the first-view **auto-step ۱→…→۲۲** and the one-workday dot animation. The local browser preview cannot scroll the page viewport (window/`body` scroll stays `0`), so the scroll/IntersectionObserver trigger never fires there. Code triggers: IntersectionObserver + scroll listener + 900 ms fallback; reduced-motion skips straight to the final state. Please confirm on the live GitHub Pages build that the dot travels صبح→کار→عصر and the chips step ۱→۵→۱۰→۱۵→۲۲ when scrolled into view.


---

## 3. Issues / things I am unsure about (please advise)

*The second-review decisions in §0 resolved most earlier questions. Items 1–5 and 7–8 below are closed per §0; only 6 and 9 remain genuinely open.*

1. ~~No-interaction default~~ → **Resolved:** keep ۲۲; first-view auto-step ۱→۵→۱۰→۱۵→۲۲ then settle on ۲۲.
2. ~~Heart line gated~~ → **Resolved:** always visible; the animation only illustrates it.
3. ~~Reduced-motion~~ → **Resolved:** skip animation, leave all conclusions on screen (accepted).
4. ~~Auto-play vs. click~~ → **Resolved:** auto-play on viewport entry (short, quiet ~1.2 s/leg); route click replays.
5. ~~Fuel gated to ۲۲~~ → **Resolved:** fuel always visible & recomputed per day; ۲۲ emphasised (`~198 L`).
6. **Wording of the uncertainty (still open).** The reported range is 35–50 km one-way, so I hedge the round trip as «تا حدود ۱۰۰ کیلومتر» and label the monthly math as a scenario: «… × سناریوی ۱۰۰ کیلومتر رفتوبرگشت در روز». The fig-cap states the reported distance vs. scenario explicitly. Is this the right split between "reported range" and "illustrative calculation"?
7. ~~Work-trips evidence block~~ → **Resolved:** removed from under Figure 4 (and S14 dropped) per decision #8. If you later want this claim, we should verify the source wording first and place it elsewhere (e.g., a commuting-in-Iran discussion), not under Figure 4.
8. ~~Figure 4/5 overlap~~ → **Resolved:** Figure 4 ends at 2,200 km → ~198 L; Figure 5 now opens from 198 L and owns the money calculation.
9. **Keyboard/AT (still open).** Day chips are real `<button>`s (keyboard-accessible), but the route’s click-to-replay is an SVG with no focus handling. Should the replay affordance be a real `<button>` (e.g., «▶ یک روز کاری را ببین» under the route) so keyboard/tab users can replay the commute?

---

## 4. Where this lives (for orientation)

- Figure scene markup & surrounding prose: `index.html` (بخش ۳ · نمونه پرند).
- Scene/cycle/chips/output JS: `js/views.js` — `drawParandRoute`, `buildParandScene`, `runParandCycle`, `p4AutoStep`, `p4SetDays`, `p4moveTo`, `renderParandOutput`.
- Styles: `css/style.css` (`.parand-*`, `.po-card`, `.parand-fuel`, `.parand-heart`).
- Previous figure-2 map consultation: `docs/map_redesign_handoff.md`; scene-2 framing & “what the article does NOT establish”: `docs/consultation_status.md`, `docs/gasoline_housing_scene2_revised_handoff.md`.

**Bottom line:** With the second-round decisions applied, the figure should read as one argument — خانه در پرند → کار در تهران → هر روز → ×۲۲ → ۲٬۲۰۰ km → ~۱۹۸ L — with the fuel line always live and the heart line always present. Remaining open items for your advice: §3.6 (reported range vs. scenario wording) and §3.9 (keyboard replay button).
