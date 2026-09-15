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


def run_city(args: argparse.Namespace) -> int:
    started_monotonic = time.monotonic()
    started_at = utc_now_iso()
    out_dir = Path(args.out).resolve()
    repo_root = Path(__file__).resolve().parent.parent

    if args.tehran:
        city_id = TEHRAN_CITY_ID
        label = "tehran"
        city_name = "Tehran"
        expected: Optional[int] = TEHRAN_EXPECTED_DISTRICTS if args.expect_districts is None else args.expect_districts
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

    errors: List[Dict[str, Any]] = []

    print("\n[1/5] discovery: child areas of the city", flush=True)
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
        return 1

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
        return 2

    print("\n[2/5] per-district raw downloads", flush=True)
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

    print("\n[3/5] normalization (raw JSON -> convenience CSVs)", flush=True)
    sale = normalize_sale_series(out_dir, districts, label)
    rent = normalize_rent(out_dir, districts, label)
    availability = build_availability(out_dir, districts, label)
    normalization = {"sale_series": sale, "rent": rent, "availability": availability}
    print(f"  {sale['file']}  ({sale['rows']} rows)", flush=True)
    print(f"  {rent['file']}  ({rent['rows']} rows)", flush=True)
    print(f"  {availability['file']}  ({availability['rows']} rows)", flush=True)

    print("\n[4/5] validation", flush=True)
    validation = validate(out_dir, districts, expected_count=expected)
    for check in validation["checks"]:
        mark = {"pass": "ok  ", "warn": "WARN", "fail": "FAIL"}[check["status"]]
        print(f"  [{mark}] {check['check']}: {check['detail']}", flush=True)

    print("\n[5/5] reports", flush=True)
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

    return exit_code


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
            "  python3 kilid_scraper.py --discover-country\n"
            "  python3 kilid_scraper.py --province 242305\n"
            "  python3 kilid_scraper.py --city 272905 --child-level NEIGHBORHOOD\n"
        ),
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--tehran", action="store_true", help="scrape all Tehran municipal districts (cityId 272905)")
    mode.add_argument("--city", metavar="CITY_ID", help="scrape any city by its Kilid cityId")
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
        choices=["MUNICIPAL_AREA", "NEIGHBORHOOD", "CITY"],
        help="level of the areas to collect for a city (default MUNICIPAL_AREA)",
    )
    parser.add_argument(
        "--expect-districts",
        type=int,
        default=None,
        help=f"fail if the discovery count differs (default {TEHRAN_EXPECTED_DISTRICTS} with --tehran, else no check)",
    )
    parser.add_argument("--label", default=None, help="override the label used in file names (e.g. 'tehran')")
    parser.add_argument("--quiet", action="store_true", help="less progress output")
    parser.add_argument("--version", action="version", version=f"kilid_scraper {SCRAPER_VERSION}")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.tehran or args.city:
            return run_city(args)
        if args.discover_country:
            return run_discover_country(args)
        return run_province(args)
    except KeyboardInterrupt:
        print("\ninterrupted — cached files are kept; rerun to resume", flush=True)
        return 130


if __name__ == "__main__":
    sys.exit(main())
