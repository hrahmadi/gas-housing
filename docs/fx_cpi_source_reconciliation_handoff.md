# Handoff — FX vs CPI: source reconciliation

**Status as of 2026-10-08.** Three open data questions were blocking reconciliation between the CPI
series shipped on `rent-vs-fx.html` (`S16`) and an outside FX-vs-CPI computation covering ۱۳۹۶–۱۴۰۳.
Q1 is now resolved, Q2 is partially answered, Q3 is still open. No code has been changed.

The outside computation's **arithmetic is correct** — every cell reproduces from the others
(`fx_index = fx ÷ 4040 × 100`, `cpi_index` as a chain of `cpi_yoy_pct`, `ratio = fx_index ÷ cpi_index`,
8/8 rows). All disagreements are in the inputs.

---

## Q1 — Which CPI series? ✅ Resolved

There are **two legitimate but different** CPI inflation series in circulation, and they were being
mixed. Both are annual-average (period-average) CPI inflation, YoY %:

| year | **SCI — مرکز آمار ایران** | World Bank / IMF (WDI `FP.CPI.TOTL.ZG`) |
| ---: | ---: | ---: |
| ۱۳۹۷ | **26.9** | 31.2 |
| ۱۳۹۸ | **34.8** | 41.2 |
| ۱۳۹۹ | **36.4** | 47.1 |
| ۱۴۰۰ | **40.2** | 40.2 / 46.2 *(see note)* |
| ۱۴۰۱ | **45.8** | 43.4 |
| ۱۴۰۲ | **40.7** | 43.5 |
| ۱۴۰۳ | **32.5** | 44.6 |

**Decision: use SCI.** It is the domestic official source, and the question being asked is about the
Iranian consumer price level. The World Bank WDI series is sourced from IMF International Financial
Statistics, so it is a systematic measure, not bad data — but it is a different measure.

*Note:* the owner's World Bank list gives **40.2** at ۱۴۰۰ (identical to SCI), while the outside
computation uses **46.2**. One of the two is a transcription error. Worth confirming before either
is quoted.

### The outside computation's CPI is spliced from both series

This is the substantive finding, and it was not visible from the file alone:

| year | outside value | SCI | WB / IMF | verdict |
| ---: | ---: | ---: | ---: | --- |
| ۱۳۹۷ | 31.2 | 26.9 | 31.2 | **WB / IMF** |
| ۱۳۹۸ | 41.2 | 34.8 | 41.2 | **WB / IMF** |
| ۱۳۹۹ | 47.1 | 36.4 | 47.1 | **WB / IMF** |
| ۱۴۰۰ | 46.2 | 40.2 | 40.2 | matches neither |
| ۱۴۰۱ | 46.5 | 45.8 | 43.4 | neither (close to SCI, not exact) |
| ۱۴۰۲ | 40.7 | 40.7 | 43.5 | **SCI** |
| ۱۴۰۳ | 32.5 | 32.5 | 44.6 | **SCI** |

Three years come from one source, two from the other, and the splice lands at **۱۴۰۰/۱۴۰۱** — precisely
where that computation's "the FX/inflation gap is closing" narrative begins. Part of the apparent
closing is a change of measuring instrument, not a change in the economy.

### What correcting to SCI does

| | cumulative ۱۳۹۶ → ۱۴۰۳ | ratio at ۱۴۰۳ (his FX) | ratio at ۱۴۰۳ (`S17` FX) |
| --- | ---: | ---: | ---: |
| outside (spliced) | ×10.88 | 1.48 | 1.57 |
| **SCI (correct)** | **×8.89** | **1.81** | **1.92** |
| WB / IMF (۱۴۰۰ = 40.2) | ×11.37 | 1.42 | 1.50 |

Correcting to SCI **raises** the ratio by ~0.3 — the outside computation understated how far FX ran
ahead of inflation, because its spliced CPI overstated inflation.

Year by year on SCI, the ratio is roughly **flat**, not closing:

| year | ۱۳۹۷ | ۱۳۹۸ | ۱۳۹۹ | ۱۴۰۰ | ۱۴۰۱ | ۱۴۰۲ | ۱۴۰۳ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| his FX | 2.05 | 1.87 | 2.43 | 1.97 | 1.81 | 1.92 | 1.81 |
| `S17` FX | 1.94 | 1.79 | **2.40** | 1.96 | 2.01 | 1.88 | **1.92** |

On `S17` FX the series ends where it started (۱٫۹۴ → ۱٫۹۲). There is a peak at ۱۳۹۹ and a retreat from
it, but no sustained convergence. The "gap is closing" claim still depends mainly on the FX inputs.

---

## Q2 — Annual-average free-market FX for ۱۴۰۱ and ۱۴۰۳ ⚠️ Partially answered

The outside file's FX agrees with the repo's `S17` quarterly mean within 0.3–3.8% for ۱۳۹۶–۱۴۰۰ and
۱۴۰۲, but not for two years, both flagged `est` and both taken from the floor of a stated range:

| year | outside | `S17` quarterly mean | gap | his note |
| ---: | ---: | ---: | ---: | --- |
| ۱۴۰۱ | 34,800 | 40,250 | −13.5% | Euronews |
| ۱۴۰۲ | 52,000 | 53,000 | −1.9% | est (range 50–61k) → 18th pct |
| ۱۴۰۳ | 65,000 | 71,750 | −9.4% | est (range 57–94k) → **22nd pct** |

A price-path chart was supplied (فروردین ۱۴۰۰ → فروردین ۱۴۰۴, rial-denominated). The only labelled
value readable from it is the tooltip at **۱۴۰۳/۱۲/۲۷ = ۹۷۷٬۸۰۰ ریال ≈ ۹۷٬۷۸۰ تومان**.

That is a single endpoint, not an annual average, and a chart image cannot be turned into 48 monthly
observations without fabricating them. It is, however, already informative: the year *ended* near
۹۷٬۷۸۰, well above both candidate annual averages (65,000 and 71,750), which is at least consistent
with the 65,000 estimate being too low.

**Still needed:** the underlying series as data (monthly values or a CSV export), not a screenshot,
so the annual means for ۱۴۰۱ and ۱۴۰۳ can be computed rather than chosen. Note the supplied chart
begins at ۱۴۰۰, so it cannot validate ۱۳۹۶–۱۳۹۹ or the ۱۳۹۶ base year either.

---

## Q3 — Definition of the rent series ❌ Open

Both sources use a Tehran rent-per-m² series, and it does not match ours by any constant factor — so
it is not a unit conversion:

| year | `S17` (converted to تومان/م²) | `S2` in `data/annual.csv` | ratio |
| ---: | ---: | ---: | ---: |
| ۱۳۹۷ | 53,000 | 36,450 | 1.45× |
| ۱۳۹۸ | 69,000 | 47,500 | 1.45× |
| ۱۳۹۹ | 101,500 | 62,900 | 1.61× |
| ۱۴۰۰ | 147,500 | 84,800 | 1.74× |
| ۱۴۰۱ | 221,250 | 126,900 | 1.74× |

The ratio **drifts upward**, which points to different definitions or weighting rather than different
units. The repo currently carries four rent series that do not reconcile: `S2` (`data/annual.csv`),
`tehran_rent_district.csv` (quarterly, ۲۲ districts), `rent_wage_index.csv`, and `S17`.

**Still needed:** unit, whether deposit (ودیعه) is capitalised in, coverage (city-wide vs districts),
and source for the rent series used in the outside dataset.

---

## Our own series needs the same fix

`S16` in `data/rent_vs_fx/fx_inflation_annual.csv` is a **third** variant, overlapping SCI only
partially:

| year | `S16` | SCI | diff |
| ---: | ---: | ---: | ---: |
| ۱۳۹۷ | 18.0 | 26.9 | **+8.9** |
| ۱۳۹۸ | 41.0 | 34.8 | **−6.2** |
| ۱۳۹۹ | 36.0 | 36.4 | +0.4 |
| ۱۴۰۰ | 40.0 | 40.2 | +0.2 |

۱۳۹۹ and ۱۴۰۰ are near-exact SCI; ۱۳۹۷ and ۱۳۹۸ are not. `S16` only covers ۱۳۹۰–۱۴۰۰, so the SCI series
(۱۳۹۷–۱۴۰۳ from the owner) would replace ۱۳۹۷–۱۴۰۰ and leave ۱۳۹۰–۱۳۹۶ needing a source of their own.

Effect on the live page is small — swapping SCI into ۱۳۹۷–۱۴۰۰ moves the CPI index at ۱۴۰۰ from
۸۶۳٫۷ to ۸۹۱٫۹, and the FX/CPI ratio from **2.70 to 2.62** (FX is unchanged at ×۲۳٫۳۳). Worth doing
for correctness, but it will not visibly change that chart.

---

## Order of work

1. **Q1 — apply SCI** everywhere. Decided; needs only the ۱۳۹۰–۱۳۹۶ continuation, which `S16` supplies.
2. **Q2 — obtain the ۱۴۰۱ and ۱۴۰۳ FX series as data.** These two values decide whether the ratio is
   flat or converging.
3. **Q3 — pin down the rent definition.** Lowest urgency for the FX/CPI question, but it blocks any
   single rent narrative across the site.

**Cross-page consequence:** `rent-vs-fx.html` reports a ratio of **2.70** over ۱۳۹۰–۱۴۰۰; the new
analysis over ۱۳۹۶–۱۴۰۳ lands near **1.9** on corrected inputs. Both are defensible — the earlier
window contains the ۱۳۹۱–۹۲ devaluation, and both datasets peak at ۱۳۹۹ — but shipping both without a
line of explanation will read as a contradiction.

## Where things live

`data/rent_vs_fx/fx_inflation_annual.csv` (`S16`) · `data/rent_drivers/fx_house_rent_quarterly.csv`
(`S17`) · `data/annual.csv` (`S2`) · `data/raw/infl.json` · source register in `data/sources.csv`
