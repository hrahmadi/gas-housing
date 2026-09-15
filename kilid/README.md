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
python3 kilid_scraper.py --city 272905 --child-level NEIGHBORHOOD
python3 kilid_scraper.py --city 272905 --expect-districts 22
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
| `--child-level` | `MUNICIPAL_AREA` | area level to collect for a city |
| `--expect-districts` | `22` with `--tehran` | abort if discovery count differs |
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

## 10. National expansion (not done here, on purpose)

`--discover-country` saves `/provinces` and reports exactly which fields it exposes; it
does not invent a hierarchy. The verified path for a later phase is:

```
/provinces                                  (31 provinces, each with cities[] and haveRegion)
   -> /comparison?childLevel=CITY&provinceId=<provinceId>          (city areaIds)
      -> /comparison?childLevel=MUNICIPAL_AREA&cityId=<cityId>     (municipal areas)
         -> /stats | /area-series | /supply | /floor-area | /forecast
```

`--province <ID>` already dumps the city list of a province (with the `haveRegion` flag
cross-referenced), and `--city <ID>` already scrapes any city. Bulk nationwide collection
is intentionally left as a separate decision.
