# Handoff — شکل ۴ (Parand commute scene): redesign implemented, issues & open questions

**Date:** 2026-09-04
**For:** fresh-eyes review (same reviewer who wrote the Figure 4 brief)
**Author note:** I implemented the redesign below from your brief. It is committed/pushed (`main`, cache-buster v19). Before/after advice is welcome on the open questions in §4, especially the **no-interaction default** and the **animation trigger**.

---

## 1. What changed (summary of the implementation)

Replaced the old "مسیر پرند تا تهران؛ از یکطرفه تا مسافت ماهانه" stepper (three numbered chips: one-way → daily → monthly) with an **accumulation scene**:

### 1.1 New markup (top → bottom inside the panel)
1. **Title:** «یک خانه در پرند، یک کار در تهران»
2. **Subtitle:** «برای بعضی از ساکنان پرند، رفت و آمد به تهران بخشی از هزینه زندگی است.»
3. **Route visual (`#parand-route`):** SVG with 🏠 پرند (خانه) on one side, 💼 تهران (محل کار) on the other, a road between, and a small commuter dot.
4. **Cycle caption (`#parand-cycle`):** an auto-playing one-workday cycle — صبح (پرند→تهران) → در محل کار → عصر (تهران→پرند) → ends at «رفت و برگشت روزانه: تا حدود ۱۰۰ کیلومتر».
5. **Heart line (`#parand-heart`):** «این مسیر یک بار نیست؛ هر روز تکرار میشود.» (revealed after the cycle completes).
6. **One control (`#parand-days-chips`):** «چند روز در ماه سر کار میرود؟» — chips ۱ / ۵ / ۱۰ / ۱۵ / ۲۲ (default **۲۲**).
7. **Accumulation output (`#parand-out`):** at ۱ → «تا ۱۰۰ کیلومتر در روز · رفت و برگشت»; at ۲۲ → «۲٬۲۰۰ کیلومتر در ماه» with the factor note «۲۲ روز کاری × تا حدود ۱۰۰ کیلومتر در روز».
8. **Fuel reveal (`#parand-fuel`):** appears only when ۲۲ workdays are selected → «با مصرف فرضی ۹ لیتر در هر ۱۰۰ کیلومتر: **۱۹۸ لیتر بنزین در ماه**» (animated in), plus a small calc note.
9. **Continue link (`#parand-next`):** «هزینهاش چقدر میشود؟ ↓» → smooth-scrolls to Figure 5 (`#fig5`). Shown only at ۲۲ days.

### 1.2 Distance is on the route, not a bracket
- The blue engineering bracket was removed. The pill sits **on the road**: initially «۳۵–۵۰ km», and after the one-day cycle it reads «~۱۰۰ km» (round trip). The uncertainty is preserved as «تا حدود ۱۰۰ کیلومتر» in the caption, not a hard «۱۰۰ کیلومتر در روز».

### 1.3 Work-trips stat included prominently
Below the figure, in the section prose, an evidence block was added:

> «بیشترین سفرهای روزانه، سفرهای شغلیاند … بیشترین سفرها مربوط به سفرهای شغلی است و بعد از آن سفرهای تحصیلی.»

with a link to the etemadonline source (شهرداری تهران traffic report). Registered as **S14** in `data/sources.csv`.

### 1.4 Transitions tied to neighbours
- Sentence immediately before the figure (now the lead of the Parand section): «اما رشد شهرهای پیرامونی فقط به این معنی نیست که خانهها از تهران دورتر شدهاند. اگر شغل همانجا بماند، این فاصله باید هر روز طی شود.»
- Sentence immediately after: «این جاست که فاصله جغرافیایی به مصرف انرژی تبدیل میشود.» → leads into Figure 5.

### 1.5 Files touched
- `index.html` — Section 4 markup + transitions + work-trips block + `id="fig5"` anchor.
- `js/views.js` — replaced `drawParandRoute`/`renderParandStats` with the commute scene, cycle, and accumulation renderers (`buildParandScene`, `runParandCycle`, `p4moveTo`, `renderParandOutput`).
- `css/style.css` — new styles for the scene, chips row, output card, fuel reveal, heart, evidence block.
- `data/sources.csv` — S14 (etemadonline trip-purpose claim).

---

## 2. Verification done

- **Zero console errors** (checked in Chromium).
- Route SVG builds; chips render; day chips update the output & fuel card; fuel + continue link only show at ۲۲ days; the ۱-day state shows the daily round-trip card; the evidence block and transitions are in the DOM.
- Cache-buster bumped `v18 → v19`; committed & pushed to `hrahmadi/gas-housing`.

**What I could NOT fully verify in this environment:** the one-workday **auto-play animation** and the heart-line reveal. The local browser preview used for testing cannot scroll the page viewport (window/`body` scroll stays `0`), so the scroll/IntersectionObserver trigger never fires there. The code has two triggers (IntersectionObserver **and** a scroll listener **and** a 900 ms fallback) and honours `prefers-reduced-motion` by skipping straight to the final state — but please confirm on the live GitHub Pages build that the dot actually travels صبح→کار→عصر when scrolled into view.

---

## 3. Issues / things I am unsure about (please advise)

1. **No-interaction default = ۲۲ days, not ۱.** Your brief’s discovery arc starts at ۱ day (100 km) and lets the reader push up to ۲۲ (2,200 km). I defaulted to **۲۲** so a passive reader immediately sees the strong claim (2,200 km/month → 198 L) without touching anything — consistent with the project’s earlier “must read without interaction” rule. Trade-off: the reader **reduces** from ۲۲ rather than *accumulating up* from ۱. Which default do you prefer — ۲۲ (punchline first) or ۵/۱۰ (discovery first, but weaker if unclicked)? Or should the chips auto-step once on first view?

2. **Heart line hidden until the animation completes.** «این مسیر یک بار نیست؛ هر روز تکرار میشود.» only fades in after the one-day cycle ends. If for any reason the animation never runs (e.g., reduced-motion path, or a reader jumps straight to the figure via the in-page link without scrolling through), the heart line stays hidden. Should it be **always visible** (static) and the animation only *illustrates* it, instead of gating the reveal behind the animation?

3. **Reduced-motion handling.** Under `prefers-reduced-motion`, the cycle currently fast-forwards to the end state (caption = round-trip, pill = ~100 km, heart shown). Confirm that’s acceptable — i.e., no motion, but all conclusions still on screen.

4. **Auto-play on scroll vs. click-to-replay.** Currently the cycle plays automatically when the scene scrolls into view, and clicking the route replays it. Is auto-play-on-scroll the right choice, or should it start paused with an explicit «▶ یک روز کاری را ببین» control? (Accessibility / surprise-factor question.)

5. **Fuel reveal is gated to exactly ۲۲ days.** Below ۲۲, `#parand-fuel` is empty and the continue link hides. That makes ۲۲ a “reward,” but a reader exploring ۵/۱۰/۱۵ sees an empty gap under the output. Would you prefer the fuel line to always show (recomputed per day count) with the ۱۹۸ L emphasized at ۲۲, or keep the gated reveal?

6. **Wording of the uncertainty.** I used «تا حدود ۱۰۰ کیلومتر» / pill «~۱۰۰ km» after doubling, not a hard 100. The ۱-day card reads «تا ۱۰۰ کیلومتر در روز · رفت و برگشت». Is «تا حدود» hedged enough for the 35–50 km one-way source? (We do **not** want to overstate a universal Parand commute.)

7. **etemadonline work-trips claim.** It is currently placed as a prose evidence block under the figure, phrased as «بیشترین سفرهای روزانه، سفرهای شغلیاند». I have **not** verified the original survey’s exact wording/definition inside the linked article (registered S14 with a “verify” note). Please confirm: (a) the claim is about **daily trips** and (b) the phrasing matches the source — and whether you’d prefer it inside the figure scene rather than the prose.

8. **Figure 4 ↔ Figure 5 overlap.** Figure 4 now ends by computing 198 L (at 22 days, 9 L/100 km) and hands off to Figure 5, whose first paragraph **also** computes 198 L. That is intentional (Fig 4 = distance→fuel, Fig 5 = fuel→cost), but the repetition may read as redundant. Keep both, or trim Figure 5’s opening so it starts from “we already have the 198 L — now what does it cost?”

9. **Keyboard/AT.** The route is clickable to replay but is an SVG without focus handling; the day chips are real buttons. If click-to-replay matters for accessibility, should the replay control be a real `<button>`? (Currently the whole `#parand-route` has a `pointer` cursor + click; not keyboard-accessible.)

---

## 4. Where this lives (for orientation)

- Figure scene markup & surrounding prose: `index.html` (بخش ۳ · نمونه پرند).
- Scene/cycle/chips/output JS: `js/views.js` — `drawParandRoute`, `buildParandScene`, `runParandCycle`, `p4moveTo`, `renderParandOutput`.
- Styles: `css/style.css` (`.parand-*`, `.po-card`, `.parand-fuel`, `.trip-evidence`).
- Source registry: `data/sources.csv` (S14 added).
- Previous figure-2 map consultation: `docs/map_redesign_handoff.md`; scene-2 framing & “what the article does NOT establish”: `docs/consultation_status.md`, `docs/gasoline_housing_scene2_revised_handoff.md`.

**Bottom line:** Does the “one house in Parand, one job in Tehran → ×days → ×fuel” accumulation read as an argument rather than a calculator, and are the defaults/reveals in §3 the right editorial choices?
