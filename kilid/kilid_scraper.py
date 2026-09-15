#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kilid public map-data scraper (data acquisition only — no analysis).

Immediate goal
--------------
Download the complete available public map data for all 22 municipal districts of
Tehran (cityId 272905), preserving every raw API response byte-for-byte.

Secondary goal
--------------
The engine is city-agnostic: ``--city <CITY_ID>`` scrapes any city that exposes a
child level, and ``--discover-country`` / ``--province <ID>`` record what the public
API reveals about the national hierarchy instead of guessing it.

Hard rules implemented here (see README.md for the long version)
----------------------------------------------------------------
* Raw responses are written **verbatim** (the exact bytes the server returned).
* Nothing is inferred, smoothed, adjusted, back-filled or interpolated.
  A missing value stays an empty CSV cell — never a zero.
* Rent is never derived from sale prices. An empty ``ASKING_RENT`` section stays
  empty and is reported as "no" in the availability report.
* Listing-derived values are never relabelled as official/Statistical-Center data.
* The normalized CSVs are a convenience layer only; the raw JSON is authoritative.
* Requests are sequential, rate limited (default 0.75 s), retried with exponential
  backoff on 429/5xx, and cached on disk (``--force`` to refresh).

Usage
-----
    python3 kilid_scraper.py --tehran
    python3 kilid_scraper.py --tehran --months 60 --force
    python3 kilid_scraper.py --tehran --delay 1.0
    python3 kilid_scraper.py --city 272905 --child-level NEIGHBORHOOD
    python3 kilid_scraper.py --discover-country
    python3 kilid_scraper.py --province 242305
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------

SCRAPER_VERSION = "1.0.0"

BASE_URL = "https://kilid.com/api/map"
TEHRAN_CITY_ID = 272905
TEHRAN_PROVINCE_ID = 242305
TEHRAN_EXPECTED_DISTRICTS = 22

DEFAULT_MONTHS = 60
DEFAULT_DELAY_S = 0.75
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_RETRIES = 4
BACKOFF_BASE_S = 2.0
BACKOFF_MAX_S = 30.0
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

PERIOD_RE = re.compile(r"^\d{3,4}-\d{2}$")

#: Identify the scraper honestly and keep a contact path in the UA.
USER_AGENT = (
    "gas-housing-kilid-scraper/{version} "
    "(+https://github.com/hrahmadi/gas-housing; public map-data acquisition; low rate)"
).format(version=SCRAPER_VERSION)

#: endpoint name -> (path, params builder)
PER_AREA_ENDPOINTS: Tuple[Tuple[str, str, Callable[[str, int], Dict[str, Any]]], ...] = (
    ("stats", "/stats", lambda area_id, months: {"months": months, "mode": "RAW", "areaId": area_id}),
    ("area-series", "/area-series", lambda area_id, months: {"areaId": area_id, "months": months}),
    ("supply", "/supply", lambda area_id, months: {"areaId": area_id}),
    ("floor-area", "/floor-area", lambda area_id, months: {"areaId": area_id}),
    ("forecast", "/forecast", lambda area_id, months: {"areaId": area_id}),
)

PER_AREA_ENDPOINT_PATHS: Tuple[str, ...] = ("/regions",) + tuple(p for _, p, _ in PER_AREA_ENDPOINTS)

#: Documented API behaviour we verified while writing this scraper (2026-09-15).
#: These are *observations*, not assumptions — they are re-derived from the raw data at
#: runtime wherever it matters, and are re-checked on every run by the validation step.
KNOWN_API_NOTES: Tuple[str, ...] = (
    "/comparison?childLevel=MUNICIPAL_AREA&cityId=<id> is what exposes the 22 Tehran "
    "district areaIds; /regions?cityId=<id> returns 373 neighbourhood records and no areaIds.",
    "areaId values are geo UUIDs, not the numeric Kilid ids (cityId / nativeKey are numeric).",
    "/area-series accepts a metric parameter but ignores it: metric=ASKING_RENT returns the "
    "sale-price payload unchanged. No rent *series* endpoint is exposed publicly as of "
    "2026-09-15, so the availability report marks rent history as 'unknown'.",
    "/stats carries four groups: AVM, ASKING_SALE, ASKING_RENT and TRANSACTION. ASKING_RENT "
    "is empty for Tehran district 2 (and must stay empty in our output).",
)

#: The ONLY external dataset in this scraper, and it is used for *selection only*.
#: It is never merged into the normalized sale/rent CSVs, and it must be checked
#: against the published census tables before anything is published.
CENSUS_1395_SOURCE: Dict[str, Any] = {
    "name": "Statistical Center of Iran — 1395 (2016) national census, urban population of the city proper",
    "entered_by_hand": True,
    "needs_verification": True,
    "purpose": "choosing which cities to scrape (Kilid exposes no population field)",
}

#: (census rank, city name exactly as Kilid spells it, population)
CENSUS_1395_TOP_CITIES: Tuple[Tuple[int, str, int], ...] = (
    (1, "تهران", 8693706),
    (2, "مشهد", 3001184),
    (3, "اصفهان", 1961260),
    (4, "کرج", 1592492),
    (5, "شیراز", 1565572),
    (6, "تبریز", 1558693),
    (7, "قم", 1201955),
    (8, "اهواز", 1184788),
    (9, "کرمانشاه", 946651),
    (10, "ارومیه", 736224),
    (11, "رشت", 679995),
    (12, "زاهدان", 587730),
    (13, "همدان", 554406),
    (14, "کرمان", 537718),
    (15, "یزد", 529673),
    (16, "اردبیل", 529374),
    (17, "بندرعباس", 526648),
    (18, "اراک", 520944),
    (19, "اسلامشهر", 448129),
    (20, "زنجان", 430871),
)

AVAILABILITY_FIELDS: Tuple[str, ...] = (
    "district_number",
    "area_name_fa",
    "area_id",
    "native_key",
    "level",
    "sale_history",
    "sale_history_periods",
    "sale_history_first_period",
    "sale_history_last_period",
    "sale_history_latest_sample_size",
    "sale_history_latest_trust",
    "rent_current",
    "rent_current_period",
    "rent_current_metrics",
    "rent_current_sample_size",
    "rent_history",
    "rent_history_note",
    "supply",
    "supply_points",
    "supply_latest_period",
    "floor_area",
    "floor_area_period",
    "floor_area_listing_n",
    "forecast",
    "forecast_after_period",
    "forecast_horizon_months",
    "notes",
)

SALE_FIELDS: Tuple[str, ...] = (
    "area_id",
    "native_key",
    "district_number",
    "area_name_fa",
    "level",
    "date",
    "period_code",
    "period_id",
    "label",
    "price_psm_median_toman",
    "price_psm_smoothed_toman",
    "price_psm_p25_toman",
    "price_psm_p75_toman",
    "price_total_median_toman",
    "sample_size",
    "trust",
    "source",
    "metraj_band",
    "window_months",
)

RENT_FIELDS: Tuple[str, ...] = (
    "area_id",
    "native_key",
    "district_number",
    "area_name_fa",
    "level",
    "period_code",
    "period_id",
    "rent_metric",
    "kind",
    "value",
    "symbol",
    "sample_size",
    "trust",
    "section",
    "group_empty",
    "group_fixed_period",
)


# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_from_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def cell(value: Any) -> Any:
    """CSV cell: ``None`` becomes an empty string (never 0, never 0.0)."""
    return "" if value is None else value


def parse_native_number(native_key: Optional[str]) -> Optional[int]:
    """``"272905:2"`` -> ``2``. Returns ``None`` when the key carries no number."""
    if not native_key:
        return None
    tail = str(native_key).split(":")[-1].strip()
    return int(tail) if tail.isdigit() else None


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def human_bytes(n: Optional[int]) -> str:
    if n is None:
        return "-"
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.2f} MB"


def git_commit(cwd: Path) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return proc.stdout.strip() or None
    except Exception:
        pass
    return None


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")


def read_json(path: Path) -> Any:
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def write_csv(path: Path, fields: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: cell(row.get(key)) for key in fields})


# --------------------------------------------------------------------------------------
# HTTP client
# --------------------------------------------------------------------------------------


class FetchError(RuntimeError):
    def __init__(self, message: str, *, status: Optional[int] = None, url: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.url = url


class KilidClient:
    """Sequential, throttled, retrying, disk-caching HTTP client for the public API."""

    def __init__(
        self,
        *,
        delay: float = DEFAULT_DELAY_S,
        timeout: float = DEFAULT_TIMEOUT_S,
        retries: int = DEFAULT_RETRIES,
        force: bool = False,
        verbose: bool = True,
    ):
        self.delay = max(0.0, float(delay))
        self.timeout = float(timeout)
        self.retries = max(0, int(retries))
        self.force = bool(force)
        self.verbose = verbose
        self.counter: Dict[str, int] = {
            "endpoint_requests": 0,
            "http_attempts": 0,
            "retries": 0,
            "fetched": 0,
            "cached": 0,
            "failed": 0,
            "bytes_fetched": 0,
        }
        self.fetches: List[Dict[str, Any]] = []
        self._last_request_ts = 0.0

    # -- URL / throttling ----------------------------------------------------------------

    @staticmethod
    def build_url(path: str, params: Optional[Dict[str, Any]] = None) -> str:
        url = f"{BASE_URL}{path}"
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)
        return url

    def _throttle(self) -> None:
        if self.delay <= 0:
            return
        elapsed = time.monotonic() - self._last_request_ts
        wait = self.delay - elapsed
        if wait > 0:
            time.sleep(wait)

    def _backoff(self, attempt: int, why: str) -> None:
        delay = min(BACKOFF_BASE_S * (2 ** attempt), BACKOFF_MAX_S)
        self.counter["retries"] += 1
        if self.verbose:
            print(f"        ... retry {attempt + 1}/{self.retries} in {delay:.0f}s ({why})", flush=True)
        time.sleep(delay)

    # -- transport ----------------------------------------------------------------------

    def _http_get(self, url: str) -> bytes:
        attempt = 0
        while True:
            self.counter["http_attempts"] += 1
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "Accept-Language": "fa,en;q=0.8",
                    "User-Agent": USER_AGENT,
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = response.read()
                self._last_request_ts = time.monotonic()
                return body
            except urllib.error.HTTPError as exc:  # subclass of URLError: must come first
                self._last_request_ts = time.monotonic()
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", "replace")[:400]
                except Exception:
                    pass
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                if exc.code in RETRY_STATUSES and attempt < self.retries:
                    self._backoff(attempt, f"HTTP {exc.code}")
                    attempt += 1
                    continue
                raise FetchError(
                    f"HTTP {exc.code} {url} :: {detail}", status=exc.code, url=url
                ) from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                self._last_request_ts = time.monotonic()
                if attempt < self.retries:
                    self._backoff(attempt, f"{type(exc).__name__}: {exc}")
                    attempt += 1
                    continue
                raise FetchError(
                    f"network error after {attempt + 1} attempt(s): {exc} :: {url}", url=url
                ) from exc

    # -- cached JSON fetch ---------------------------------------------------------------

    def get_json(
        self,
        path: str,
        params: Optional[Dict[str, Any]],
        out_path: Path,
        label: str,
    ) -> Tuple[Any, Dict[str, Any]]:
        """Fetch ``path`` and store the response body verbatim in ``out_path``.

        Existing files are reused unless ``--force`` was given. Returns the decoded
        payload plus a provenance record (url, sha256, bytes, retrieved_at, cache flag).
        """
        url = self.build_url(path, params)
        meta: Dict[str, Any] = {"label": label, "url": url, "file": str(out_path)}

        if out_path.exists() and not self.force:
            body = out_path.read_bytes()
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception as exc:
                if self.verbose:
                    print(f"        ! cached {out_path.name} is not valid JSON ({exc}) - refetching", flush=True)
            else:
                self.counter["cached"] += 1
                meta.update(
                    {
                        "from_cache": True,
                        "bytes": len(body),
                        "sha256": sha256_bytes(body),
                        "file_mtime": iso_from_ts(out_path.stat().st_mtime),
                    }
                )
                self.fetches.append(meta)
                return payload, meta

        # (if we get here with an existing file, its cache copy was unreadable: refetch)
        self.counter["endpoint_requests"] += 1
        self._throttle()
        try:
            body = self._http_get(url)
        except FetchError as exc:
            self.counter["failed"] += 1
            meta.update({"from_cache": False, "error": str(exc), "status": exc.status})
            self.fetches.append(meta)
            raise

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as exc:  # non-JSON body: keep nothing, report it
            self.counter["failed"] += 1
            meta.update({"from_cache": False, "error": f"invalid JSON: {exc}", "bytes": len(body)})
            self.fetches.append(meta)
            raise FetchError(f"response from {url} is not valid JSON: {exc}", url=url) from exc

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(body)  # verbatim: the raw artefact

        self.counter["fetched"] += 1
        self.counter["bytes_fetched"] += len(body)
        meta.update(
            {
                "from_cache": False,
                "bytes": len(body),
                "sha256": sha256_bytes(body),
                "retrieved_at": utc_now_iso(),
            }
        )
        self.fetches.append(meta)
        return payload, meta


# --------------------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------------------


def discover_city(
    client: KilidClient,
    out_dir: Path,
    *,
    city_id: int,
    label: str,
    child_level: str,
    expect_count: Optional[int],
) -> Dict[str, Any]:
    """Resolve ``cityId`` -> child areas (the 22 Tehran districts for MUNICIPAL_AREA)."""
    discovery_dir = out_dir / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)

    comparison_file = discovery_dir / f"{label}_{child_level.lower()}_children.json"
    payload, _ = client.get_json(
        "/comparison",
        {"childLevel": child_level, "cityId": city_id},
        comparison_file,
        "discovery:comparison",
    )

    city_area = payload.get("area") or {}
    rows = payload.get("rows") or []
    if not isinstance(rows, list):
        raise FetchError(f"unexpected /comparison payload for cityId={city_id} (no rows list)")

    # /regions is saved for reference; it returns neighbourhoods (no areaIds).
    regions_file = discovery_dir / f"{label}_regions.json"
    regions_error: Optional[str] = None
    try:
        client.get_json("/regions", {"cityId": city_id}, regions_file, "discovery:regions")
    except FetchError as exc:
        regions_error = str(exc)
        if client.verbose:
            print(f"    ! /regions failed (non-fatal): {exc}", flush=True)

    enriched: List[Dict[str, Any]] = []
    for position, row in enumerate(rows):
        number = parse_native_number(row.get("nativeKey"))
        enriched.append({"row": row, "number": number, "position": position})

    if enriched and all(item["number"] is not None for item in enriched):
        enriched.sort(key=lambda item: item["number"])

    used_dirs: Dict[str, int] = {}
    districts: List[Dict[str, Any]] = []
    for index, item in enumerate(enriched, start=1):
        row = item["row"]
        number = item["number"]
        dir_name = f"region-{number:02d}" if number is not None else f"area-{index:02d}"
        if dir_name in used_dirs:
            used_dirs[dir_name] += 1
            dir_name = f"{dir_name}-{used_dirs[dir_name]}"
        else:
            used_dirs[dir_name] = 1
        districts.append(
            {
                "index": index,
                "dir": dir_name,
                "area_id": row.get("areaId"),
                "level": row.get("level") or child_level,
                "name_fa": row.get("name"),
                "native_key": row.get("nativeKey"),
                "number": number,
                "slug": row.get("slug"),
                "discovery_row": row,
            }
        )

    distinct_numbers = {d["number"] for d in districts if d["number"] is not None}
    duplicated_numbers = sorted(
        number for number in distinct_numbers if sum(1 for d in districts if d["number"] == number) > 1
    )

    return {
        "label": label,
        "city_id": city_id,
        "child_level": child_level,
        "city_area": city_area,
        "districts": districts,
        "districts_found": len(districts),
        "expected_districts": expect_count,
        "duplicate_district_numbers": duplicated_numbers,
        "comparison_file": str(comparison_file.relative_to(out_dir)),
        "regions_file": str(regions_file.relative_to(out_dir)) if regions_file.exists() else None,
        "regions_error": regions_error,
        "comparison_period_code": payload.get("periodCode"),
        "comparison_source": payload.get("source"),
    }


def discover_country(client: KilidClient, out_dir: Path) -> Dict[str, Any]:
    """Save /provinces verbatim and report the schema it actually exposes."""
    discovery_dir = out_dir / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)

    provinces_file = discovery_dir / "provinces.json"
    payload, _ = client.get_json("/provinces", None, provinces_file, "discovery:provinces")
    if not isinstance(payload, list):
        raise FetchError("/provinces did not return a list")

    province_key_union: set = set()
    city_key_union: set = set()
    total_cities = 0
    provinces_without_cities: List[Dict[str, Any]] = []
    cities_with_regions = 0
    city_ids: List[int] = []

    for province in payload:
        if isinstance(province, dict):
            province_key_union.update(province.keys())
        cities = province.get("cities") if isinstance(province, dict) else None
        if not isinstance(cities, list) or not cities:
            provinces_without_cities.append(
                {"id": province.get("id"), "name": province.get("name")} if isinstance(province, dict) else {}
            )
            continue
        for city in cities:
            total_cities += 1
            if isinstance(city, dict):
                city_key_union.update(city.keys())
                if city.get("haveRegion"):
                    cities_with_regions += 1
                if isinstance(city.get("id"), int):
                    city_ids.append(city["id"])

    schema = {
        "generated_at": utc_now_iso(),
        "endpoint": "/provinces",
        "provinces_returned": len(payload),
        "province_fields": sorted(province_key_union),
        "city_fields": sorted(city_key_union),
        "cities_total": total_cities,
        "cities_with_haveRegion_true": cities_with_regions,
        "provinces_without_cities": provinces_without_cities,
        "hierarchy_observed": {
            "province": {"id_field": "id", "id_example": payload[0].get("id") if payload else None},
            "city": {"id_field": "cities[].id", "note": "matches the cityId used by /comparison, /regions, /stats"},
            "area": {"id_field": "areaId (geo UUID, only via /comparison or per-area endpoints)"},
        },
        "tehran_city_id_present": TEHRAN_CITY_ID in city_ids,
        "city_id_known_example": {"cityId": TEHRAN_CITY_ID, "provinceId": TEHRAN_PROVINCE_ID},
        "what_is_not_exposed": [
            "'areaId' is not present anywhere in /provinces.",
            "'level' is not present in /provinces (use /comparison?childLevel=... to learn levels).",
        ],
        "next_phase": (
            "To enumerate nationally: GET /comparison?childLevel=CITY&provinceId=<provinceId> "
            "gives every city areaId, then GET /comparison?childLevel=MUNICIPAL_AREA&cityId=<cityId> "
            "gives its municipal areas. This scraper deliberately does not guess beyond that."
        ),
        "note": "No hierarchy was invented. Fields listed here are exactly what /provinces returned.",
    }
    write_json(discovery_dir / "country_schema.json", schema)
    return schema


def discover_province(client: KilidClient, out_dir: Path, province_id: int) -> Dict[str, Any]:
    """Save the CITY children of one province (discovery only, no bulk scraping)."""
    discovery_dir = out_dir / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)

    cities_file = discovery_dir / f"province-{province_id}_cities.json"
    payload, _ = client.get_json(
        "/comparison",
        {"childLevel": "CITY", "provinceId": province_id},
        cities_file,
        "discovery:province-cities",
    )
    rows = payload.get("rows") or []

    have_region: Dict[int, Optional[bool]] = {}
    provinces_file = discovery_dir / "provinces.json"
    try:
        provinces = (
            read_json(provinces_file)
            if provinces_file.exists()
            else client.get_json("/provinces", None, provinces_file, "discovery:provinces")[0]
        )
        for province in provinces or []:
            if province.get("id") != province_id:
                continue
            for city in province.get("cities") or []:
                if isinstance(city, dict) and isinstance(city.get("id"), int):
                    have_region[city["id"]] = bool(city.get("haveRegion"))
    except Exception:
        pass

    cities = []
    for row in rows:
        native = row.get("nativeKey")
        city_id = parse_native_number(native)
        cities.append(
            {
                "city_id": city_id,
                "native_key": native,
                "name_fa": row.get("name"),
                "area_id": row.get("areaId"),
                "have_region_per_provinces_endpoint": have_region.get(city_id) if city_id else None,
            }
        )

    report = {
        "generated_at": utc_now_iso(),
        "province_id": province_id,
        "cities_returned": len(cities),
        "cities": cities,
        "file": str(cities_file.relative_to(out_dir)),
        "note": "Discovery only. Run --city <city_id> to scrape one city's children.",
    }
    write_json(discovery_dir / f"province-{province_id}_cities_report.json", report)
    return report


# --------------------------------------------------------------------------------------
# Scraping
# --------------------------------------------------------------------------------------


def scrape_areas(
    client: KilidClient,
    out_dir: Path,
    districts: List[Dict[str, Any]],
    *,
    months: int,
) -> Dict[str, Any]:
    """Download the five per-area endpoints for every district (cache-aware)."""
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    total = len(districts)

    for position, district in enumerate(districts, start=1):
        area_id = district.get("area_id")
        district_dir = raw_dir / district["dir"]
        district_dir.mkdir(parents=True, exist_ok=True)
        heading = f"[{position:>2}/{total}] {district.get('name_fa')} ({district.get('native_key')}) -> raw/{district['dir']}"
        print(heading, flush=True)

        endpoints: Dict[str, Any] = {}
        for name, path, params_fn in PER_AREA_ENDPOINTS:
            out_path = district_dir / f"{name}.json"
            record: Dict[str, Any] = {"endpoint": name, "path": path}
            try:
                payload, meta = client.get_json(
                    path, params_fn(area_id, months), out_path, f"{district['dir']}:{name}"
                )
            except FetchError as exc:
                record.update({"ok": False, "error": str(exc), "status": exc.status})
                endpoints[name] = record
                print(f"        {name:<12} FAILED  {exc}", flush=True)
                continue

            record.update(
                {
                    "ok": True,
                    "from_cache": bool(meta.get("from_cache")),
                    "bytes": meta.get("bytes"),
                    "sha256": meta.get("sha256"),
                    "note": summarize_payload(name, payload),
                }
            )
            endpoints[name] = record
            origin = "cached" if meta.get("from_cache") else "ok"
            print(f"        {name:<12} {origin:<7} {human_bytes(meta.get('bytes'))}  {record['note']}", flush=True)

        results.append({"district": district, "endpoints": endpoints})

    index = {
        "generated_at": utc_now_iso(),
        "months_requested": months,
        "district_count": total,
        "districts": [
            {
                "index": d["index"],
                "dir": d["dir"],
                "area_id": d["area_id"],
                "level": d["level"],
                "name_fa": d["name_fa"],
                "native_key": d["native_key"],
                "district_number": d["number"],
                "slug": d["slug"],
            }
            for d in districts
        ],
        "note": (
            "Directory names come from the API's own district number (nativeKey suffix), "
            "never from request ordering."
        ),
    }
    write_json(raw_dir / "districts_index.json", index)
    return {"results": results, "index": index}


def summarize_payload(name: str, payload: Any) -> str:
    """Short human-readable note about a response — for progress output only."""
    if not isinstance(payload, dict):
        return f"{type(payload).__name__}"
    if name == "area-series":
        return f"{len(payload.get('points') or [])} points, last={payload.get('lastPeriodCode')}"
    if name == "supply":
        return f"{len(payload.get('points') or [])} points"
    if name == "floor-area":
        return f"{len(payload.get('buckets') or [])} buckets, period={payload.get('periodCode')}"
    if name == "forecast":
        return f"available={payload.get('available')}, horizon={payload.get('horizonMonths')}"
    if name == "stats":
        groups = payload.get("groups") or []
        empty = [g.get("section") for g in groups if isinstance(g, dict) and g.get("empty")]
        return f"{len(groups)} groups" + (f", empty={','.join(empty)}" if empty else "")
    return "ok"


# --------------------------------------------------------------------------------------
# Normalization (raw JSON -> convenience CSVs; raw stays authoritative)
# --------------------------------------------------------------------------------------


def load_raw(out_dir: Path, district: Dict[str, Any], name: str) -> Optional[Any]:
    path = out_dir / "raw" / district["dir"] / f"{name}.json"
    if not path.exists():
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def district_area_block(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("area"), dict):
        return payload["area"]
    return {}


def normalize_sale_series(out_dir: Path, districts: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    """One row per district/month from raw ``area-series`` responses."""
    out_path = out_dir / "normalized" / f"kilid_{label}_sale_price_monthly.csv"
    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    per_district: Dict[str, int] = {}

    for district in districts:
        series = load_raw(out_dir, district, "area-series")
        if not isinstance(series, dict):
            skipped.append({"dir": district["dir"], "reason": "no area-series.json"})
            continue
        area = district_area_block(series) or {}
        source = series.get("source")
        band = series.get("metrajBand")
        window = series.get("windowMonths")
        count = 0
        for point in series.get("points") or []:
            if not isinstance(point, dict):
                continue
            rows.append(
                {
                    "area_id": district.get("area_id") or area.get("areaId"),
                    "native_key": district.get("native_key") or area.get("nativeKey"),
                    "district_number": district.get("number"),
                    "area_name_fa": district.get("name_fa") or area.get("nameFa"),
                    "level": district.get("level") or area.get("level"),
                    "date": point.get("date"),
                    "period_code": point.get("periodCode"),
                    "period_id": point.get("periodId"),
                    "label": point.get("label"),
                    "price_psm_median_toman": point.get("pricePsmMedian"),
                    "price_psm_smoothed_toman": point.get("pricePsmSmoothed"),
                    "price_psm_p25_toman": point.get("pricePsmP25"),
                    "price_psm_p75_toman": point.get("pricePsmP75"),
                    "price_total_median_toman": point.get("priceTotalMedian"),
                    "sample_size": point.get("sampleSize"),
                    "trust": point.get("trust"),
                    "source": source,
                    "metraj_band": band,
                    "window_months": window,
                }
            )
            count += 1
        per_district[district["dir"]] = count

    write_csv(out_path, SALE_FIELDS, rows)
    return {
        "file": str(out_path.relative_to(out_dir)),
        "rows": len(rows),
        "districts_with_series": sum(1 for n in per_district.values() if n),
        "districts_without_series": [k for k, n in per_district.items() if not n],
        "skipped": skipped,
    }


def normalize_rent(out_dir: Path, districts: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    """Rows for every *populated* ASKING_RENT entry. Empty sections produce no rows."""
    out_path = out_dir / "normalized" / f"kilid_{label}_rent_available.csv"
    rows: List[Dict[str, Any]] = []
    districts_with_rent: List[Dict[str, Any]] = []
    districts_without_rent: List[Dict[str, Any]] = []
    unavailable: List[Dict[str, Any]] = []

    for district in districts:
        stats = load_raw(out_dir, district, "stats")
        if not isinstance(stats, dict):
            unavailable.append({"dir": district["dir"], "reason": "no stats.json"})
            continue
        area = district_area_block(stats) or {}
        rent_groups = [
            group
            for group in stats.get("groups") or []
            if isinstance(group, dict) and group.get("section") == "ASKING_RENT"
        ]
        if not rent_groups:
            unavailable.append({"dir": district["dir"], "reason": "no ASKING_RENT section in /stats"})
            continue

        district_entry_count = 0
        for group in rent_groups:
            for entry in group.get("entries") or []:
                if not isinstance(entry, dict):
                    continue
                district_entry_count += 1
                rows.append(
                    {
                        "area_id": district.get("area_id") or area.get("areaId"),
                        "native_key": district.get("native_key") or area.get("nativeKey"),
                        "district_number": district.get("number"),
                        "area_name_fa": district.get("name_fa") or area.get("nameFa"),
                        "level": district.get("level") or area.get("level"),
                        "period_code": entry.get("periodCode") or group.get("periodCode"),
                        "period_id": entry.get("periodId") or group.get("periodId"),
                        "rent_metric": entry.get("label"),
                        "kind": entry.get("kind"),
                        "value": entry.get("value"),
                        "symbol": entry.get("symbol"),
                        "sample_size": entry.get("sampleSize"),
                        "trust": entry.get("trust"),
                        "section": group.get("section"),
                        "group_empty": group.get("empty"),
                        "group_fixed_period": group.get("fixedPeriod"),
                    }
                )
        if district_entry_count:
            districts_with_rent.append(
                {
                    "dir": district["dir"],
                    "name_fa": district.get("name_fa"),
                    "entries": district_entry_count,
                }
            )
        else:
            districts_without_rent.append({"dir": district["dir"], "name_fa": district.get("name_fa")})

    write_csv(out_path, RENT_FIELDS, rows)
    return {
        "file": str(out_path.relative_to(out_dir)),
        "rows": len(rows),
        "districts_with_current_rent": districts_with_rent,
        "districts_without_current_rent": districts_without_rent,
        "districts_without_stats": unavailable,
        "note": "Empty ASKING_RENT is preserved as empty: no row, no zero, no inference from sale prices.",
    }


def build_availability(out_dir: Path, districts: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    """Where is data actually available? (one row per district, no values substituted)."""
    out_path = out_dir / "normalized" / f"kilid_{label}_availability.csv"
    rows: List[Dict[str, Any]] = []

    for district in districts:
        series = load_raw(out_dir, district, "area-series")
        stats = load_raw(out_dir, district, "stats")
        supply = load_raw(out_dir, district, "supply")
        floor_area = load_raw(out_dir, district, "floor-area")
        forecast = load_raw(out_dir, district, "forecast")

        points = (series or {}).get("points") or []
        points = [p for p in points if isinstance(p, dict)]
        first_period = points[0].get("periodCode") if points else None
        last_period = points[-1].get("periodCode") if points else None
        latest_sample = points[-1].get("sampleSize") if points else None
        latest_trust = points[-1].get("trust") if points else None

        rent_groups = [
            g
            for g in (stats or {}).get("groups") or []
            if isinstance(g, dict) and g.get("section") == "ASKING_RENT"
        ]
        rent_entries = [
            e for g in rent_groups for e in (g.get("entries") or []) if isinstance(e, dict)
        ]
        rent_current = "yes" if rent_entries else ("no" if rent_groups else "unknown")
        rent_period = None
        if rent_entries:
            rent_period = rent_entries[0].get("periodCode") or next(
                (g.get("periodCode") for g in rent_groups if g.get("periodCode")), None
            )

        supply_points = [p for p in (supply or {}).get("points") or [] if isinstance(p, dict)]
        buckets = [b for b in (floor_area or {}).get("buckets") or [] if isinstance(b, dict)]

        forecast_available = (forecast or {}).get("available")

        notes: List[str] = []
        if series is None:
            notes.append("area-series missing")
        if stats is None:
            notes.append("stats missing")
        if rent_groups and not rent_entries:
            notes.append("ASKING_RENT present but empty")
        if rent_current == "unknown":
            notes.append("no ASKING_RENT section returned")
        if forecast is not None and forecast_available is False:
            notes.append("forecast not available for this area")

        rows.append(
            {
                "district_number": district.get("number"),
                "area_name_fa": district.get("name_fa"),
                "area_id": district.get("area_id"),
                "native_key": district.get("native_key"),
                "level": district.get("level"),
                "sale_history": "yes" if points else "no",
                "sale_history_periods": len(points) or "",
                "sale_history_first_period": first_period,
                "sale_history_last_period": last_period,
                "sale_history_latest_sample_size": latest_sample,
                "sale_history_latest_trust": latest_trust,
                "rent_current": rent_current,
                "rent_current_period": rent_period,
                "rent_current_metrics": len(rent_entries) or "",
                "rent_current_sample_size": (rent_entries[0].get("sampleSize") if rent_entries else None),
                "rent_history": "unknown",
                "rent_history_note": (
                    "no rent-series endpoint is exposed by the public API "
                    "(/area-series ignores metric=RENT); absence is not zero"
                ),
                "supply": "yes" if supply_points else "no",
                "supply_points": len(supply_points) or "",
                "supply_latest_period": (supply_points[-1].get("periodCode") if supply_points else None),
                "floor_area": "yes" if buckets else "no",
                "floor_area_period": (floor_area or {}).get("periodCode"),
                "floor_area_listing_n": (floor_area or {}).get("totalListingN"),
                "forecast": (
                    "yes" if forecast_available is True else "no" if forecast_available is False else "unknown"
                ),
                "forecast_after_period": (forecast or {}).get("anchorPeriodCode"),
                "forecast_horizon_months": (forecast or {}).get("horizonMonths"),
                "notes": "; ".join(notes),
            }
        )

    write_csv(out_path, AVAILABILITY_FIELDS, rows)
    return {"file": str(out_path.relative_to(out_dir)), "rows": len(rows)}


# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------


def _check(name: str, status: str, detail: str, **extra: Any) -> Dict[str, Any]:
    record = {"check": name, "status": status, "detail": detail}
    record.update(extra)
    return record


def validate(
    out_dir: Path,
    districts: List[Dict[str, Any]],
    *,
    expected_count: Optional[int],
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    expected = "22" if expected_count is None else str(expected_count)

    # --- geography ---------------------------------------------------------------------
    area_ids = [d.get("area_id") for d in districts]
    native_keys = [d.get("native_key") for d in districts]
    unique_area_ids = {a for a in area_ids if a}
    unique_native_keys = {n for n in native_keys if n}

    checks.append(
        _check(
            "geography.district_count",
            "pass" if (expected_count is None or len(districts) == expected_count) else "fail",
            f"found {len(districts)} child areas at the requested level (expected {expected})",
            expected=expected_count,
            found=len(districts),
        )
    )
    checks.append(
        _check(
            "geography.unique_area_ids",
            "pass" if len(unique_area_ids) == len(districts) and len(districts) > 0 else "fail",
            f"{len(unique_area_ids)} unique areaId values for {len(districts)} districts",
        )
    )
    checks.append(
        _check(
            "geography.unique_native_keys",
            "pass" if len(unique_native_keys) == len(districts) and len(districts) > 0 else "fail",
            f"{len(unique_native_keys)} unique nativeKey values for {len(districts)} districts",
        )
    )
    missing_keys = [d["dir"] for d in districts if not d.get("native_key")]
    if missing_keys:
        checks.append(
            _check("geography.native_keys_present", "warn", f"missing nativeKey for: {', '.join(missing_keys)}")
        )

    numbers = [d["number"] for d in districts if d.get("number") is not None]
    if numbers:
        span = f"numbers {min(numbers)}..{max(numbers)}"
        gaps = sorted(set(range(min(numbers), max(numbers) + 1)) - set(numbers))
        checks.append(
            _check(
                "geography.district_numbering",
                "pass" if not gaps else "warn",
                f"{span}; missing numbers: {gaps if gaps else 'none'}",
            )
        )

    # --- history -----------------------------------------------------------------------
    dupes: List[str] = []
    unparseable: List[str] = []
    unordered: List[str] = []
    missing_series: List[str] = []
    last_periods: Dict[str, str] = {}
    last_observed: Dict[str, str] = {}
    for district in districts:
        series = load_raw(out_dir, district, "area-series")
        points = [p for p in ((series or {}).get("points") or []) if isinstance(p, dict)]
        if not points:
            missing_series.append(district["dir"])
            continue
        codes = [p.get("periodCode") for p in points]
        bad = [c for c in codes if not isinstance(c, str) or not PERIOD_RE.match(c)]
        if bad:
            unparseable.append(f"{district['dir']}:{bad[:3]}")
        seen = {c for c in codes if c}
        if len(seen) != len([c for c in codes if c]):
            dupes.append(district["dir"])
        ordered = [c for c in codes if c]
        if ordered != sorted(ordered):
            unordered.append(district["dir"])
        last_periods[district["dir"]] = ordered[-1] if ordered else ""
        stats = load_raw(out_dir, district, "stats")
        observed = ((stats or {}).get("series") or {}).get("lastObservedPeriodCode")
        last_observed[district["dir"]] = observed or ""

    checks.append(
        _check(
            "history.area_series_present",
            "pass" if not missing_series else "fail",
            f"{len(districts) - len(missing_series)}/{len(districts)} districts returned a non-empty area-series",
            missing=missing_series,
        )
    )
    checks.append(
        _check(
            "history.period_codes_parseable",
            "pass" if not unparseable else "fail",
            "all periodCode values match YYYY-MM (Jalali)" if not unparseable else f"bad values: {unparseable[:5]}",
        )
    )
    checks.append(
        _check(
            "history.no_duplicate_period_codes",
            "pass" if not dupes else "fail",
            "no duplicate periodCode within any district" if not dupes else f"duplicates in: {dupes}",
        )
    )
    checks.append(
        _check(
            "history.ascending_order",
            "pass" if not unordered else "warn",
            "every district's points are in ascending periodCode order"
            if not unordered
            else f"not ascending for: {unordered}",
        )
    )

    def outliers(mapping: Dict[str, str]) -> Tuple[List[str], Optional[str]]:
        values = [v for v in mapping.values() if v]
        if not values:
            return [], None
        mode = max(set(values), key=values.count)
        return sorted(k for k, v in mapping.items() if v and v != mode), mode

    series_outliers, series_mode = outliers(last_periods)
    observed_outliers, observed_mode = outliers(last_observed)
    checks.append(
        _check(
            "history.latest_period_consistency",
            "pass" if not series_outliers else "warn",
            f"modal area-series last period = {series_mode}"
            + (f"; differs for: {series_outliers}" if series_outliers else "; all districts agree"),
            modal=series_mode,
            outliers=series_outliers,
        )
    )
    checks.append(
        _check(
            "history.last_observed_period_consistency",
            "pass" if not observed_outliers else "warn",
            f"modal stats.series.lastObservedPeriodCode = {observed_mode}"
            + (f"; differs for: {observed_outliers}" if observed_outliers else "; all districts agree"),
            modal=observed_mode,
            outliers=observed_outliers,
        )
    )

    # --- rent --------------------------------------------------------------------------
    with_rent: List[str] = []
    without_rent: List[str] = []
    no_section: List[str] = []
    for district in districts:
        stats = load_raw(out_dir, district, "stats")
        groups = [
            g for g in ((stats or {}).get("groups") or []) if isinstance(g, dict) and g.get("section") == "ASKING_RENT"
        ]
        entries = [e for g in groups for e in (g.get("entries") or []) if isinstance(e, dict)]
        if entries:
            with_rent.append(district["dir"])
        elif groups:
            without_rent.append(district["dir"])
        else:
            no_section.append(district["dir"])

    checks.append(
        _check(
            "rent.coverage",
            "pass",
            f"{len(with_rent)} district(s) with current ASKING_RENT, "
            f"{len(without_rent)} with an empty ASKING_RENT section, "
            f"{len(no_section)} with no ASKING_RENT section "
            "(absence is reported, never converted to zero)",
            with_current_rent=with_rent,
            empty_section=without_rent,
            no_section=no_section,
        )
    )

    # --- raw integrity -----------------------------------------------------------------
    raw_files = sorted((out_dir / "raw").glob("*/*.json"))
    verbatim_files = [p for p in raw_files if p.name != "districts_index.json"]
    checks.append(
        _check(
            "integrity.raw_files_present",
            "pass" if len(verbatim_files) >= len(districts) else "warn",
            f"{len(verbatim_files)} raw response files under raw/ (5 expected per district)",
        )
    )

    failed = [c for c in checks if c["status"] == "fail"]
    warned = [c for c in checks if c["status"] == "warn"]
    return {
        "checks": checks,
        "failed": len(failed),
        "warned": len(warned),
        "status": "fail" if failed else ("warn" if warned else "pass"),
    }


# --------------------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------------------


def build_metadata(
    out_dir: Path,
    *,
    label: str,
    city_id: int,
    city_name: str,
    city_area: Dict[str, Any],
    child_level: str,
    months: int,
    districts_found: int,
    expected_count: Optional[int],
    args: argparse.Namespace,
    repo_root: Path,
    selection: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    commit = git_commit(repo_root)
    return {
        "source": "Kilid",
        "base_url": BASE_URL,
        "source_kind": "listing-derived public map aggregates (not official government statistics)",
        "city": city_name,
        "city_id": str(city_id),
        "city_area_id": city_area.get("areaId"),
        "city_native_key": city_area.get("nativeKey"),
        "province_id": city_area.get("provinceId"),
        "child_level": child_level,
        "retrieved_at": utc_now_iso(),
        "months_requested": months,
        "endpoints": list(PER_AREA_ENDPOINT_PATHS),
        "discovery_endpoints": ["/provinces", "/comparison?childLevel=<LEVEL>&cityId=<ID>"],
        "scraper_version": SCRAPER_VERSION,
        "scraper_file": str(Path(__file__).resolve()),
        "git_commit": commit,
        "invocation": {
            "argv": sys.argv,
            "force": bool(args.force),
            "delay_seconds": args.delay,
            "timeout_seconds": args.timeout,
            "retries": args.retries,
        },
        "cache_policy": "existing raw JSON is reused unless --force is given",
        "raw_files_are_verbatim": True,
        "districts_found": districts_found,
        "districts_expected": expected_count,
        "selection": selection,
        "notes": list(KNOWN_API_NOTES),
        "rules": [
            "raw responses are never overwritten with cleaned values",
            "missing values are never filled, interpolated or replaced with zero",
            "rent is never inferred from sale prices",
            "listing data is never relabelled as Statistical-Center/official data",
            "district and neighbourhood observations are never mixed in one normalized file",
            "trust=\"DIRECT\" is not treated as evidence of official government provenance",
        ],
        "disclaimer": (
            "Kilid values are asking/listing-derived aggregates published for its own map UI. "
            "They are not official Statistical Center of Iran transaction statistics."
        ),
    }


def build_summary(
    out_dir: Path,
    *,
    client: KilidClient,
    started_at: str,
    finished_at: str,
    started_monotonic: float,
    discovery: Dict[str, Any],
    scrape: Dict[str, Any],
    normalization: Dict[str, Any],
    validation: Dict[str, Any],
    errors: List[Dict[str, Any]],
    exit_code: int = 0,
) -> Dict[str, Any]:
    return {
        "run": {
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": round(time.monotonic() - started_monotonic, 2),
            "scraper_version": SCRAPER_VERSION,
            "label": discovery["label"],
            "city_id": discovery["city_id"],
            "child_level": discovery["child_level"],
        },
        "requests": dict(client.counter),
        "districts": {
            "found": discovery["districts_found"],
            "expected": discovery.get("expected_districts"),
            "duplicate_district_numbers": discovery.get("duplicate_district_numbers"),
        },
        "discovery": {
            "comparison_file": discovery.get("comparison_file"),
            "regions_file": discovery.get("regions_file"),
            "regions_error": discovery.get("regions_error"),
            "comparison_source": discovery.get("comparison_source"),
            "comparison_period_code": discovery.get("comparison_period_code"),
            "city_area": discovery.get("city_area"),
            "district_index_file": "raw/districts_index.json",
        },
        "per_district": [
            {
                "dir": item["district"]["dir"],
                "district_number": item["district"]["number"],
                "name_fa": item["district"]["name_fa"],
                "native_key": item["district"]["native_key"],
                "area_id": item["district"]["area_id"],
                "endpoints": item["endpoints"],
            }
            for item in scrape["results"]
        ],
        "normalized": normalization,
        "validation": validation,
        "fetches": client.fetches,
        "errors": errors,
        "exit_code": exit_code,
    }


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------


def process_city(
    client: KilidClient,
    out_dir: Path,
    *,
    city_id: int,
    label: str,
    city_name: str,
    expected: Optional[int],
    args: argparse.Namespace,
    selection: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Full pipeline for one city: discovery -> download -> normalize -> validate -> reports.

    ``out_dir`` is the *city* directory. For ``--tehran``/``--city`` that is ``--out``
    itself; multi-city runs pass ``<out>/cities/<label>``. Returns a result dict with
    ``exit_code`` and the written summary.
    """
    started_monotonic = time.monotonic()
    started_at = utc_now_iso()
    repo_root = Path(__file__).resolve().parent.parent

    if not args.quiet:
        print(f"\n=== {city_name} (cityId={city_id}), level={args.child_level} -> {out_dir}", flush=True)

    errors: List[Dict[str, Any]] = []

    print("[1/5] discovery: child areas of the city", flush=True)
    try:
        discovery = discover_city(
            client,
            out_dir,
            city_id=city_id,
            label=label,
            child_level=args.child_level,
            expect_count=expected,
        )
    except FetchError as exc:
        print(f"  discovery failed: {exc}", flush=True)
        write_json(
            out_dir / "scrape_summary.json",
            {
                "run": {"started_at": started_at, "finished_at": utc_now_iso(), "label": label, "city_id": city_id},
                "errors": [{"stage": "discovery", "error": str(exc)}],
                "exit_code": 1,
            },
        )
        return {"exit_code": 1, "summary": None, "label": label, "city_id": city_id, "out_dir": str(out_dir)}

    districts = discovery["districts"]
    print(f"  found {discovery['districts_found']} {args.child_level} record(s) for cityId={city_id}", flush=True)
    if discovery["duplicate_district_numbers"]:
        print(f"  ! duplicate district numbers: {discovery['duplicate_district_numbers']}", flush=True)

    if expected is not None and discovery["districts_found"] != expected:
        message = f"expected {expected} districts, found {discovery['districts_found']}"
        print(f"  FAIL  {message}", flush=True)
        errors.append({"stage": "discovery", "error": message})
        validation = {
            "checks": [_check("geography.district_count", "fail", message, expected=expected, found=discovery["districts_found"])],
            "failed": 1,
            "warned": 0,
            "status": "fail",
        }
        write_json(
            out_dir / "scrape_summary.json",
            build_summary(
                out_dir,
                client=client,
                started_at=started_at,
                finished_at=utc_now_iso(),
                started_monotonic=started_monotonic,
                discovery=discovery,
                scrape={"results": [], "index": {}},
                normalization={},
                validation=validation,
                errors=errors,
                exit_code=2,
            ),
        )
        return {
            "exit_code": 2,
            "summary": None,
            "label": label,
            "city_id": city_id,
            "out_dir": str(out_dir),
            "districts_found": discovery["districts_found"],
            "validation": validation,
        }

    print("[2/5] per-district raw downloads", flush=True)
    scrape = scrape_areas(client, out_dir, districts, months=args.months)
    for item in scrape["results"]:
        for name, record in item["endpoints"].items():
            if not record.get("ok"):
                errors.append(
                    {
                        "stage": "download",
                        "district": item["district"]["dir"],
                        "endpoint": name,
                        "error": record.get("error"),
                    }
                )

    print("[3/5] normalization (raw JSON -> convenience CSVs)", flush=True)
    sale = normalize_sale_series(out_dir, districts, label)
    rent = normalize_rent(out_dir, districts, label)
    availability = build_availability(out_dir, districts, label)
    normalization = {"sale_series": sale, "rent": rent, "availability": availability}
    print(f"  {sale['file']}  ({sale['rows']} rows)", flush=True)
    print(f"  {rent['file']}  ({rent['rows']} rows)", flush=True)
    print(f"  {availability['file']}  ({availability['rows']} rows)", flush=True)

    print("[4/5] validation", flush=True)
    validation = validate(out_dir, districts, expected_count=expected)
    for check in validation["checks"]:
        mark = {"pass": "ok  ", "warn": "WARN", "fail": "FAIL"}[check["status"]]
        print(f"  [{mark}] {check['check']}: {check['detail']}", flush=True)

    print("[5/5] reports", flush=True)
    metadata = build_metadata(
        out_dir,
        label=label,
        city_id=city_id,
        city_name=city_name,
        city_area=discovery.get("city_area") or {},
        child_level=args.child_level,
        months=args.months,
        districts_found=discovery["districts_found"],
        expected_count=expected,
        args=args,
        repo_root=repo_root,
        selection=selection,
    )
    write_json(out_dir / "metadata.json", metadata)

    exit_code = 2 if validation["status"] == "fail" else (1 if errors else 0)
    summary = build_summary(
        out_dir,
        client=client,
        started_at=started_at,
        finished_at=utc_now_iso(),
        started_monotonic=started_monotonic,
        discovery=discovery,
        scrape=scrape,
        normalization=normalization,
        validation=validation,
        errors=errors,
        exit_code=exit_code,
    )
    write_json(out_dir / "scrape_summary.json", summary)

    print(
        f"  metadata.json, scrape_summary.json written "
        f"({client.counter['fetched']} fetched, {client.counter['cached']} cached, "
        f"{client.counter['failed']} failed, {human_bytes(client.counter['bytes_fetched'])} downloaded)",
        flush=True,
    )
    print(f"\nvalidation: {validation['status'].upper()}", flush=True)
    print(f"districts with current asking-rent data: {len(rent['districts_with_current_rent'])}", flush=True)

    return {
        "exit_code": exit_code,
        "summary": str(out_dir / "scrape_summary.json"),
        "label": label,
        "city_id": city_id,
        "city_name": city_name,
        "out_dir": str(out_dir),
        "districts_found": discovery["districts_found"],
        "sale_rows": sale["rows"],
        "rent_rows": rent["rows"],
        "districts_with_rent": len(rent["districts_with_current_rent"]),
        "validation": validation,
    }


def run_city(args: argparse.Namespace) -> int:
    """Single-city mode: ``--tehran`` or ``--city <ID>``."""
    out_dir = Path(args.out).resolve()

    if args.tehran:
        city_id = TEHRAN_CITY_ID
        label = "tehran"
        city_name = "Tehran"
        expected: Optional[int] = (
            TEHRAN_EXPECTED_DISTRICTS if args.expect_districts is None else args.expect_districts
        )
    else:
        city_id = int(args.city)
        label = args.label or f"city-{city_id}"
        city_name = args.label or f"city {city_id}"
        expected = args.expect_districts

    client = KilidClient(
        delay=args.delay, timeout=args.timeout, retries=args.retries, force=args.force, verbose=not args.quiet
    )

    print(f"Kilid scraper v{SCRAPER_VERSION} — {city_name} (cityId={city_id}), level={args.child_level}", flush=True)
    print(f"output: {out_dir}", flush=True)
    print(f"cache: {'FORCE refresh' if args.force else 'reuse existing raw JSON'}, delay={args.delay}s", flush=True)

    return process_city(
        client,
        out_dir,
        city_id=city_id,
        label=label,
        city_name=city_name,
        expected=expected,
        args=args,
    )["exit_code"]


def run_discover_country(args: argparse.Namespace) -> int:
    out_dir = Path(args.out).resolve()
    client = KilidClient(delay=args.delay, timeout=args.timeout, retries=args.retries, force=args.force)
    schema = discover_country(client, out_dir)
    print(json.dumps(schema, ensure_ascii=False, indent=2))
    print(f"\nsaved: {out_dir / 'discovery' / 'provinces.json'}", flush=True)
    return 0


def run_province(args: argparse.Namespace) -> int:
    out_dir = Path(args.out).resolve()
    client = KilidClient(delay=args.delay, timeout=args.timeout, retries=args.retries, force=args.force)
    report = discover_province(client, out_dir, int(args.province))
    for city in report["cities"]:
        flag = city.get("have_region_per_provinces_endpoint")
        marker = {True: "regions:yes", False: "regions:no", None: "regions:?"}[flag]
        print(f"  {city['city_id']:>8}  {marker:<12} {city['name_fa']}  ({city['area_id']})")
    print(f"\n{report['cities_returned']} city/cities saved to {report['file']}", flush=True)
    print("Next: python3 kilid_scraper.py --city <city_id>", flush=True)
    return 0


# --------------------------------------------------------------------------------------
# National city enumeration + multi-city runs
# --------------------------------------------------------------------------------------

RANKING_FIELDS: Tuple[str, ...] = ("stockN", "sampleSize", "pricePsmMedian", "census1395")

RANKING_CSV_FIELDS: Tuple[str, ...] = (
    "rank",
    "city_id",
    "native_key",
    "name_fa",
    "province_id",
    "province_name_fa",
    "have_region",
    "census_rank_1395",
    "population_1395",
    "stockN",
    "sampleSize",
    "pricePsmMedian",
    "trust",
    "area_id",
)


def slugify_label(text: Optional[str], fallback: str) -> str:
    """Filesystem-safe ASCII label derived from the API's own slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or fallback


def enumerate_national_cities(client: KilidClient, out_dir: Path, *, rank_by: str) -> Dict[str, Any]:
    """List every city the public API knows about, ranked by a Kilid field.

    Two requests: ``/provinces`` (province membership + ``haveRegion``) and
    ``/comparison?childLevel=CITY`` (city ``areaId`` + housing stock). Nothing is
    inferred: cities that cannot be matched between the two responses are reported.
    """
    discovery_dir = out_dir / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)

    provinces_file = discovery_dir / "provinces.json"
    provinces, _ = client.get_json("/provinces", None, provinces_file, "discovery:provinces")

    national_file = discovery_dir / "national_city_children.json"
    payload, _ = client.get_json(
        "/comparison", {"childLevel": "CITY"}, national_file, "discovery:national-cities"
    )
    rows = payload.get("rows") or []

    province_of: Dict[int, Dict[str, Any]] = {}
    have_region: Dict[int, bool] = {}
    for province in provinces or []:
        if not isinstance(province, dict):
            continue
        for city in province.get("cities") or []:
            if not isinstance(city, dict) or not isinstance(city.get("id"), int):
                continue
            province_of[city["id"]] = {
                "province_id": province.get("id"),
                "province_name_fa": province.get("name"),
                "province_slug": province.get("slug"),
            }
            have_region[city["id"]] = bool(city.get("haveRegion"))

    cities: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        city_id = parse_native_number(row.get("nativeKey"))
        info = province_of.get(city_id, {}) if city_id is not None else {}
        cities.append(
            {
                "city_id": city_id,
                "native_key": row.get("nativeKey"),
                "name_fa": row.get("name"),
                "slug": row.get("slug"),
                "area_id": row.get("areaId"),
                "stockN": row.get("stockN"),
                "sampleSize": row.get("sampleSize"),
                "pricePsmMedian": row.get("pricePsmMedian"),
                "trust": row.get("trust"),
                "have_region": have_region.get(city_id) if city_id is not None else None,
                "province_id": info.get("province_id"),
                "province_name_fa": info.get("province_name_fa"),
            }
        )

    def sort_value(city: Dict[str, Any]) -> float:
        value = city.get(rank_by)
        return float(value) if isinstance(value, (int, float)) else -1.0

    census_by_name = {name: (rank, population) for rank, name, population in CENSUS_1395_TOP_CITIES}
    for city in cities:
        hit = census_by_name.get((city.get("name_fa") or "").strip())
        city["census_rank_1395"] = hit[0] if hit else None
        city["population_1395"] = hit[1] if hit else None

    if rank_by == "census1395":
        # external ranking: cities absent from the table sort last
        cities.sort(
            key=lambda c: (
                c["census_rank_1395"] is None,
                c["census_rank_1395"] or 0,
                -(c["stockN"] or 0),
            )
        )
    else:
        cities.sort(key=sort_value, reverse=True)
    for index, city in enumerate(cities, start=1):
        city["rank"] = index

    resolved_names = {c["name_fa"].strip() for c in cities if c.get("census_rank_1395") is not None}
    census_unresolved = [name for _, name, _ in CENSUS_1395_TOP_CITIES if name not in resolved_names]

    matched = {c["city_id"] for c in cities if c["city_id"] is not None}
    expected_ids = set(province_of)
    coverage = {
        "cities_in_provinces_response": len(expected_ids),
        "cities_in_national_comparison": len(cities),
        "matched_by_city_id": len(expected_ids & matched),
        "in_comparison_not_in_provinces": sorted(matched - expected_ids),
        "in_provinces_not_in_comparison": sorted(expected_ids - matched),
        "note": (
            "The two endpoints do not agree exactly; both raw responses are stored so the "
            "difference can be inspected later. No city was added or removed by hand."
        ),
    }

    report = {
        "generated_at": utc_now_iso(),
        "rank_by": rank_by,
        "rank_by_note": (
            "Kilid fields (stockN/sampleSize/pricePsmMedian) are Kilid's own aggregates and are "
            "proxies for city size only — NOT official census population. rank_by=census1395 uses "
            "the hand-entered table below (selection aid only)."
        ),
        "source_endpoints": ["/provinces", "/comparison?childLevel=CITY"],
        "national_comparison_period_code": payload.get("periodCode"),
        "national_comparison_source": payload.get("source"),
        "census_1395": {
            "source": CENSUS_1395_SOURCE,
            "table": [
                {"rank": rank, "name_fa": name, "population": population}
                for rank, name, population in CENSUS_1395_TOP_CITIES
            ],
            "names_not_found_in_enumeration": census_unresolved,
        },
        "coverage": coverage,
        "cities": cities,
    }
    write_json(discovery_dir / "national_cities.json", report)

    write_csv(
        out_dir / "normalized" / "kilid_national_city_ranking.csv",
        RANKING_CSV_FIELDS,
        [
            {
                "rank": c["rank"],
                "city_id": c["city_id"],
                "native_key": c["native_key"],
                "name_fa": c["name_fa"],
                "province_id": c["province_id"],
                "province_name_fa": c["province_name_fa"],
                "have_region": c["have_region"],
                "census_rank_1395": c.get("census_rank_1395"),
                "population_1395": c.get("population_1395"),
                "stockN": c["stockN"],
                "sampleSize": c["sampleSize"],
                "pricePsmMedian": c["pricePsmMedian"],
                "trust": c["trust"],
                "area_id": c["area_id"],
            }
            for c in cities
        ],
    )
    return report


def select_cities(
    enumeration: Dict[str, Any], args: argparse.Namespace
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[int]]:
    """Pick candidate cities (in selection order). Returns ``(candidates, excluded, unknown_ids)``.

    For ``--rank-by census1395`` the order is the hand-entered census table; otherwise it is
    Kilid's own field. Candidates are only *candidates* — ``verify_candidates`` then keeps the
    ones that actually expose data at the requested level.
    """
    ranked = enumeration["cities"]
    by_id = {c["city_id"]: c for c in ranked if c["city_id"] is not None}

    if args.cities:
        wanted = [int(part) for part in re.split(r"[,\s]+", args.cities.strip()) if part.strip().isdigit()]
        unknown = [w for w in wanted if w not in by_id]
        selected = [by_id[w] for w in wanted if w in by_id]
        return selected, [], unknown

    limit = args.top_cities if args.top_cities is not None else 10

    if args.rank_by == "census1395":
        # The census table itself is the criterion, so haveRegion=false is not used to filter
        # (that flag is unreliable: Urmia reports false yet exposes 13 municipal areas).
        candidates = [c for c in ranked if c.get("census_rank_1395") is not None]
        excluded = [c for c in ranked if c.get("have_region") is False]
        return candidates[: max(limit, len(candidates))], excluded, []

    if args.include_no_region:
        candidates, excluded = ranked, []
    else:
        candidates = [c for c in ranked if c.get("have_region") is not False]
        excluded = [c for c in ranked if c.get("have_region") is False]
    return candidates, excluded, []


def verify_candidates(
    client: KilidClient,
    out_dir: Path,
    candidates: List[Dict[str, Any]],
    *,
    limit: int,
    args: argparse.Namespace,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """Keep the first ``limit`` candidates that really expose areas at the requested level.

    Each check is the same ``/comparison`` call the run would make anyway and is stored in the
    city's own discovery directory, so a verified candidate is never downloaded twice.
    Cities that return nothing are skipped and named — never silently replaced.
    """
    kept: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    examined = 0

    for city in candidates:
        if len(kept) >= limit:
            break
        examined += 1
        label = slugify_label(city.get("slug"), f"city-{city['city_id']}")
        out_path = (
            out_dir
            / "cities"
            / label
            / "discovery"
            / f"{label}_{args.child_level.lower()}_children.json"
        )
        try:
            payload, _ = client.get_json(
                "/comparison",
                {"childLevel": args.child_level, "cityId": city["city_id"]},
                out_path,
                f"{label}:discovery",
            )
            count = len(payload.get("rows") or [])
        except FetchError as exc:
            skipped.append(
                {
                    "city_id": city["city_id"],
                    "name_fa": city.get("name_fa"),
                    "reason": f"discovery request failed: {exc}",
                }
            )
            print(f"  ! {city.get('name_fa')}: {exc}", flush=True)
            continue

        if count == 0:
            skipped.append(
                {
                    "city_id": city["city_id"],
                    "name_fa": city.get("name_fa"),
                    "census_rank_1395": city.get("census_rank_1395"),
                    "reason": f"no {args.child_level} children returned",
                }
            )
            print(f"  - {city.get('name_fa')}: 0 {args.child_level} children — skipped", flush=True)
            continue

        entry = dict(city)
        entry["discovered_children"] = count
        kept.append(entry)
        print(f"  + {city.get('name_fa')}: {count} {args.child_level} area(s)", flush=True)

    return kept, skipped, examined


NATIONAL_CITY_AVAILABILITY_FIELDS: Tuple[str, ...] = (
    "city_id",
    "city_label",
    "city_name_fa",
    "province_name_fa",
    "census_rank_1395",
    "population_1395",
    "level",
    "areas",
    "sale_rows",
    "areas_with_full_window",
    "months_min",
    "months_max",
    "sale_first_period",
    "sale_last_period",
    "latest_sample_size_sum",
    "areas_with_rent",
    "rent_rows",
    "rent_history",
    "validation_status",
    "warnings",
)


def build_national_reports(out_dir: Path, cities: List[Dict[str, Any]], *, months: int) -> Dict[str, Any]:
    """Roll the per-city convenience files up into three national CSVs.

    Reads only files already on disk (the per-city normalized CSVs), so it costs no requests
    and can be regenerated on every run. The raw JSON stays authoritative.
    """
    city_rows: List[Dict[str, Any]] = []
    area_rows: List[Dict[str, Any]] = []
    sale_rows: List[Dict[str, Any]] = []

    for city in cities:
        label = city["label"]
        city_dir = out_dir / "cities" / label
        base = {
            "city_id": city["city_id"],
            "city_label": label,
            "city_name_fa": city.get("name_fa"),
            "province_name_fa": city.get("province_name_fa"),
            "census_rank_1395": city.get("census_rank_1395"),
            "population_1395": city.get("population_1395"),
        }

        sale = _read_csv(city_dir / "normalized" / f"kilid_{label}_sale_price_monthly.csv")
        availability = _read_csv(city_dir / "normalized" / f"kilid_{label}_availability.csv")
        city_summary_path = city_dir / "scrape_summary.json"
        validation_status, warnings = "-", []
        if city_summary_path.exists():
            try:
                summary = read_json(city_summary_path)
                validation = summary.get("validation") or {}
                validation_status = validation.get("status") or "-"
                warnings = [c["check"] for c in validation.get("checks") or [] if c.get("status") == "warn"]
            except Exception:
                pass

        counts = collections.Counter(row.get("native_key") for row in sale)
        levels = {row.get("level") for row in availability if row.get("level")}

        for row in availability:
            area_rows.append({**base, **row})
        for row in sale:
            sale_rows.append({**base, **row})

        latest_samples = [
            int(row["sale_history_latest_sample_size"])
            for row in availability
            if str(row.get("sale_history_latest_sample_size") or "").strip().isdigit()
        ]
        city_rows.append(
            {
                **base,
                "level": ",".join(sorted(levels)) or city.get("level"),
                "areas": len(availability) or city.get("districts_found"),
                "sale_rows": len(sale),
                "areas_with_full_window": sum(1 for n in counts.values() if n >= months),
                "months_min": min(counts.values()) if counts else None,
                "months_max": max(counts.values()) if counts else None,
                "sale_first_period": min((r["period_code"] for r in sale), default=None),
                "sale_last_period": max((r["period_code"] for r in sale), default=None),
                "latest_sample_size_sum": sum(latest_samples) if latest_samples else None,
                "areas_with_rent": sum(1 for row in availability if row.get("rent_current") == "yes"),
                "rent_rows": sum(1 for row in availability if row.get("rent_current") == "yes"),
                "rent_history": "unknown",
                "validation_status": validation_status,
                "warnings": ";".join(warnings),
            }
        )

    normalized_dir = out_dir / "normalized"
    write_csv(normalized_dir / "kilid_national_city_availability.csv", NATIONAL_CITY_AVAILABILITY_FIELDS, city_rows)
    write_csv(
        normalized_dir / "kilid_national_area_availability.csv",
        ("city_label", "city_id", "city_name_fa") + AVAILABILITY_FIELDS,
        area_rows,
    )
    write_csv(
        normalized_dir / "kilid_national_sale_price_monthly.csv",
        ("city_label", "city_id", "city_name_fa") + SALE_FIELDS,
        sale_rows,
    )
    return {
        "city_availability": "normalized/kilid_national_city_availability.csv",
        "area_availability": "normalized/kilid_national_area_availability.csv",
        "sale_price_monthly": "normalized/kilid_national_sale_price_monthly.csv",
        "cities": len(city_rows),
        "areas": len(area_rows),
        "sale_rows": len(sale_rows),
    }


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def run_top_cities(args: argparse.Namespace) -> int:
    """Multi-city mode: enumerate the country, then scrape the selected cities."""
    out_dir = Path(args.out).resolve()
    client = KilidClient(
        delay=args.delay, timeout=args.timeout, retries=args.retries, force=args.force, verbose=not args.quiet
    )

    print(f"Kilid scraper v{SCRAPER_VERSION} — national city selection", flush=True)
    print(f"rank by: {args.rank_by} (Kilid's own field; not official population)", flush=True)
    print(f"output: {out_dir}", flush=True)
    print(f"cache: {'FORCE refresh' if args.force else 'reuse existing raw JSON'}, delay={args.delay}s", flush=True)

    print("\n[0/5] national enumeration (/provinces + /comparison?childLevel=CITY)", flush=True)
    try:
        enumeration = enumerate_national_cities(client, out_dir, rank_by=args.rank_by)
    except FetchError as exc:
        print(f"  enumeration failed: {exc}", flush=True)
        return 1

    coverage = enumeration["coverage"]
    print(
        f"  {coverage['cities_in_national_comparison']} city rows; "
        f"{coverage['cities_in_provinces_response']} cities in /provinces; "
        f"{coverage['matched_by_city_id']} matched by city id",
        flush=True,
    )
    if coverage["in_comparison_not_in_provinces"] or coverage["in_provinces_not_in_comparison"]:
        print(
            f"  ! coverage differs (unmatched: "
            f"{len(coverage['in_comparison_not_in_provinces'])} city rows, "
            f"{len(coverage['in_provinces_not_in_comparison'])} /provinces entries) — both raw files kept",
            flush=True,
        )

    selected, excluded, unknown = select_cities(enumeration, args)
    if unknown:
        print(f"  ! requested city ids not present in the enumeration: {unknown}", flush=True)

    limit = args.top_cities if args.top_cities is not None else len(selected)
    verified_skipped: List[Dict[str, Any]] = []
    examined = 0
    if args.cities or args.national_only or not args.verify_availability:
        selected = selected[:limit]
    else:
        print(
            f"\nverifying which candidates expose {args.child_level} data "
            "(results are reused as each city's discovery call):",
            flush=True,
        )
        selected, verified_skipped, examined = verify_candidates(
            client, out_dir, selected, limit=limit, args=args
        )
        if verified_skipped:
            print(
                "  skipped for lack of data: "
                + ", ".join(
                    f"{s['name_fa']} ({s['reason']})" for s in verified_skipped
                ),
                flush=True,
            )

    if not selected:
        print("  no cities selected — nothing to do", flush=True)
        return 2

    selection = {
        "mode": "cities" if args.cities else "top-cities",
        "rank_by": args.rank_by,
        "requested": args.cities or (args.top_cities if args.top_cities is not None else 10),
        "verified_availability": bool(not args.national_only and args.verify_availability and not args.cities),
        "candidates_examined": examined,
        "skipped_no_data": verified_skipped,
        "excluded_have_region_false_count": len(excluded),
        "excluded_have_region_false_sample": [
            {"rank": c["rank"], "city_id": c["city_id"], "name_fa": c["name_fa"]} for c in excluded[:20]
        ],
        "unknown_city_ids": unknown,
        "enumeration_file": "discovery/national_cities.json",
        "census_1395_source": CENSUS_1395_SOURCE if args.rank_by == "census1395" else None,
        "selected": [
            {
                "rank": c["rank"],
                "city_id": c["city_id"],
                "name_fa": c["name_fa"],
                "slug": c["slug"],
                "have_region": c["have_region"],
                "census_rank_1395": c.get("census_rank_1395"),
                "population_1395": c.get("population_1395"),
                "stockN": c["stockN"],
                "discovered_children": c.get("discovered_children"),
                "province_name_fa": c["province_name_fa"],
            }
            for c in selected
        ],
    }
    write_json(out_dir / "discovery" / "selected_cities.json", selection)

    print(f"\nselected {len(selected)} city/cities:", flush=True)
    for c in selected:
        flag = {True: "regions", False: "no-regions", None: "regions?"}[c.get("have_region")]
        extra = f", census#{c['census_rank_1395']}" if c.get("census_rank_1395") else ""
        print(
            f"  #{c['rank']:<3} {c['name_fa']} ({c['native_key']}) — {flag}, "
            f"{c.get('discovered_children', '?')} areas{extra}",
            flush=True,
        )
    if excluded and not args.include_no_region and args.rank_by != "census1395":
        print(
            f"  ({len(excluded)} city/cities with haveRegion=false were skipped; "
            "pass --include-no-region to attempt them anyway)",
            flush=True,
        )

    if args.national_only:
        print(
            f"\nnational-only: stopping before per-city downloads.\n"
            f"  ranking   : {out_dir / 'normalized' / 'kilid_national_city_ranking.csv'}\n"
            f"  discovery : {out_dir / 'discovery' / 'national_cities.json'}\n"
            f"  selection : {out_dir / 'discovery' / 'selected_cities.json'}",
            flush=True,
        )
        return 0

    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    total = len(selected)
    for position, city in enumerate(selected, start=1):
        label = slugify_label(city.get("slug"), f"city-{city['city_id']}")
        city_out = out_dir / "cities" / label
        print(f"\n########## city {position}/{total}: {city['name_fa']} (label={label}) ##########", flush=True)
        result = process_city(
            client,
            city_out,
            city_id=city["city_id"],
            label=label,
            city_name=city["name_fa"] or label,
            expected=args.expect_districts,
            args=args,
            selection={
                "mode": selection["mode"],
                "rank_by": args.rank_by,
                "national_rank": city["rank"],
                "stockN": city["stockN"],
                "have_region": city.get("have_region"),
                "province_name_fa": city.get("province_name_fa"),
                "enumeration_file": selection["enumeration_file"],
                "selection_file": "discovery/selected_cities.json",
                "note": (
                    "Ranking is by Kilid stockN (housing stock), not official census population."
                ),
            },
        )
        results.append(
            {
                "rank": city["rank"],
                "city_id": city["city_id"],
                "label": label,
                "name_fa": city["name_fa"],
                "province_name_fa": city.get("province_name_fa"),
                "stockN": city["stockN"],
                "have_region": city.get("have_region"),
                "census_rank_1395": city.get("census_rank_1395"),
                "population_1395": city.get("population_1395"),
                "level": args.child_level,
                "districts_found": result.get("districts_found"),
                "sale_rows": result.get("sale_rows"),
                "rent_rows": result.get("rent_rows"),
                "districts_with_rent": result.get("districts_with_rent"),
                "validation_status": (result.get("validation") or {}).get("status"),
                "exit_code": result["exit_code"],
                "out_dir": str(Path(result["out_dir"]).relative_to(out_dir)),
            }
        )
        if result["exit_code"] != 0:
            errors.append(
                {
                    "stage": "city",
                    "label": label,
                    "city_id": city["city_id"],
                    "exit_code": result["exit_code"],
                }
            )

    national_summary = {
        "generated_at": utc_now_iso(),
        "scraper_version": SCRAPER_VERSION,
        "rank_by": args.rank_by,
        "months_requested": args.months,
        "selection": selection,
        "enumeration_coverage": coverage,
        "cities": results,
        "skipped_no_data": selection["skipped_no_data"],
        "national_reports": build_national_reports(out_dir, results, months=args.months),
        "totals": {
            "cities_selected": len(selected),
            "cities_processed": len(results),
            "districts_total": sum(r["districts_found"] or 0 for r in results),
            "sale_rows_total": sum(r["sale_rows"] or 0 for r in results),
            "rent_rows_total": sum(r["rent_rows"] or 0 for r in results),
            "cities_with_current_rent": sum(1 for r in results if r["districts_with_rent"]),
            "requests": dict(client.counter),
        },
        "errors": errors,
        "exit_code": 0 if not errors else 1,
    }
    write_json(out_dir / "national_summary.json", national_summary)

    print("\n================ national recap ================", flush=True)
    print(f"{'city':<22}{'districts':>10}{'sale rows':>11}{'rent districts':>16}{'validation':>12}", flush=True)
    for row in results:
        print(
            f"{(row['name_fa'] or row['label'])[:21]:<22}{row['districts_found'] or 0:>10}"
            f"{row['sale_rows'] or 0:>11}{row['districts_with_rent'] or 0:>16}"
            f"{(row['validation_status'] or '-'):>12}",
            flush=True,
        )
    print(
        f"\ntotals: {len(results)} cities, {national_summary['totals']['districts_total']} areas, "
        f"{national_summary['totals']['sale_rows_total']} sale rows, "
        f"{national_summary['totals']['cities_with_current_rent']} cities with current rent data",
        flush=True,
    )
    print(
        f"requests: {client.counter['fetched']} fetched, {client.counter['cached']} cached, "
        f"{client.counter['failed']} failed, {client.counter['retries']} retries",
        flush=True,
    )
    print(f"summary: {out_dir / 'national_summary.json'}", flush=True)
    return national_summary["exit_code"]


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kilid_scraper.py",
        description="Download Kilid's public map data (raw archival + normalized convenience CSVs).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 kilid_scraper.py --tehran\n"
            "  python3 kilid_scraper.py --tehran --months 60 --force\n"
            "  python3 kilid_scraper.py --top-cities 10 --rank-by census1395\n"
            "  python3 kilid_scraper.py --top-cities 10 --national-only\n"
            "  python3 kilid_scraper.py --cities 272905,272895\n"
            "  python3 kilid_scraper.py --discover-country\n"
            "  python3 kilid_scraper.py --province 242305\n"
            "  python3 kilid_scraper.py --city 272905\n"
        ),
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--tehran", action="store_true", help="scrape all Tehran municipal districts (cityId 272905)")
    mode.add_argument("--city", metavar="CITY_ID", help="scrape any city by its Kilid cityId")
    mode.add_argument(
        "--top-cities",
        nargs="?",
        const=10,
        type=int,
        metavar="N",
        help="scrape the N largest cities (default 10) by Kilid's own city enumeration",
    )
    mode.add_argument("--cities", metavar="ID,ID,...", help="scrape an explicit list of city ids")
    mode.add_argument("--province", metavar="PROVINCE_ID", help="discovery only: list the cities of a province")
    mode.add_argument("--discover-country", action="store_true", help="save /provinces and report its schema")

    parser.add_argument("--months", type=int, default=DEFAULT_MONTHS, help=f"months of history to request (default {DEFAULT_MONTHS})")
    parser.add_argument("--force", action="store_true", help="refresh: ignore cached raw JSON and re-download")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent / "kilid_data"), help="output directory (default: <script_dir>/kilid_data)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_S, help=f"seconds between requests (default {DEFAULT_DELAY_S})")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help=f"per-request timeout in seconds (default {DEFAULT_TIMEOUT_S:.0f})")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help=f"retries for 429/5xx and network errors (default {DEFAULT_RETRIES})")
    parser.add_argument(
        "--child-level",
        default="MUNICIPAL_AREA",
        choices=["MUNICIPAL_AREA", "CITY"],
        help=(
            "level of the areas to collect for a city (default MUNICIPAL_AREA). "
            "NEIGHBORHOOD is rejected by the API ('childLevel is not a market level')."
        ),
    )
    parser.add_argument(
        "--expect-districts",
        type=int,
        default=None,
        help=f"fail if the discovery count differs (default {TEHRAN_EXPECTED_DISTRICTS} with --tehran, else no check)",
    )
    parser.add_argument("--label", default=None, help="override the label used in file names (e.g. 'tehran')")
    parser.add_argument(
        "--rank-by",
        default="stockN",
        choices=list(RANKING_FIELDS),
        help=(
            "ranking for --top-cities: a Kilid field (stockN/sampleSize/pricePsmMedian) or "
            "census1395 (hand-entered 1395 census population; selection aid only). Default stockN."
        ),
    )
    parser.add_argument(
        "--verify-availability",
        dest="verify_availability",
        action="store_true",
        default=True,
        help="before downloading, check each candidate city exposes areas and substitute the next one (default)",
    )
    parser.add_argument(
        "--no-verify",
        dest="verify_availability",
        action="store_false",
        help="skip the availability check and just take the first N candidates",
    )
    parser.add_argument(
        "--national-only",
        action="store_true",
        help="with --top-cities/--cities: enumerate and select only, do not download per-city data",
    )
    parser.add_argument(
        "--include-no-region",
        action="store_true",
        help="also consider cities whose /provinces record has haveRegion=false",
    )
    parser.add_argument("--quiet", action="store_true", help="less progress output")
    parser.add_argument("--version", action="version", version=f"kilid_scraper {SCRAPER_VERSION}")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.tehran or args.city:
            return run_city(args)
        if args.top_cities is not None or args.cities:
            return run_top_cities(args)
        if args.discover_country:
            return run_discover_country(args)
        return run_province(args)
    except KeyboardInterrupt:
        print("\ninterrupted — cached files are kept; rerun to resume", flush=True)
        return 130


if __name__ == "__main__":
    sys.exit(main())
