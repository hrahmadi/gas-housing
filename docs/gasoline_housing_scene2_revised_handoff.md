# Developer Handoff — Revised Research + Interaction Direction

## Project

Interactive Persian data-article:

**ارتباط بین مصرف بنزین و هزینه بالای مسکن**

Format: single static HTML page, Persian RTL, deployed on GitHub Pages. Client-side only; no backend/server required.

This document updates the earlier interaction/article handoffs. It incorporates the fresh-eyes review of the Tehran affordability map and the decision to proceed without waiting for a complete origin-destination commuting matrix.

---

# 1. Core editorial thesis

The article is **not** trying to prove a quantified national causal relationship between housing prices and gasoline consumption.

The thesis is narrower and more useful:

> **بخشی از مصرف بالای بنزین ایران ممکن است نه حاصل سفرهای غیرضروری، بلکه هزینه انرژیِ فاصله‌ای باشد که بحران مسکن میان محل زندگی و محل کار ایجاد کرده است.**

In plain terms:

**Housing unaffordability → spatial displacement → longer distance between home and employment → necessary commuting → transport-energy consumption → gasoline is one visible manifestation.**

Cheap gasoline may make this spatial arrangement more economically survivable, but the article should not claim that cheap gasoline created all of the spatial pattern.

Do not claim a percentage of national gasoline consumption caused by housing.

The article's goal is to **introduce and make intuitive the connection**.

---

# 2. Important new editorial decision: do NOT wait for a complete OD matrix

A public downloadable Tehran metropolitan origin-destination commuting matrix has not been found.

There is strong evidence that detailed OD/work-trip data exist in Iranian census and transport-planning systems, and published research has used inter-city work-trip flows to define Tehran's functional urban area. However, the raw municipality-to-municipality matrix is not currently accessible as a clean public dataset.

**Do not block development on this.**

The article can proceed using:

### Observed / documented evidence

- Tehran district rent data
- Tehran housing-price series
- official minimum-wage series
- national gasoline-consumption series
- census population data
- documented peripheral built-up growth
- published research on Tehran functional-area commuting
- reported Parand–Tehran commuter volumes and distances

### Calculated values

- monthly commute distance from a stated daily distance and working days
- monthly gasoline consumption from stated distance and assumed fuel efficiency
- monthly commuting cost from stated fuel price and calculated fuel consumption

### Estimated / scenario values

- hypothetical worker profiles
- estimated OD distributions where needed
- scenario ranges for peripheral commuting

Every figure should visibly distinguish these categories.

A complete OD matrix would improve precision later, but it is **not required for version 1**.

---

# 3. Revised role of Scene 2: Tehran affordability map

## Previous interpretation to REMOVE

Do **not** make the map's main message:

> "Affordable Tehran has steadily shrunk from 1388 to 1400."

The actual district-rent/minimum-wage calculations do not support a monotonic decline in the number of affordable districts.

Depending on the income multiple, apartment size and rent-share threshold, the number of affordable districts fluctuates substantially across years.

For example:

| Parameters | 1388 | 1389 | 1390 | 1391 | 1392 | 1393 | 1394 | 1395 | 1396 | 1397 | 1398 | 1399 | 1400 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2× min wage, 35 m², 35% | 4 | 5 | 4 | 2 | 3 | 5 | 6 | 6 | 6 | 6 | 6 | 5 | 5 |
| 2× min wage, 30 m², 35% | 9 | 11 | 6 | 4 | 6 | 6 | 10 | 12 | 12 | 9 | 8 | 6 | 6 |
| 3× min wage, 30 m², 35% | 19 | 18 | 17 | 13 | 14 | 18 | 18 | 18 | 18 | 18 | 17 | 15 | 17 |
| 3× min wage, 40 m², 30% | 9 | 9 | 6 | 4 | 4 | 6 | 7 | 10 | 10 | 9 | 7 | 6 | 6 |
| 1× min wage, any size | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Reason: statutory minimum wage sometimes increased sharply, roughly keeping pace with the particular rent measure used in the model.

Therefore:

### The actual purpose of Scene 2 should be:

> **«با این درآمد، در کجای تهران می توان زندگی کرد؟»**

The map demonstrates that **housing affordability is spatially uneven** and that income strongly affects the geographic range of housing options.

It does NOT claim to predict actual household locations.

It does NOT claim that fewer and fewer districts were affordable every year.

---

# 4. Recommended Scene 2 interaction

Default assumptions should be simple, not calculator-like:

- Year: 1388 initially
- Income: 2× statutory minimum wage
- Apartment size: 35 m²
- Rent burden threshold: 35%

Primary user control:

**Income: 1× → 2× → 3× → 5× minimum wage**

Optional/secondary controls can expose apartment size and rent-share assumptions, but they should not dominate the screen.

The map should visually answer:

> **«اگر درآمد شما X باشد، کدام بخش های تهران از نظر اجاره برای شما قابل پرداخت است؟»**

Suggested explanatory text under the map:

> «این نقشه محل واقعی سکونت خانوارها را پیش بینی نمی کند. بر اساس اجاره ثبت شده در مناطق مختلف، درآمد فرضی و یک سقف مشخص برای سهم اجاره از درآمد، فقط جغرافیای تقریبی توان پرداخت را نشان می دهد.»

This disclaimer is important.

---

# 5. How the map should animate over time

Do NOT animate the map as:

**green → less green → less green → less green**

That would imply a monotonic deterioration not supported by the data.

Instead, the time slider can show **how the composition and location of affordable districts changes**.

The visual message is:

> affordability has a geography

rather than:

> affordability necessarily shrinks every year

This is still useful because it sets up the next question:

> **«اگر خانه قابل پرداخت در بخش های مشخصی از شهر متمرکز باشد، این مناطق کجا قرار گرفته اند؟»**

That question leads naturally into peripheral growth.

---

# 6. Minimum wage should remain as a scenario yardstick

Keep statutory minimum wage because it is official, annual and reproducible.

But do NOT describe it as:

- median worker income
- average household income
- the income of a typical worker

Label it as:

> **«درآمد فرضی بر اساس حداقل دستمزد قانونی»**

Using multiple-of-minimum-wage scenarios is useful because it reveals how housing geography changes with income.

The fact that 1× minimum wage produces no affordable district under the default assumptions can be shown, but must not be translated into a sweeping claim such as "minimum-wage workers cannot live in Tehran." It means only that **under the model's specific rent-share, apartment-size and district-rent assumptions, no district passes the affordability threshold**.

---

# 7. Add a small supporting affordability chart

A useful secondary chart is:

**Tehran rent index vs minimum-wage index**

with a common base year, e.g. 1388 = 100.

Purpose:

- provide context for the map
- show why a simple annual affordability count can fluctuate
- make clear that housing pressure and wage policy do not move in a perfectly monotonic way

This chart should support the map, not replace it.

Potential explanatory sentence:

> «اگر فقط نسبت اجاره به حداقل دستمزد را نگاه کنیم، بعضی سال ها حتی شاهد بهبود موقت قدرت پرداخت هستیم. این موضوع نتیجه تغییرات سالانه دستمزد و تفاوت میان حداقل دستمزد و درآمد واقعی خانوارهاست؛ بنابراین برای فهم مسئله فضایی، فقط به یک شاخص سالانه کافی نیست.»

---

# 8. Job-centre overlay: keep it qualitative

Do NOT draw specific districts such as 6, 7, 11 and 12 and label them "the employment centres" unless we obtain a defensible employment-density dataset.

Instead:

### Preferred treatment

Use a restrained, qualitative central-employment-area indication and prose such as:

> «بخش مهمی از اشتغال اداری، تجاری و خدماتی تهران در بخش های مرکزی و میانی شهر متمرکز است.»

No exact employment percentage is needed.

Even better, let the **commuting evidence in Scene 3/4 establish the destination relationship**. This removes the need to build an employment-density layer at all.

---

# 9. Scene 3 should carry more of the spatial-displacement argument

This is the stronger spatial evidence.

Use the metropolitan built-up growth study for 2010–2020:

| Area | Built-up growth 2010–2020 |
|---|---:|
| Tehran | ~4.8% |
| Pardis | ~244.8% |
| Pishva | ~187.8% |
| Pakdasht | ~162.3% |
| Robat Karim | ~138.5% |
| Shahriar | ~82.9% |

The point of this scene is:

> **«اگر مسکن در هسته گران می شود، رشد مسکونی کجا اتفاق می افتد؟»**

The map should visibly show that peripheral areas experienced extraordinary built-up expansion compared with Tehran.

This is much stronger evidence for outward spatial change than the district affordability map's year-by-year affordable-district count.

Scene 2 therefore becomes **supporting context**.

Scene 3 becomes the main empirical spatial-displacement visualization.

---

# 10. Scene 4: commuting without pretending to have a complete OD matrix

We do not need a full OD matrix for version 1.

Use **Parand as the concrete case** and present it explicitly as a reported/illustrative case.

Observed/reported anchor:

- roughly 30–40 thousand daily travelers between Parand and Tehran have been reported
- Parand is roughly 35 km from the Tehran metropolitan edge
- some destinations inside Tehran are around 50 km away one way
- ~100 km/day round trip is therefore a reasonable illustrative upper/mid-range scenario for certain commuters

These figures are reported estimates, not an official municipality-to-municipality OD matrix.

Label them accordingly.

The narrative should say, in effect:

> «پرند نمونه ای از یک شهر پیرامونی است که مسکن را از محل اشتغال جدا کرده است. ده ها هزار نفر هر روز به سمت تهران رفت و آمد می کنند. برای بخشی از آنها، این یعنی ده ها کیلومتر سفر در هر روز کاری.»

---

# 11. The worker scenario is the core interactive narrative

The reader should follow one hypothetical worker rather than interact with a giant transport dashboard.

Example:

> **یک کارمند که در پرند زندگی می کند و در تهران کار می کند.**

Then calculate:

100 km/day × 22 workdays/month = 2,200 km/month

Fuel-efficiency scenarios:

- 7 L/100 km → 154 L/month
- 9 L/100 km → 198 L/month
- 12 L/100 km → 264 L/month

These are **CALCULATED**, based on explicit assumptions.

Do not present them as measured consumption of an actual Parand worker.

---

# 12. The fuel-efficiency control

Use 7 / 9 / 12 L per 100 km as a sensitivity range.

Interpretation:

- 7 = relatively efficient vehicle
- 9 = central illustrative assumption
- 12 = inefficient/older vehicle

The UI should clearly say this is a **scenario range**.

The user should immediately see:

**daily distance → monthly distance → monthly liters**

The interaction should not require knowledge of vehicle engineering.

---

# 13. Gasoline-price interaction

Then ask:

> **«حالا اگر قیمت بنزین را بالا ببریم چه می شود؟»**

Controls:

- gasoline price
- income level
- optionally fuel efficiency

Outputs:

- monthly commute fuel cost
- share of income consumed by commuting

This is a CALCULATED scenario, not an observed statistic.

The conceptual distinction is:

### Discretionary travel

A price increase can reduce demand by causing people to eliminate some trips.

### Necessary work commute

A worker cannot simply remove the commute without potentially affecting employment/income.

The interaction exists to make this distinction intuitively obvious.

---

# 14. Do not overclaim the 1398 protest connection

The article can say:

- gasoline prices were raised sharply in November 2019
- widespread protests followed
- fuel costs do not affect all households equally
- a long-distance peripheral worker is structurally more exposed to a fuel-price shock than someone living close to work

Do NOT claim:

- the protests were caused only by gasoline prices
- protesters were predominantly peripheral workers
- we have identified a causal share of protest participation attributable to commuting cost

The point is illustration and distributional exposure, not proof of protest causality.

---

# 15. Revised narrative order for the article

The article should reveal the thesis very early.

### Opening

1. Gasoline consumption rose from about 56m to 120m L/day between 1382 and 1402.
2. Conventional explanation: gasoline is too cheap.
3. Immediate counter-question:

> «اما مردم چرا این قدر باید رانندگی کنند؟»

4. Introduce housing affordability as the missing factor.
5. State that the article will investigate the connection through data.

### Scene 2 — Affordability

> «با این درآمد، در کجای تهران می توان زندگی کرد؟»

Show spatial affordability, not a claimed monotonic collapse.

### Scene 3 — Peripheralization

> «وقتی خانه قابل پرداخت از مرکز شهر دور می شود، این خانه ها کجا ظاهر می شوند؟»

Show peripheral built-up growth.

### Scene 4 — Commute

> «اما شغل کجا مانده است؟»

Introduce commuting evidence and Parand.

### Scene 5 — Energy cost

> «این فاصله چقدر انرژی می خواهد؟»

Calculate kilometers and liters.

### Scene 6 — Fuel-price shock

> «اگر بنزین گران شود، این فاصله ناپدید نمی شود.»

Show monthly cost / income exposure.

### Scene 7 — Policy

Contrast:

- make travel more expensive
- make proximity and low-energy travel more accessible

Potential levers:

- affordable housing near employment
- job creation closer to peripheral residents
- regional rail / metro / BRT / reliable public transport
- then fuel-price reform as one policy lever among several

---

# 16. Article voice / design principle

This is an **article, not a dashboard or spreadsheet**.

The reader should be told what is happening and why it matters. Interactions should reveal or reinforce the argument.

Target ratio:

**~70% narrative / ~30% interactive data experience.**

Avoid:

- excessive controls
- giant parameter panels
- unexplained formulas
- dashboards full of KPIs
- forcing the reader to discover the thesis by themselves

The page should feel like a serious data investigation with a clear argument.

Desktop-first is acceptable for the initial version. Responsive/mobile adaptation can follow once the desktop narrative and interaction are stable.

---

# 17. Evidence hierarchy

### High confidence / observed or official

- annual national gasoline consumption
- Tehran district rent dataset
- annual statutory minimum wage
- Tehran housing-price series
- census population
- metropolitan built-up-area change
- published work-commuting/functional-area research

### Medium confidence / reported empirical evidence

- Parand 30–40k daily Tehran travelers
- Parand 35–50 km one-way distance
- peripheral commuter burden reported in Iranian media/research

### Calculated by us

- 2,200 km/month for a 100-km/day, 22-day scenario
- 154/198/264 L/month for 7/9/12 L/100km
- commuting cost at specified gasoline prices

### Estimated / scenario assumptions

- hypothetical worker income
- hypothetical mode split when needed
- assumed destination distribution if OD is unavailable

Never blur these categories.

---

# 18. Recommended footnote language

For observed data:

> **داده مشاهده شده / منبع رسمی**

For our arithmetic:

> **محاسبه بر اساس داده و فرض های اعلام شده**

For scenarios:

> **برآورد سناریویی، نه آمار رسمی**

For the affordability map specifically:

> «نتیجه این مدل نشان دهنده توان پرداخت فرضی است، نه محل واقعی سکونت خانوارها.»

---

# 19. What would make a data journalist / urban economist object?

Avoid these claims:

1. "Affordable districts steadily disappeared every year."
2. "Minimum wage represents the typical worker."
3. "Districts 6/7/11/12 are exactly the employment centres" without employment-density evidence.
4. "X% of Iranian gasoline consumption is caused by housing prices."
5. "1398 protests happened because peripheral workers couldn't afford gasoline."
6. Treating reported Parand figures as a census OD matrix.
7. Presenting calculated fuel consumption as observed individual consumption.

Strong claims that are defensible:

1. Housing affordability is geographically uneven.
2. Income strongly changes the geography of affordable housing.
3. Peripheral Tehran has experienced much faster built-up growth than central Tehran.
4. Peripheral settlements are functionally linked to Tehran by commuting.
5. Long mandatory commuting consumes time, money and transport energy.
6. Fuel-price increases therefore have a different distributional effect on peripheral workers with long commutes.

---

# 20. Developer implementation priorities

### First priority

Build a clean narrative prototype with these three working pieces:

1. gasoline growth chart
2. Tehran affordability map
3. Parand worker commute calculator

### Second priority

Add peripheral-growth map and commute narrative.

### Third priority

Add gasoline-price/income sensitivity interaction.

Do not wait for a complete OD dataset.

Keep the architecture modular so that a future OD matrix can replace the scenario layer without rewriting the article.

---

# 21. Key conceptual line for the whole project

The article should ultimately turn the question around.

Instead of only asking:

> **«چطور مصرف بنزین را کم کنیم؟»**

ask:

> **«چطور نیاز به این مقدار رفت و آمد را کم کنیم؟»**

Because if people have been pushed away from employment by housing costs, simply making the journey more expensive does not remove the distance.

It only makes crossing that distance more expensive.

That is the central structural insight the interactive article should leave the reader with.
