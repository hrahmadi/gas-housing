# Kilid public map-data scraper

Reproducible acquisition of **Kilid's public map API** — starting with the 22 municipal
districts of Tehran (cityId `272905`), built so other cities can be enumerated later.

This tool **only downloads and preserves data**. It performs no analysis, no rent
estimation and no cleaning of values.

```bash
python3 kilid_scraper.py --tehran          # download + normalize + validate
python3 kilid_scraper.py --tehran --force  # refresh every response
```

---

## 1. Rules this scraper follows (hard constraints)

| Rule | Where it is enforced |
| --- | --- |
| Raw responses are stored **verbatim** (the exact bytes the server sent) | `KilidClient.get_json()` writes `response.read()` unchanged |
| Nothing is inferred from sale prices (no rent estimation) | normalization only copies fields; rent comes solely from `ASKING_RENT` |
| Missing values stay missing (never `0`, never interpolated) | `cell()` maps `None` -> empty CSV cell |
| Empty `ASKING_RENT` is preserved as empty | `normalize_rent()` writes no row for it; availability marks `no`/`unknown` |
| Listing-derived values are never relabelled official / Statistical-Center data | `metadata.json` disclaimer + `KNOWN_API_NOTES` |
| No smoothing, no adjustment of Kilid values | columns are pass-through copies of API fields |
| District and neighbourhood observations are never mixed in one file | every normalized row carries `level`; the requested level is fixed per run |
| The raw JSON is authoritative; CSVs are convenience only | CSVs are regenerated from `raw/` on every run |
| Cancellation / failure never corrupts an archive | files are written once, fully; reruns reuse them |

---

## 2. Requirements

Python 3.9+ and the standard library only — `requirements.txt` intentionally lists no
third-party packages. No `pip install` step is needed.

---

## 3. CLI

```bash
python3 kilid_scraper.py --tehran                        # 22 Tehran districts, 60 months
python3 kilid_scraper.py --tehran --months 60            # explicit history window
python3 kilid_scraper.py --tehran --force                # ignore cache, re-download all
python3 kilid_scraper.py --tehran --delay 1.0            # slower, even more polite
python3 kilid_scraper.py --city 272905                   # any city by Kilid cityId
python3 kilid_scraper.py --city 272905 --expect-districts 22
python3 kilid_scraper.py --top-cities 10 --rank-by census1395   # 10 largest cities (census order)
python3 kilid_scraper.py --top-cities 10 --national-only  # enumerate + select, download nothing
python3 kilid_scraper.py --cities 272905,272895          # an explicit list of city ids
python3 kilid_scraper.py --discover-country              # save /provinces + report schema
python3 kilid_scraper.py --province 242305               # discovery: list a province's cities
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--months` | `60` | history window sent to `/stats` and `/area-series` |
| `--force` | off | re-download even when a cached raw file exists |
| `--out` | `<script_dir>/kilid_data` | output root |
| `--delay` | `0.75` s | minimum spacing between requests (sequential, never parallel) |
| `--timeout` | `30` s | per-request timeout |
| `--retries` | `4` | retries for `429/500/502/503/504` and network errors (exponential backoff 2 -> 30 s, honours `Retry-After`) |
| `--child-level` | `MUNICIPAL_AREA` | area level to collect for a city (`MUNICIPAL_AREA` or `CITY`) |
| `--expect-districts` | `22` with `--tehran` | abort if discovery count differs (meaningful for single-city runs) |
| `--top-cities [N]` | `10` | enumerate the country, then scrape the N largest cities |
| `--cities ID,ID,...` | – | scrape an explicit list of city ids |
| `--rank-by` | `stockN` | `stockN` \| `sampleSize` \| `pricePsmMedian` (Kilid fields) \| `census1395` (see §10) |
| `--verify-availability` / `--no-verify` | on | probe each candidate and substitute the next one when a city exposes no areas |
| `--include-no-region` | off | also consider cities whose `/provinces` record says `haveRegion=false` |
| `--national-only` | off | enumerate and select only (2 requests), download nothing |
| `--label` | `tehran` / `city-<id>` | used in file names |

Exit codes: `0` success · `1` some downloads failed · `2` validation failed (e.g. not 22
districts) · `130` interrupted.

---

## 4. Output layout

```
kilid_data/
  discovery/
    tehran_municipal_area_children.json   /comparison?childLevel=MUNICIPAL_AREA&cityId=272905 (source of the 22 areaIds)
    tehran_regions.json                   /regions?cityId=272905 (373 neighbourhood records; no areaIds)
    provinces.json                        only with --discover-country
    country_schema.json                   schema report for /provinces
  raw/
    districts_index.json                  the discovered 22 districts, with their API fields
    region-01/
      stats.json  area-series.json  supply.json  floor-area.json  forecast.json
    region-02/ ... region-22/             same five files per district
  normalized/
    kilid_tehran_sale_price_monthly.csv   one row per district/month
    kilid_tehran_rent_available.csv       only *populated* ASKING_RENT entries (may be header-only)
    kilid_tehran_availability.csv         what exists / does not exist, per district
  metadata.json                           provenance for this dataset
  scrape_summary.json                     per-run accounting, validation, per-file sha256
```

Directory names come from each district's own `nativeKey` (`272905:2` -> `region-02`), never
from request order. `raw/` files are byte-identical to the API response — including
whatever whitespace/escaping the server chose.

### Multi-city runs (`--top-cities`, `--cities`)

Each city gets its own copy of the same layout, plus national artefacts at the root:

```
kilid_data/
  discovery/
    provinces.json                    /provinces (verbatim)
    national_city_children.json       /comparison?childLevel=CITY (verbatim)
    national_cities.json              merged + ranked city list (with coverage notes)
    selected_cities.json              what was selected, what was skipped and why
  normalized/
    kilid_national_city_ranking.csv   every city, ranked
  cities/
    tehran/     {discovery,raw,normalized,metadata.json,scrape_summary.json}
    mashhad/    same layout
    ...
  national_summary.json               per-city recap + totals
```

For `--top-cities`/`--cities` the top-level `discovery/` and `normalized/` hold **national**
files only; per-city data lives under `cities/<label>/`. `--tehran` and `--city` keep the
single-city layout at the root of `--out`.

---

## 5. What the API actually exposes (verified 2026-09-15)

Base URL: `https://kilid.com/api/map`

| Endpoint | Role here | Notes |
| --- | --- | --- |
| `/provinces` | national schema discovery | 31 provinces, 423 cities; city records carry `haveRegion` |
| `/comparison?childLevel=MUNICIPAL_AREA&cityId=272905` | **district discovery** | returns exactly 22 rows with `areaId`, `nativeKey`, `name` |
| `/comparison?childLevel=CITY&provinceId=<id>` | province -> cities | returns each city's `areaId` |
| `/regions?cityId=272905` | reference only | 373 neighbourhood records; **contains no `areaId`** |
| `/stats?months=60&mode=RAW&areaId=<id>` | per-district snapshot | 4 groups: `AVM`, `ASKING_SALE`, `ASKING_RENT`, `TRANSACTION` |
| `/area-series?areaId=<id>&months=60` | monthly sale series | `windowMonths`, `pricePsm*`, `sampleSize`, `trust` |
| `/supply?areaId=<id>` | listing supply | `listingN`, `adN`, `daysOnMarketMedian`, `collectionArtifact` |
| `/floor-area?areaId=<id>` | size distribution | `buckets[]` with `sharePct` |
| `/forecast?areaId=<id>` | model forecast | `available`, `anchorValue`, `horizonMonths` |

Findings worth knowing before you analyse anything:

* `areaId` is a geo UUID, not a numeric Kilid id. The numeric ids are `cityId` and the
  `nativeKey` form `cityId:districtNumber`.
* **`childLevel=NEIGHBORHOOD` does not exist** — the API answers `400 {"message":"childLevel is
  not a market level"}`. Valid market levels seen: `COUNTRY`, `CITY`, `MUNICIPAL_AREA`.
* **`haveRegion` in `/provinces` is unreliable.** Urmia reports `false` yet exposes 13
  municipal areas; Kermanshah reports `true` yet exposes **0**. That is why multi-city runs
  *verify* each candidate instead of trusting the flag (see §10).
* **`stockN` on the national CITY comparison is not a size measure.** Mashhad reports
  `stockN=6737` while its listing sample is `163,116`; Tehran reports `stockN=4,264,326`.
  `sampleSize` (listings in the current period) is the only usable Kilid size proxy.
* The national `childLevel=CITY` response returns 450 rows while `/provinces` lists 423 cities;
  423 match by `cityId`. The 27 unmatched rows carry county-style names (e.g. «خمینی شهر»,
  «شاهین شهر و میمه») and no aggregates. Both raw responses are kept; the difference is
  reported, not guessed away.
* **No rent series is exposed.** `/area-series` accepts a `metric` parameter but ignores
  it (`metric=ASKING_RENT` returns the sale-price payload unchanged). Rent only appears as
  the current `ASKING_RENT` group in `/stats`, and it is empty for Tehran district 2.
  Rent history is therefore reported as `unknown`, not as `no`.
* `/stats` also carries a `TRANSACTION` section (last observed `1400-03`), which is a
  different measurement basis from the listing series. It is preserved in the raw files
  but deliberately **not** merged into the normalized sale CSV.
* `trust: "DIRECT"` means "not modelled by Kilid" — it is **not** evidence of official
  government provenance. `source: "listing"` describes asking prices, not transactions.

### 5.1 What the first Tehran run actually found (2026-09-15)

`python3 kilid_scraper.py --tehran` — 112 requests, 0 failures, validation `pass`.

* **22/22 districts** discovered and downloaded; every district returned 60 monthly
  sale-price points spanning `1400-06` … `1405-05` (uniform window, no gaps, no duplicates).
* **Rent: 0 of 22 districts have current asking-rent data.** All 22 `/stats` responses
  contain an `ASKING_RENT` group with `"empty": true` and `"entries": []`. The expectation
  that e.g. district 1 has rent data is *not* what the public API returns today, so
  `kilid_tehran_rent_available.csv` is header-only. This is a finding about Kilid's coverage,
  not a scraper limitation — and it means rent **cannot** currently be sourced here at all.
* **District 20 is different and must be flagged in any analysis.** 8 of its 60 months
  (`1404-08` … `1405-03`) carry `trust: "MODELED"` with `sampleSize` between 1 and 19,
  i.e. Kilid's own model filled in months where direct listings were too thin. All other
  1312 rows are `trust: "DIRECT"`.
* `source: "listing"` on all 1320 rows — asking prices, not transactions.
* `/stats` also exposes a `TRANSACTION` group, but it is stale: last observed `1400-03`
  for all 22 districts. It is kept in the raw files and never mixed into the sale CSV.
* `area-series.lastPeriodCode` is `1405-05`, while `stats.series.lastObservedPeriodCode` is
  `1405-06`; with `windowMonths: 3` the last closed 3-month window is one month behind the
  latest observation. Do not treat the final point as a complete month.
* `supply` returned 12 monthly points for 21 districts and **10** for district 20.
* House-file sizes: 118 files, ~1.2 MB in total.

---

## 6. Normalized CSV columns

`kilid_tehran_sale_price_monthly.csv` (one row per district/month, from `/area-series`):

```
area_id, native_key, district_number, area_name_fa, level, date, period_code, period_id, label,
price_psm_median_toman, price_psm_smoothed_toman, price_psm_p25_toman, price_psm_p75_toman,
price_total_median_toman, sample_size, trust, source, metraj_band, window_months
```

`kilid_tehran_rent_available.csv` (only populated `ASKING_RENT` entries):

```
area_id, native_key, district_number, area_name_fa, level, period_code, period_id,
rent_metric, kind, value, symbol, sample_size, trust, section, group_empty, group_fixed_period
```

`kilid_tehran_availability.csv` (the "where do we actually have data?" table):

```
district_number, area_name_fa, area_id, native_key, level,
sale_history, sale_history_periods, sale_history_first_period, sale_history_last_period,
sale_history_latest_sample_size, sale_history_latest_trust,
rent_current, rent_current_period, rent_current_metrics, rent_current_sample_size,
rent_history, rent_history_note,
supply, supply_points, supply_latest_period,
floor_area, floor_area_period, floor_area_listing_n,
forecast, forecast_after_period, forecast_horizon_months, notes
```

`rent_current` is `yes` / `no` (section present but empty) / `unknown` (no section returned).
`rent_history` is `unknown` for the reason given above. Absence is never encoded as `0`.

---

## 7. Caching, resume and refresh

* Any raw file that already exists **and parses as JSON** is reused; the run then only
  re-normalizes and re-validates from disk. So `--tehran` is cheap to re-run.
* `--force` re-downloads everything (discovery included) and rewrites the raw files.
* A corrupt/truncated cached file is detected and refetched automatically.
* `scrape_summary.json` records, for every endpoint call: URL, cache hit/miss, byte size,
  sha256 of the stored body and retrieval timestamp — so a cached archive stays auditable.

## 8. Politeness

* Sequential requests, default `0.75 s` spacing (raise it with `--delay`).
* Retries only on `429`/`5xx`/network errors, with exponential backoff and `Retry-After`
  support; no parallel hammering.
* `https://kilid.com/robots.txt` currently allows all user agents (`User-agent: *` /
  `Allow: /`); a Tehran run is ~112 requests. Keep it that way — do not lower `--delay`
  aggressively, and check Kilid's terms before redistributing the data.

## 9. Validation performed on every run

Geography: exactly 22 child areas (configurable), unique `areaId`s, unique `nativeKey`s,
district-number continuity.
History: `area-series` present and non-empty, `periodCode` parseable as `YYYY-MM`,
ascending, no duplicates inside a district, `lastPeriodCode` (series) and
`lastObservedPeriodCode` (`/stats`) consistent across districts with outliers named.
Rent: counts of districts with current `ASKING_RENT`, with an empty section, and with no
section at all (absence is reported, never zeroed).
Integrity: number of raw files on disk.

Results land in `scrape_summary.json` under `validation.checks` with `pass`/`warn`/`fail`.

## 10. National / multi-city collection

```bash
python3 kilid_scraper.py --top-cities 10 --rank-by census1395 --delay 1.0
```

How a multi-city run works:

1. **Enumerate (2 requests, cached):** `/provinces` for province membership + `haveRegion`,
   and `/comparison?childLevel=CITY` for every city's `areaId` and aggregates. Both are stored
   verbatim; `discovery/national_cities.json` merges them and reports coverage differences
   instead of papering over them.
2. **Rank** by a Kilid field (`stockN`, `sampleSize`, `pricePsmMedian`) or by `census1395`.
3. **Verify each candidate** (`--verify-availability`, on by default): one `/comparison` call
   per candidate — the same call the city's own discovery would make, stored in its directory
   and therefore never repeated. The first N candidates that expose areas at the requested
   level are kept; cities that expose none are skipped, named, and recorded in
   `discovery/selected_cities.json` under `skipped_no_data`. **Nothing is silently substituted.**
4. **Scrape** each selected city into `cities/<label>/` and write `national_summary.json`.

Cost: `2 + (candidates examined) + N × (1 + 5 × areas)` requests, all sequential.

### 10.1 `--rank-by census1395` — the one external dataset

Kilid exposes no population field, and its own size fields are unusable for this purpose
(`stockN` puts Mashhad at rank 15 with 6,737 while Tehran has 4,264,326; `sampleSize` is
listing volume, which promotes Amol/Sari/Babolsar above Qom/Ahvaz/Urmia). So `census1395`
uses a **hand-entered table of the 1395 (2016) census urban populations** at the top of
`kilid_scraper.py`:

* it is a **selection aid only** — never written into the sale/rent CSVs, never used as a value;
* `CENSUS_1395_SOURCE` marks it `entered_by_hand: true` and `needs_verification: true`, and the
  same block is copied into `discovery/national_cities.json` and `discovery/selected_cities.json`;
* names are matched against Kilid's own `name_fa`; unmatched names are reported in
  `census_1395.names_not_found_in_enumeration` (all 20 resolved at the time of writing);
* **verify the figures against the Statistical Center of Iran publication before publishing
  anything that cites population.**

### 10.2 Province-level discovery

`--discover-country` saves `/provinces` and reports exactly which fields it exposes.
`--province <ID>` saves the CITY children of one province
(`/comparison?childLevel=CITY&provinceId=<id>`) with `haveRegion` cross-referenced. The
verified hierarchy is:

```
/provinces                                  (31 provinces, each with cities[] and haveRegion)
   -> /comparison?childLevel=CITY&provinceId=<provinceId>          (city areaIds)
      -> /comparison?childLevel=MUNICIPAL_AREA&cityId=<cityId>     (municipal areas)
         -> /stats | /area-series | /supply | /floor-area | /forecast
```

Province-wide bulk collection (hundreds of cities, thousands of requests) is deliberately
left as a separate decision.

### 10.3 What the 10-city run found (2026-09-15)

`python3 kilid_scraper.py --top-cities 10 --rank-by census1395 --delay 1.0`
— 484 requests fetched (+134 served from cache), 0 failures, 0 retries, 2.13 MB.

| city | census rank | areas | sale rows | months per area | modal last period | areas with rent |
| --- | --- | --- | --- | --- | --- | --- |
| Tehran | 1 | 22 | 1320 | 60–60 | 1405-05 | 0 |
| Mashhad | 2 | 13 | 678 | 47–59 | 1405-05 | 0 |
| Isfahan | 3 | 15 | 769 | 43–57 | 1405-05 | 0 |
| Karaj | 4 | 12 | 612 | 44–60 | 1405-05 | 0 |
| Shiraz | 5 | 11 | 610 | 51–60 | 1405-05 | 0 |
| Tabriz | 6 | 10 | 317 | 20–48 | 1405-05 | 0 |
| Qom | 7 | 8 | 131 | 7–35 | 1404-04 | 0 |
| Ahvaz | 8 | 8 | 182 | 14–30 | 1405-05 | 0 |
| Urmia | 10 | 13 | 143 | 11–11 | 1404-04 | 0 |
| Rasht | 11 → **substitute for Kermanshah** | 5 | 197 | 30–54 | 1405-05 | 0 |

Findings that matter for any analysis:

* **Kilid is not a rent source at all right now.** 0 of 117 areas, in all 10 cities, expose a
  populated `ASKING_RENT`; every one of them returns `empty: true`. Rent cannot be sourced from
  this API today — not from Tehran, not from any other city.
* **Only Tehran has a uniform history.** 60/60 months for all 22 of its areas. Every other city
  is ragged: Mashhad 47–59 months per area, Isfahan 43–57, Tabriz 20–48, Qom 7–35, Urmia 11.
  Just **25 of 117 areas** (Tehran 22 + Karaj 2 + Shiraz 1) reach the full 60-month window, so
  cross-city monthly series are *not* comparable without explicit alignment.
* **Some cities lag.** Qom's modal last period is `1404-04` and Urmia's is `1404-04` (Urmia stops
  at `1404-04` for every area) — roughly a year behind Tehran's `1405-05`.
* **Kermanshah (census #9) exposes 0 municipal areas** → recorded in `skipped_no_data` and
  replaced by census #11 Rasht. Nothing was guessed; the substitution is in
  `discovery/selected_cities.json`.
* **Urmia's "13 areas" are not a 1–22 district structure**: numbering is 1..22 with 8, 9, 13
  and 15–20 missing, and each area has only 11 months. Validation flags this
  (`geography.district_numbering` warn).
* Karaj, Qom and Ahvaz warn on `history.latest_period_consistency`: individual areas stop one or
  more months earlier than their city's modal period.
* Kilid's own size proxy (`latest_sample_size_sum`, current listings across areas): Tehran
  419,629 · Mashhad 125,587 · Shiraz 57,197 · Karaj 56,609 · Isfahan 43,486 · Tabriz 33,859 ·
  Rasht 24,253 · Ahvaz 5,437 · Urmia 4,784 · Qom 4,217. Notice how weakly that tracks population
  — Qom (#7 by population) has fewer listings than Rasht (#11).

National roll-ups produced: `normalized/kilid_national_city_availability.csv` (10 rows),
`normalized/kilid_national_area_availability.csv` (117 rows),
`normalized/kilid_national_sale_price_monthly.csv` (4,959 rows), all carrying `city_id`/`level`
so areas and cities are never silently mixed.

**Note on the duplicated Tehran copy:** `kilid_data/` (root) keeps the Tehran-only deliverable
layout from the original handoff, while `kilid_data/cities/tehran/` is Tehran as part of the
multi-city dataset. They are the same API responses; `--force` refreshes each independently.
