# Dataset Handoff — Iran Gasoline, Housing & Spatial Inequality

**For:** Interactive article developer  
**Research state:** September 2026

## 1. Purpose

This handoff tells the developer which datasets/evidence we currently have, which are suitable for production, which are contextual or illustrative, and which gaps still need research.

The article is **narrative-first**. Data should support the story rather than turn the page into a dashboard.

## 2. Core thesis

> Iran’s unusually high gasoline consumption is partly a consequence of spatial inequality created by housing affordability. As workers are pushed toward cheaper housing on the metropolitan periphery, the distance between affordable housing and employment increases. Fuel and transport energy become part of the cost of accessing a job.

The data do **not** need to prove a national causal coefficient. They need to make the mechanism concrete and credible, while clearly distinguishing observed data, sourced claims, and our own calculations/estimates.

## 3. Data hierarchy

| Tier | Meaning | How to use |
|---|---|---|
| **A — production-grade** | Official or well-defined underlying dataset; directly usable for charts/calculations. | Safe to put in primary visuals with source note. |
| **B — strong supporting evidence** | Peer-reviewed/research source or official estimate, but not a complete raw series or has definitional limitations. | Use in narrative, annotations, case studies, or secondary visuals. |
| **C — illustrative estimate** | Our calculation, interpolation, or reported figure that has not been independently verified to primary-data level. | Label explicitly as **برآورد / محاسبه**; never make it look like observed data. |
| **D — unresolved** | Interesting lead, but not reliable enough for publication yet. | Do not use in final article until verified. |

## 4. Master annual dataset

Current working file:

`iran_gas_housing_research_dataset.xlsx`

The `Annual Data` sheet contains the harmonized working series currently available. Treat it as a **research scratch dataset**, not a final audited database.

Recommended production structure:

```text
data/annual.csv
```

Include `source_id` and units for every variable.

---

# 5. Tehran rental affordability dataset — MAIN HOUSING DATASET

### Primary source

Ali Tayebi open GitHub project:

https://github.com/alitayebi/maps/tree/master/rent

### What it gives us

- Quarterly Tehran housing/rent information.
- All **22 municipal districts** of Tehran.
- Begins in **1388** and extends through **1400**.
- Combined with annual official wage changes to construct affordability.
- Designed specifically to show **where a household can afford to live**.

### Recommended use

This should be the principal dataset for the interactive map:

> **«با درآمد X تومان، کجای تهران می‌توانستی خانه اجاره کنی؟»**

Show how affordable geography changes through time and income level.

### Important

Do **not** immediately collapse the dataset into a citywide average. The spatial dimension is the point.

Before production, the developer should extract the raw files and document:

- exact variable names
- units
- quarterly definitions
- wage assumptions
- affordability threshold
- apartment-size assumptions
- geographic identifiers

### Production file

```text
data/tehran_rent_district.csv
```

---

# 6. Tehran housing purchase-price series

A long-run Tehran average transaction price per square meter is available through Central Bank / official housing-market reporting and secondary reproductions.

### Working series currently used

| Year | Tehran avg. price / m² (million تومان) |
|---|---:|
| 1382 | 0.599 |
| 1383 | 0.584 |
| 1384 | 0.649 |
| 1385 | 0.831 |
| 1386 | 1.509 |
| 1387 | 1.778 |
| 1388 | 1.607 |
| 1389 | 1.735 |
| 1390 | 2.041 |
| 1391 | 2.964 |
| 1392 | 3.954 |
| 1393 | 4.176 |
| 1394 | 4.141 |
| 1395 | 4.372 |
| 1396 | 4.822 |
| 1397 | 8.241 |
| 1398 | 13.330 |
| 1399 | 24.029 |
| 1400 | 31.296 |

A known later observation is **81.44 million تومان/m² in Esfand 1402**. Do **not** label that number as the annual 1402 average; it is a month-end observation.

### Recommended use

Use purchase prices as a **long-run context chart** showing the housing-market transformation.

Do not make this the principal affordability measure. Rent is closer to the lived experience of a worker currently deciding where to live.

**Confidence:** B

---

# 7. Tehran rent series

Working annual/point observations from published Central Bank housing-market reporting:

| Observation | Average rent / m² (تومان) |
|---|---:|
| 1390 | 12,950 |
| 1391 | 15,470 |
| 1392 | 18,590 |
| 1393 | 20,860 |
| 1394 | 22,900 |
| 1395 | 23,420 |
| 1396 | 28,210 |
| 1397 | 36,450 |
| 1398 | 47,500 |
| 1399 | 62,900 |
| 1400 | 84,800 |
| 1401 | 126,900 |

### Important

Before final publication, harmonize whether each observation is:

- annual average
- year-end
- specific month

For the main time-series chart, the district-level Tayebi data are preferable because they preserve spatial variation.

**Confidence:** A/B

---

# 8. Minimum wage

### Source family

Ministry of Cooperatives, Labour and Social Welfare / High Labour Council annual wage decisions.

The government sets the annual statutory wage floor around the Persian New Year.

### Working series

| Year | Monthly minimum wage (rial) |
|---|---:|
| 1382 | 853,380 |
| 1383 | 1,066,020 |
| 1384 | 1,225,920 |
| 1385 | 1,500,000 |
| 1386 | 1,830,000 |
| 1387 | 2,196,000 |
| 1388 | 2,635,200 |
| 1389 | 3,030,000 |
| 1390 | 3,303,000 |
| 1391 | 3,897,000 |
| 1392 | 4,871,250 |
| 1393 | 6,089,100 |
| 1394 | 7,124,250 |
| 1395 | 8,121,660 |
| 1396 | 9,299,310 |
| 1397 | 11,112,690 |
| 1398 | 15,168,810 |
| 1399 | 18,354,270 |
| 1400 | 26,554,950 |
| 1401 | 41,797,500 |
| 1402 | 53,082,840 |

### Recommended use

Use as a **deliberately conservative low-income worker scenario**.

Do not describe it as the average salary of a Tehran worker.

Potential derived measures:

- rent / minimum wage
- housing price / annual minimum wage
- fuel cost / minimum wage
- affordable apartment area under specified rent burden

**Confidence:** A/B

---

# 9. Iran gasoline consumption

### Working annual series

| Year | Average daily gasoline consumption (million L/day) |
|---|---:|
| 1382 | 56 |
| 1383 | 61 |
| 1384 | 67 |
| 1385 | 74 |
| 1386 | 65 |
| 1387 | 67 |
| 1388 | 65 |
| 1389 | 61 |
| 1390 | 60 |
| 1391 | 64 |
| 1392 | 68 |
| 1393 | 70 |
| 1394 | 71 |
| 1395 | 75 |
| 1396 | 81 |
| 1397 | 89 |
| 1398 | 89 |
| 1399 | 75 |
| 1400 | 88 |
| 1401 | 105 |
| 1402 | 120 |

Recent points are supported by Oil Ministry / SHANA reporting, including approximately **120 million liters/day in 1402**.

### Important caveat

The **1399 decline** must be treated as a COVID mobility shock, not evidence against the housing hypothesis.

### Recommended use

Primary opening chart:

> **56 → 120 million liters/day**

Then ask what portion of this is discretionary driving versus energy required to reach work.

**Confidence:** A/B

---

# 10. Population

Use census population primarily as context/control rather than as the main argument.

Known Tehran-city census points include approximately:

| Census | Tehran city population |
|---|---:|
| 1385 | 7.71m |
| 1390 | ~8.15m |
| 1395 | 8.69m |

Be explicit about whether a figure refers to:

- Tehran city
- Tehran province
- Tehran Metropolitan Region
- Functional Urban Area

These are not interchangeable.

**Confidence:** A

---

# 11. Tehran metropolitan periphery — population/spatial growth

A recent Tehran Metropolitan Region study uses housing transactions and satellite-derived built-up data for **2010–2020**.

Striking reported built-up growth figures:

| County | Built-up growth 2010–2020 |
|---|---:|
| Tehran | 4.8% |
| Pardis | 244.8% |
| Pakdasht | 162.3% |
| Pishva | 187.8% |
| Robat Karim | 138.5% |
| Shahriar | 82.9% |
| Rey | 58.0% |

This is strong supporting evidence for **center-to-periphery spatial displacement/expansion**.

### Recommended use

Animate or map peripheral expansion after showing Tehran housing affordability.

**Confidence:** B

---

# 12. Functional/commuting data — strongest current evidence

### Tehran Functional Urban Area research

A 2025 study uses actual **inter-city travel-to-work flows** for **1996, 2006 and 2016** to define Tehran’s functional urban area.

The data were obtained from the **Road Maintenance & Transportation Organization (RMTO)**.

This establishes that robust OD commuting data exist and were used in serious metropolitan research.

The raw numerical OD matrix has **not yet been found publicly**.

Source:

https://doi.org/10.1016/j.pirs.2024.100075

### Functional linkage indicators

Another study provides functional linkage indicators for peripheral cities:

| City | Functional indicator |
|---|---:|
| Tehran | 13.052 |
| Robat Karim | 2.921 |
| Eslamshahr | 2.794 |
| Pardis | 2.033 |
| Varamin | 1.826 |
| Pakdasht | 1.122 |
| Hashtgerd | 1.288 |
| Shahriar | 0.971 |

Source:

https://doi.org/10.1111/rsp3.12627

### IMPORTANT

These indicators are **not commuter headcounts**. Do not turn them into "X thousand commuters."

They can establish strong functional relationships but cannot replace an OD matrix.

**Confidence:** B

---

# 13. Parand — main concrete case study

Parand is currently the best available bridge between:

**lower-cost housing → peripheral settlement → work commute → transport/fuel cost**

Research describes Parand and other Tehran new towns as being created to absorb Tehran population overflow / provide lower-cost housing, while developing a dormitory relationship with the metropolitan core.

Source:

https://doi.org/10.1080/19463138.2011.652359

### Reported commuting figures

Contemporary reporting gives approximately:

- **30–40 thousand daily travelers** between Parand and Tehran.
- At least **~35 km** to the Tehran metropolitan edge.
- Up to **~50 km** to destinations inside Tehran.
- Therefore **~100 km/day round trip** is a plausible scenario for some workers.

One source explicitly describes the majority of these travelers as using private transport before the Parand metro connection.

### Important confidence rule

Treat 30–40k and 35–50 km as **reported estimates / case-study evidence**, not census-grade OD data.

Do not present them as a complete official Parand→Tehran OD matrix.

---

# 14. Parand commute calculation

This is a **model calculation**, not observed fuel consumption for a particular worker.

Assume:

- 100 km/day round trip
- 22 workdays/month

Then:

```text
100 km × 22 = 2,200 km/month
```

At different vehicle-efficiency assumptions:

| Efficiency | Monthly gasoline |
|---|---:|
| 7 L/100 km | 154 L/month |
| 9 L/100 km | 198 L/month |
| 12 L/100 km | 264 L/month |

Label this clearly as:

> **محاسبه / برآورد بر اساس مسافت رفت‌وبرگشت و مصرف فرضی خودرو**

Do not make it visually indistinguishable from observed data.

---

# 15. Vehicle efficiency

Do **not** hard-code one national fuel-efficiency number.

Use a scenario range such as:

- **7 L/100 km** — relatively efficient
- **9 L/100 km** — middle scenario
- **12 L/100 km** — high-consumption/older-vehicle scenario

The 12 L/100 km figure is useful as a high-consumption scenario associated with old/inefficient cars.

The range is deliberately transparent and avoids making the story depend on one controversial fleet-average estimate.

**Confidence:** C when used as an assumption

---

# 16. Public transportation

Do **not** currently use the draft claim:

> «تنها ۲۶ درصد جمعیت تهران روزانه از حمل و نقل عمومی استفاده می‌کنند.»

Searches found conflicting definitions/older modal-share statistics.

Before publication, verify exactly what the number means:

- share of population
- share of trips
- share of commuting trips
- daily passenger journeys

For the article, the preferred metric is **share of commuting/work trips served by public transportation**, with year and denominator stated.

For the first version, it is enough to show that better transit can replace part of the gasoline-dependent commute and that peripheral transit access is a constraint.

**Confidence:** D until verified

---

# 17. National transport / OD database leads

The Traffic Research Laboratory at Iran University of Science and Technology documents a national transport-plan update that included a large **travel-demand database** and roughly **250 OD matrices**, including passenger OD matrices.

Source:

https://trafficlab.ir/portfolio/%D8%A8%D8%B1%D9%88%D8%B2%D8%B1%D8%B3%D8%A7%D9%86%DB%8C-%D8%B7%D8%B1%D8%AD-%D8%AC%D8%A7%D9%85%D8%B9-%D8%AD%D9%85%D9%84-%D9%88-%D9%82%D9%84-%DA%A9%D8%B4%D9%88%D8%B1-%D8%AA%D9%87%DB%8C/

The raw matrices have not yet been located for download.

### Additional research lead

Traffic Lab's thesis list includes a 1401 thesis titled approximately:

> «برآورد ماتریس تقاضای سفرهای بین‌شهری با استفاده از داده‌های شبکه تلفن همراه: مطالعه موردی استان تهران»

This could provide newer OD evidence if the underlying thesis/report or tables can be obtained.

Source:

https://trafficlab.ir/%D9%BE%D8%A7%DB%8C%D8%A7%D9%86-%D9%86%D8%A7%D9%85%D9%87-%D9%87%D8%A7/

---

# 18. Current annual dataset

The working annual data assembled so far:

| Year | Gasoline (m L/day) | Tehran house price (M toman/m²) | Minimum wage (rial/month) |
|---|---:|---:|---:|
| 1382 | 56 | 0.599 | 853,380 |
| 1383 | 61 | 0.584 | 1,066,020 |
| 1384 | 67 | 0.649 | 1,225,920 |
| 1385 | 74 | 0.831 | 1,500,000 |
| 1386 | 65 | 1.509 | 1,830,000 |
| 1387 | 67 | 1.778 | 2,196,000 |
| 1388 | 65 | 1.607 | 2,635,200 |
| 1389 | 61 | 1.735 | 3,030,000 |
| 1390 | 60 | 2.041 | 3,303,000 |
| 1391 | 64 | 2.964 | 3,897,000 |
| 1392 | 68 | 3.954 | 4,871,250 |
| 1393 | 70 | 4.176 | 6,089,100 |
| 1394 | 71 | 4.141 | 7,124,250 |
| 1395 | 75 | 4.372 | 8,121,660 |
| 1396 | 81 | 4.822 | 9,299,310 |
| 1397 | 89 | 8.241 | 11,112,690 |
| 1398 | 89 | 13.330 | 15,168,810 |
| 1399 | 75 | 24.029 | 18,354,270 |
| 1400 | 88 | 31.296 | 26,554,950 |
| 1401 | 105 | — | 41,797,500 |
| 1402 | 120 | — | 53,082,840 |

Note: the housing series is not complete after 1400 in this annual table; later observations exist but must be harmonized before being treated as annual averages.

---

# 19. What the developer may calculate now

## Safe/appropriate calculations

### Indexed comparison

Create an indexed chart:

- gasoline consumption
- Tehran housing price
- minimum wage

with a common base year.

**Warning:** descriptive only. Do not imply causality from co-movement.

### Housing affordability

Use:

> rent / wage

rather than relying exclusively on house-price growth.

### Periphery expansion

Map or animate peripheral built-up growth alongside the housing-affordability story.

### Parand commute model

Use 35–50 km one-way / ~100 km round-trip as a transparent case-study scenario.

### Monthly fuel requirement

Use 7 / 9 / 12 L/100km scenarios.

### Fuel cost vs income

Calculate fuel cost as a percentage of minimum wage under several gasoline-price scenarios.

### 1398 policy-shock illustration

Show how the economics of an existing mandatory commute change after a fuel-price increase.

Do not claim that housing geography alone caused the 1398 protests.

---

# 20. What NOT to claim

Do not claim that rising housing prices quantitatively caused Iran's national gasoline-consumption increase.

Do not treat functional linkage indicators such as DII as commuter counts.

Do not present the Parand 30–40k figure as a full official OD matrix.

Do not present **81.44m تومان/m² in Esfand 1402** as the annual 1402 Tehran average.

Do not use minimum wage as average worker income.

Do not use the **26% Tehran public-transport** number until its definition and source are verified.

Do not present model-derived commute fuel consumption as observed individual consumption.

---

# 21. Recommended production file structure

```text
data/
  annual.csv
  tehran_rent_district.csv
  periphery.csv
  sources.csv
  assumptions.json
```

### `annual.csv`

Cleaned annual series with:

- year
- variable
- value
- unit
- source_id

### `tehran_rent_district.csv`

Raw/cleaned Tayebi quarterly district data, 1388–1400.

### `periphery.csv`

Municipality population, spatial-growth and commuting evidence.

### `sources.csv`

Every numerical value or factual claim with:

- source_id
- source title
- URL
- publication date (where available)
- variable/claim
- definition
- confidence tier

### `assumptions.json`

All model assumptions, including:

- fuel efficiency
- workdays/month
- commute distance
- gasoline-price scenarios
- any future transit assumptions

**Do not embed unexplained constants in JavaScript.** Every modeled figure should come from the assumptions/data files.

---

# 22. Primary source list

- **Ali Tayebi — Tehran rent/affordability project:** https://github.com/alitayebi/maps/tree/master/rent
- **Central Bank of Iran:** https://www.cbi.ir/
- **Ministry of Labour / High Labour Council:** https://www.mcls.gov.ir/
- **SHANA gasoline reporting:** https://www.shana.ir/news/477056/
- **Tehran Functional Urban Area research:** https://doi.org/10.1016/j.pirs.2024.100075
- **Functional spatial structure research:** https://doi.org/10.1111/rsp3.12627
- **Tehran new-town / Parand research:** https://doi.org/10.1080/19463138.2011.652359
- **Tehran Metropolitan Region housing/periphery research:** https://www.sciencedirect.com/science/article/pii/S1757780225001064
- **Traffic Research Laboratory — national transport plan:** https://trafficlab.ir/portfolio/%D8%A8%D8%B1%D9%88%D8%B2%D8%B1%D8%B3%D8%A7%D9%86%DB%8C-%D8%B7%D8%B1%D8%AD-%D8%AC%D8%A7%D9%85%D8%B9-%D8%AD%D9%85%D9%84-%D9%88-%D9%86%D9%82%D9%84-%DA%A9%D8%B4%D9%88%D8%B1-%D8%AA%D9%87%DB%8C/
- **Traffic Research Laboratory — thesis list:** https://trafficlab.ir/%D9%BE%D8%A7%DB%8C%D8%A7%D9%86-%D9%86%D8%A7%D9%85%D9%87-%D9%87%D8%A7/

---

# 23. Recommended next research pass

The highest-value missing dataset remains a usable Tehran metropolitan **origin–destination commuting matrix**.

Search first for:

- underlying 2016 census/RMTO commuting tables
- Tehran transport-plan OD matrices
- Tehran traffic comprehensive-plan matrices
- mobile-phone-based OD studies for Tehran province
- municipality-level work-trip flows

If no raw matrix can be obtained, use observed/quoted Parand and other peripheral-city evidence to build a transparent scenario model rather than inventing precise OD shares.

The goal of the article is to **introduce and make visible the connection**, not to claim an econometrically identified national causal effect. A transparent illustrative model is therefore acceptable when clearly labeled.
