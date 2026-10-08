# Handoff — FX vs CPI: source reconciliation

**Status as of 2026-10-08. Q1 applied. Q2 partly applied (۱۴۰۱ and ۱۴۰۲ corrected, ۱۴۰۳ open). Q3 open.**

Q1 (which CPI series) is **decided and implemented** — see "Applied" below. The outside computation's
**arithmetic is correct**: every cell reproduces from the others (`fx_index = fx ÷ 4040 × 100`,
`cpi_index` as a chain of `cpi_yoy_pct`, `ratio = fx_index ÷ cpi_index`, 8/8 rows). All disagreements
are in the inputs.

---

## Applied (Q1) — SCI is now the CPI source

| where | change |
| --- | --- |
| `data/rent_vs_fx/fx_inflation_annual.csv` | ۱۳۹۷–۱۴۰۰ inflation replaced with SCI (18.0→**26.9**, 41.0→**34.8**, 36.0→**36.4**, 40.0→**40.2**); source ids split into `source_id_fx` / `source_id_inflation` |
| `data/sources.csv` | `S18` added (SCI annual CPI ۱۳۹۷–۱۴۰۳); `S16` note rewritten to record that it now supplies only ۱۳۹۰–۱۳۹۶ inflation |
| `data/rent_vs_fx/panel_annual.csv` | new `source_id_inflation` column |
| `rent-vs-fx.html` | rebuilt — CPI now ×**8.92** (was ×8.64), FX/CPI ratio **2.62** (was 2.70); legend and table note name the source |

The page-level effect is small, as predicted. The point of the change is that the series is now
attributable to a single named source rather than to a handoff workbook.

**Still needed for ۱۳۹۰–۱۳۹۶:** those seven values (21.5 / 30.5 / 34.7 / 15.6 / 11.9 / 9.0 / 10.0)
remain from `S16` and are **unverified**. They are consistent with SCI's published annual-average
rates for those years, but no citation is held. Until confirmed, the CPI chain is SCI for the last
four years and uncited for the first seven — the same shape of problem this document was written to
resolve, just in a smaller window.

**Not changed:** the FX series is untouched. `S16`'s FX is still year-end-ish and its definition is
still unconfirmed; `S17`'s quarterly FX still stands as the drivers page's source.

---

## Q1 detail — two legitimate series, and the splice that mixed them

Both are annual-average CPI inflation, YoY %:

| year | **SCI — مرکز آمار ایران** | World Bank / IMF (WDI `FP.CPI.TOTL.ZG`) |
| ---: | ---: | ---: |
| ۱۳۹۷ | **26.9** | 31.2 |
| ۱۳۹۸ | **34.8** | 41.2 |
| ۱۳۹۹ | **36.4** | 47.1 |
| ۱۴۰۰ | **40.2** | 40.2 / 46.2 *(see note)* |
| ۱۴۰۱ | **45.8** | 43.4 |
| ۱۴۰۲ | **40.7** | 43.5 |
| ۱۴۰۳ | **32.5** | 44.6 |

The World Bank WDI series is sourced from IMF International Financial Statistics — a systematic
measure, not bad data. Neither is "wrong"; they are different instruments.

*Note:* the owner's World Bank list gives **40.2** at ۱۴۰۰ (identical to SCI), while the outside
computation uses **46.2**. One of the two is a transcription error.

### The outside computation's CPI was spliced from both

| year | outside value | SCI | WB / IMF | verdict |
| ---: | ---: | ---: | ---: | --- |
| ۱۳۹۷ | 31.2 | 26.9 | 31.2 | **WB / IMF** |
| ۱۳۹۸ | 41.2 | 34.8 | 41.2 | **WB / IMF** |
| ۱۳۹۹ | 47.1 | 36.4 | 47.1 | **WB / IMF** |
| ۱۴۰۰ | 46.2 | 40.2 | 40.2 | matches neither |
| ۱۴۰۱ | 46.5 | 45.8 | 43.4 | neither (close to SCI, not exact) |
| ۱۴۰۲ | 40.7 | 40.7 | 43.5 | **SCI** |
| ۱۴۰۳ | 32.5 | 32.5 | 44.6 | **SCI** |

Three years from one source, two from the other, and the splice lands at **۱۴۰۰/۱۴۰۱** — precisely
where that computation's "the FX/inflation gap is closing" narrative begins. Part of the apparent
closing is a change of measuring instrument, not a change in the economy.

### What correcting to SCI does

| | cumulative ۱۳۹۶ → ۱۴۰۳ | ratio at ۱۴۰۳ (his FX) | ratio at ۱۴۰۳ (`S17` FX) |
| --- | ---: | ---: | ---: |
| outside (spliced) | ×10.88 | 1.48 | 1.57 |
| **SCI** | **×8.89** | **1.81** | **1.92** |
| WB / IMF (۱۴۰۰ = 40.2) | ×11.37 | 1.42 | 1.50 |

SCI is *lower* than WB/IMF for ۱۳۹۷–۱۳۹۹, so the spliced series overstated inflation and thereby
understated how far FX ran ahead. Year by year on SCI the ratio is roughly **flat**, not closing:

| year | ۱۳۹۷ | ۱۳۹۸ | ۱۳۹۹ | ۱۴۰۰ | ۱۴۰۱ | ۱۴۰۲ | ۱۴۰۳ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| his FX | 2.05 | 1.87 | 2.43 | 1.97 | 1.81 | 1.92 | 1.81 |
| `S17` FX | 1.94 | 1.79 | **2.40** | 1.96 | 2.01 | 1.88 | **1.92** |

On `S17` FX the series ends where it started (۱٫۹۴ → ۱٫۹۲). There is a peak at ۱۳۹۹ and a retreat
from it, but no sustained convergence.

---

## Q2 — Annual-average free-market FX ⚠️ ۱۴۰۱ and ۱۴۰۲ fixed, ۱۴۰۳ still open

**Update — applied.** A 35-point sample at a regular **21-day interval** was supplied (`S19`):
17 points from ۱۴۰۱-۰۱-۱۵ to ۱۴۰۱-۱۲-۱۵ and 18 from ۱۴۰۲-۰۱-۰۷ to ۱۴۰۲-۱۲-۲۸. It settles the
question — and **inverts** the earlier reading:

| year | sampled (time-weighted) | outside file | `S17` quarterly mean | verdict |
| ---: | ---: | ---: | ---: | --- |
| ۱۴۰۱ | **34,655** | 34,800 | 40,250 | **`S17` is ~14% too high** |
| ۱۴۰۲ | **51,583** | 52,000 | 53,000 | all agree |

The outside file's ۱۴۰۱ was right and **our `S17` was wrong**, so the earlier note about it taking the
floor of a range was wrong too. Quarterly means from the samples now override `S17`:

| quarter | `S17` | corrected | Δ | samples |
| --- | ---: | ---: | ---: | ---: |
| بهار ۱۴۰۱ | 30,000 | 29,416 | −1.9% | 4 |
| تابستان ۱۴۰۱ | 34,000 | 31,176 | −8.3% | 5 |
| پائیز ۱۴۰۱ | 42,000 | 35,097 | −16.4% | 4 |
| زمستان ۱۴۰۱ | 55,000 | 44,894 | −18.4% | 4 |
| بهار ۱۴۰۲ | 52,000 | 51,287 | −1.4% | 5 |
| تابستان ۱۴۰۲ | 50,000 | 49,547 | −0.9% | 4 |
| پائیز ۱۴۰۲ | 52,000 | 50,518 | −2.8% | 4 |
| زمستان ۱۴۰۲ | 58,000 | 55,196 | −4.8% | 5 |

Annual FX growth changes materially: ۱۴۰۱ **+50% → +31%**, ۱۴۰۲ **+32% → +47%**. Originals are kept
in `panel_quarterly.csv` (`fx_original_toman`, `fx_source_id`).

**Still needed:** `S19` has no site name or URL — "a currency-conversion site" — so its provenance is
weaker than `S17`'s and it needs identifying. And **۱۴۰۰ and ۱۴۰۳ were not sampled**, so if the same
error exists there the chart is still wrong. The one readable point from the earlier chart image,
۱۴۰۳-۱۲-۲۷ = ۹۷۷٬۸۰۰ ریال ≈ ۹۷٬۷۸۰ تومان, sits above both candidate ۱۴۰۳ annual means, which hints
`S17`'s ۱۴۰۳ may be too low rather than too high — the opposite direction to ۱۴۰۱.

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

## Our own series needed the same fix — applied

`S16`'s inflation column was a **third** variant, overlapping SCI only partially:

| year | `S16` (before) | SCI | diff |
| ---: | ---: | ---: | ---: |
| ۱۳۹۷ | 18.0 | 26.9 | **+8.9** |
| ۱۳۹۸ | 41.0 | 34.8 | **−6.2** |
| ۱۳۹۹ | 36.0 | 36.4 | +0.4 |
| ۱۴۰۰ | 40.0 | 40.2 | +0.2 |

۱۳۹۹ and ۱۴۰۰ already matched SCI; ۱۳۹۷ and ۱۳۹۸ did not. So the old column was **an SCI series with
two bad years**, not a different measure — which is why replacing ۱۳۹۷–۱۴۰۰ with SCI *de-splices* the
chain rather than creating a splice.

`S16` only covers ۱۳۹۰–۱۴۰۰, so the SCI swap left ۱۳۹۰–۱۳۹۶ still needing a source of its own. That
gap is recorded in `data/sources.csv` and in the page footer.

---

## Order of work

1. ~~**Q1 — apply SCI.**~~ **Done.** What remains is a citation for the ۱۳۹۰–۱۳۹۶ continuation.
2. ~~**Q2 — correct ۱۴۰۱–۱۴۰۲ FX.**~~ **Done.** Remaining: identify the `S19` site, and sample ۱۴۰۰ and
   ۱۴۰۳, which the same error may affect.
3. **Q3 — pin down the rent definition.** Lowest urgency for the FX/CPI question, but it blocks any
   single rent narrative across the site.

**Cross-page consequence:** `rent-vs-fx.html` reports a ratio of **2.62** over ۱۳۹۰–۱۴۰۰; the new
analysis over ۱۳۹۶–۱۴۰۳ lands near **1.9** on corrected inputs. Both are defensible — the earlier
window contains the ۱۳۹۱–۹۲ devaluation, and both datasets peak at ۱۳۹۹ — but shipping both without a
line of explanation will read as a contradiction.

## Where things live

`data/rent_vs_fx/fx_inflation_annual.csv` (`S16`) · `data/rent_drivers/fx_house_rent_quarterly.csv`
(`S17`) · `data/annual.csv` (`S2`) · `data/raw/infl.json` · source register in `data/sources.csv`
