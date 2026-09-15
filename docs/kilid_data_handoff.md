# Kilid data handoff — what we now have (and what we do not)

**Acquired:** 2026-09-15 (1405-06/07) · **Source:** Kilid's public map API `https://kilid.com/api/map`
**Tool:** `kilid/kilid_scraper.py` (see `kilid/README.md`) · **Archive:** `kilid/kilid_data/`
**Volume:** ~600 sequential requests, 0 failures, ~9.6 MB, 796 files, every response stored byte-verbatim.

## 1. What was collected

| scope | cities | areas (municipal districts) | monthly sale-price rows |
| --- | --- | --- | --- |
| Tehran (`--tehran`) | 1 | 22 | 1,320 (22 × 60) |
| Top-10 cities by 1395 census population (`--top-cities 10 --rank-by census1395`) | 10 | 117 | 4,959 |

Per area, five endpoints were archived: `/stats`, `/area-series` (60 months requested),
`/supply`, `/floor-area`, `/forecast`. Nothing was smoothed, filled or converted.

Archive on disk: **796 files, 8.73 MB**, including **695 byte-verbatim API responses**
(5 per area × 139 area directories: 117 in `cities/`, plus the 22 Tehran areas kept at the
root) and 30 discovery files. Normalized rows: 4,959 sale-price rows, 117 area-availability
rows, 10 city-availability rows, 450 enumerated cities.

Normalized convenience layers (raw JSON stays authoritative):

```
kilid/kilid_data/normalized/kilid_national_city_availability.csv    10 rows  — coverage per city
kilid/kilid_data/normalized/kilid_national_area_availability.csv   117 rows  — coverage per area
kilid/kilid_data/normalized/kilid_national_sale_price_monthly.csv  4,959 rows — all cities, with city_id + level
kilid/kilid_data/normalized/kilid_national_city_ranking.csv        450 rows  — the city enumeration, ranked
kilid/kilid_data/cities/<label>/…                                             — per-city raw + normalized + reports
```

## 2. The headline finding: there is no rent data

**0 of 117 areas — in all 10 cities — expose a populated `ASKING_RENT` section.** Every one
returns `{"empty": true, "entries": []}` (117 empty sections, 0 missing sections, 0 entries). Also:

* `/area-series` accepts `metric` but ignores it (`metric=ASKING_RENT` returns the sale payload
  unchanged) — there is no rent *series* endpoint.
* `kilid_*_rent_available.csv` files exist but are header-only. Rent history is `unknown`,
  never `no`, and never `0`.
* Consequence: **Kilid cannot be a rent source for this project.** Rent has to come from the
  existing SCI/Tayebi datasets (`data/tehran_rent_district.csv`), or the question has to be
  reframed around sale-price affordability.

## 3. Coverage is ragged outside Tehran

| city | census rank | areas | months per area | modal last period | current rent |
| --- | --- | --- | --- | --- | --- |
| Tehran | 1 | 22 | 60–60 | 1405-05 | 0 |
| Mashhad | 2 | 13 | 47–59 | 1405-05 | 0 |
| Isfahan | 3 | 15 | 43–57 | 1405-05 | 0 |
| Karaj | 4 | 12 | 44–60 | 1405-05 | 0 |
| Shiraz | 5 | 11 | 51–60 | 1405-05 | 0 |
| Tabriz | 6 | 10 | 20–48 | 1405-05 | 0 |
| Qom | 7 | 8 | 7–35 | 1404-04 | 0 |
| Ahvaz | 8 | 8 | 14–30 | 1405-05 | 0 |
| Urmia | 10 | 13 | 11–11 | 1404-04 | 0 |
| Rasht | 11 (substitute for Kermanshah, #9) | 5 | 30–54 | 1405-05 | 0 |

* Only **25 of 117 areas** (Tehran 22, Karaj 2, Shiraz 1) reach the full 60-month window.
  Cross-city monthly comparisons must align windows explicitly — do not assume a common start.
* Kermanshah (census #9) exposes **0** municipal areas; recorded in
  `discovery/selected_cities.json → skipped_no_data`, replaced by census #11 Rasht. Nothing
  was invented.
* Urmia's 13 areas are numbered 1..22 with 8, 9, 13, 15–20 missing — not a complete district map.
* Qom and Urmia stop ~a year behind Tehran (`1404-04`).
* Kilid's `haveRegion` flag in `/provinces` is unreliable (Urmia `false` yet 13 areas;
  Kermanshah `true` yet 0) — the scraper verifies instead of trusting it.

## 4. Data-quality flags to carry into any analysis

* `source: "listing"` everywhere — these are **asking prices from listings**, not transactions
  and not Statistical-Center statistics. `trust: "DIRECT"` only means "not modelled by Kilid".
* **14.1% of all rows are model output, not observations** (`trust: "MODELED"`): 699 of 4,959.
  Concentrated early (1400-06…1400-10 carry ~50 modeled rows per month) and very uneven by city:

  | city | rows | modeled | share | rows with `sampleSize` < 10 |
  | --- | --- | --- | --- | --- |
  | Tehran | 1,320 | 8 | 0.6% | 2 |
  | Mashhad | 678 | 114 | 16.8% | 94 |
  | Isfahan | 769 | 131 | 17.0% | 116 |
  | Karaj | 612 | 45 | 7.4% | 36 |
  | Shiraz | 610 | 101 | 16.6% | 86 |
  | Tabriz | 317 | 100 | 31.5% | 94 |
  | Qom | 131 | 43 | 32.8% | 36 |
  | Ahvaz | 182 | 73 | 40.1% | 70 |
  | Urmia | 143 | 0 | 0.0% | 0 |
  | Rasht | 197 | 84 | 42.6% | 64 |

  Tehran district 20 is the only Tehran case (8 months, `1404-08`…`1405-03`, `sampleSize` 1–19);
  every other Tehran row is `DIRECT`.
* **Thin samples are common outside Tehran**: 598 rows (12%) have `sampleSize` < 10 and 740 (15%)
  have < 50, against a median of 1,952 and a maximum of 82,446. Any city-level index built from
  these series needs a sample-size floor, or the modeled and thin rows will dominate the movement.
* `/stats` also carries a `TRANSACTION` group, stale at `1400-03` for every Tehran district —
  kept in raw, deliberately not merged into the sale CSV.
* Karaj, Qom, Ahvaz: individual areas end 1+ months before their city's modal period.
* `windowMonths: 3` — the last point is a smoothed 3-month window, and
  `lastObservedPeriodCode` runs one month ahead of `series.lastPeriodCode` (`1405-06` vs `1405-05`).
* `supply` series length varies (12 monthly points for 86 of 117 areas, but 4–11 points for the
  rest), while `floor-area` (6 buckets) and `forecast` (`available: true`) are present everywhere.

## 5. Reproduce / extend

```bash
python3 kilid/kilid_scraper.py --tehran                                  # Tehran only
python3 kilid/kilid_scraper.py --top-cities 10 --rank-by census1395      # this dataset
python3 kilid/kilid_scraper.py --top-cities 20 --rank-by census1395      # widen
python3 kilid/kilid_scraper.py --city <cityId>                           # one more city
python3 kilid/kilid_scraper.py --top-cities 10 --national-only           # 2 requests: just the ranking
```

Cached responses are reused; `--force` refreshes. ~1 second per request, sequential.

`--rank-by census1395` is the only external input: a hand-entered 1395 census population table
inside the script, marked `needs_verification` and used **only** to choose cities. Kilid's own
size fields are unusable for ranking (`stockN` ranks Mashhad 15th with 6,737 while Tehran has
4,264,326; listing volume puts Amol/Sari/Babolsar above Qom/Ahvaz/Urmia).

## 6. Open decisions

1. Widen to 20 cities (adds ~a dozen mid-size cities, ~2× the requests), or stop at 10?
2. Rent: accept that Kilid has none and keep using SCI/Tayebi, or look for another source?
3. Whether to publish the raw archive (`kilid/kilid_data/`, ~9.6 MB) with the article repo.
