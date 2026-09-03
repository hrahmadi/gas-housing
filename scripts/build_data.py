#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build script for the Gas–Housing interactive article.

Reads:
  - data/annual.csv, data/periphery.csv, data/sources.csv, data/assumptions.json
  - <SOURCE_GEOJSON>  (Ali Tayebi Tehran 22-district rent GeoJSON, downloaded externally)

Writes:
  - data/tehran_rent_district.csv   (long format, quarterly, per district)
  - data/data.js                    (single structured JS blob: `window.ARTICLE_DATA = ...`)
  - assets/geo/tehran_districts.js  (simplified, projected district geometry for the map)

Usage:
  python3 scripts/build_data.py <SOURCE_GEOJSON> [<INFL_JSON>]
"""
import csv, json, math, sys, os

GEO = sys.argv[1] if len(sys.argv) > 1 else "/tmp/regions8800.geojson"
INFL = sys.argv[2] if len(sys.argv) > 2 else "/tmp/infl.json"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LAT0 = 35.72          # projection reference latitude (deg)
LON0 = 51.32          # projection reference longitude (deg)
M_PER_DEG = 111320.0
TOL = 45.0            # simplification tolerance in meters
TARGET_W = 1000.0     # normalized map width (viewBox units)

# ----------------------------------------------------------------------------
# 1. Geometry helpers
# ----------------------------------------------------------------------------
def project(lon, lat):
    x = (lon - LON0) * M_PER_DEG * math.cos(math.radians(LAT0))
    y = (LAT0 - lat) * M_PER_DEG
    return (x, y)

def perp_dist(p, a, b):
    """Distance from point p to segment ab (meters)."""
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)

def dp_simplify(pts, tol):
    """Douglas–Peucker on a closed ring (assumes pts[0]==pts[-1])."""
    if len(pts) < 4:
        return pts
    # work on the ring without the closing point, then re-close
    ring = pts[:-1]
    if len(ring) < 3:
        return pts
    stack = [(0, len(ring) - 1)]
    keep = [False] * len(ring)
    keep[0] = keep[-1] = True
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        dmax, idx = -1.0, i
        for k in range(i + 1, j):
            d = perp_dist(ring[k], ring[i], ring[j])
            if d > dmax:
                dmax, idx = d, k
        if dmax > tol:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    out = [p for p, k in zip(ring, keep) if k]
    if len(out) < 3:
        return pts
    out.append(out[0])
    return out

def simplify_ring(ring, tol):
    # ring: list of [lon, lat]
    proj = [project(pt[0], pt[1]) for pt in ring]
    # decimate consecutive duplicates
    dec = [proj[0]]
    for p in proj[1:]:
        if math.hypot(p[0]-dec[-1][0], p[1]-dec[-1][1]) > 1e-6:
            dec.append(p)
    if len(dec) >= 2 and math.hypot(dec[0][0]-dec[-1][0], dec[0][1]-dec[-1][1]) < 1e-6:
        dec.pop()
    dec.append(dec[0])
    simp = dp_simplify(dec, tol)
    return simp

# ----------------------------------------------------------------------------
# 2. Load source files
# ----------------------------------------------------------------------------
with open(GEO, encoding="utf-8") as f:
    geo = json.load(f)

with open(INFL, encoding="utf-8") as f:
    infl = json.load(f)["infl"]

def read_csv(name):
    p = os.path.join(ROOT, "data", name)
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))

annual_rows = read_csv("annual.csv")
periphery_rows = read_csv("periphery.csv")
sources_rows = read_csv("sources.csv")

with open(os.path.join(ROOT, "data", "assumptions.json"), encoding="utf-8") as f:
    assumptions = json.load(f)

# ----------------------------------------------------------------------------
# 3. Quarter metadata
# ----------------------------------------------------------------------------
quarters = []
for i, q in enumerate(infl, start=1):
    quarters.append({"q": i, "label": q["Time"]})
# q -> (year, season_index 0..3)
def quarter_meta(q):
    # q=1 -> بهار 1388
    idx = q - 1
    year = 1388 + idx // 4
    season = idx % 4
    names = ["بهار", "تابستان", "پاییز", "زمستان"]
    return year, season, names[season]

# ----------------------------------------------------------------------------
# 4. Build district records + long CSV
# ----------------------------------------------------------------------------
districts = []
rent_long = []
for feat in geo["features"]:
    props = feat["properties"]
    reg = int(props["region"])
    # geometry rings
    geom = feat["geometry"]
    rings_raw = []
    if geom["type"] == "Polygon":
        rings_raw = geom["coordinates"]
    else:  # MultiPolygon
        for poly in geom["coordinates"]:
            rings_raw.extend(poly)
    rings = []
    for ring in rings_raw:
        s = simplify_ring(ring, TOL)
        if len(s) >= 4:
            rings.append(s)

    rent = {}
    for q in range(1, 51):
        raw = props.get(str(q), "-")
        if raw == "-" or raw is None or raw == "":
            rent[q] = None
        else:
            rent[q] = float(raw)  # rials per m2
            year, season, _ = quarter_meta(q)
            rent_long.append({
                "region": reg, "q": q, "jalali_year": year,
                "season": season, "season_label": _,
                "rent_toman_m2": round(rent[q] / 10.0, 1),
                "rent_rial_m2": round(rent[q], 0),
            })

    districts.append({"region": reg, "rent": rent, "rings": rings})

# sort by region
districts.sort(key=lambda d: d["region"])

# write long CSV
with open(os.path.join(ROOT, "data", "tehran_rent_district.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["region", "q", "jalali_year", "season", "season_label", "rent_toman_m2", "rent_rial_m2"])
    for r in sorted(rent_long, key=lambda r: (r["region"], r["q"])):
        w.writerow([r["region"], r["q"], r["jalali_year"], r["season"], r["season_label"],
                    r["rent_toman_m2"], r["rent_rial_m2"]])

# ----------------------------------------------------------------------------
# 5. Project / normalize geometry into 0..TARGET_W coordinate space
# ----------------------------------------------------------------------------
allx = [p[0] for d in districts for ring in d["rings"] for p in ring]
ally = [p[1] for d in districts for ring in d["rings"] for p in ring]
minx, maxx = min(allx), max(allx)
miny, maxy = min(ally), max(ally)
scale = TARGET_W / (maxx - minx)
H = (maxy - miny) * scale

def norm(p):
    return (round((p[0] - minx) * scale, 2), round(H - (p[1] - miny) * scale, 2))

geo_out = []
for d in districts:
    rings = [[norm(p) for p in ring] for ring in d["rings"]]
    geo_out.append({"region": d["region"], "rings": rings})

with open(os.path.join(ROOT, "assets", "geo", "tehran_districts.js"), "w", encoding="utf-8") as f:
    f.write("// Generated by scripts/build_data.py — simplified & projected Tehran 22-district geometry.\n")
    f.write("// Coordinates normalized to a 0..1000 wide viewBox (height %.1f).\n" % H)
    f.write("window.TEHRAN_GEO = {\"height\": %.2f, \"districts\": %s};\n" % (H, json.dumps(geo_out, ensure_ascii=False)))

# ----------------------------------------------------------------------------
# 6. Build the article data blob
# ----------------------------------------------------------------------------
def series(var):
    out = {}
    for row in annual_rows:
        if row["variable"] == var:
            out[int(row["year"])] = float(row["value"])
    return out

annual = {
    "gasoline": series("gasoline"),
    "house_price": series("house_price"),
    "min_wage": series("min_wage"),
    "tehran_rent": series("tehran_rent"),
    "unit": {
        "gasoline": "million_liter_per_day",
        "house_price": "million_toman_per_m2",
        "min_wage": "rial_per_month",
        "tehran_rent": "toman_per_m2",
    },
}

# per-district annual average rent (toman/m2), averaged over quarters present
district_annual = {}
for dist in districts:
    reg = dist["region"]
    year_sum = {}
    year_cnt = {}
    for q, val in dist["rent"].items():
        if val is None:
            continue
        year, season, _ = quarter_meta(q)
        year_sum[year] = year_sum.get(year, 0.0) + val / 10.0
        year_cnt[year] = year_cnt.get(year, 0) + 1
    district_annual[reg] = {
        year: round(year_sum[year] / year_cnt[year], 1)
        for year in sorted(year_sum)
    }

periphery = {}
for row in periphery_rows:
    key = (row["name"], row["metric"])
    periphery.setdefault(row["name"], {})[row["metric"]] = {
        "value": float(row["value"]) if row["value"] else None,
        "unit": row["unit"],
        "source_id": row["source_id"],
        "confidence": row["confidence"],
    }

district_names = {
    1: "منطقه ۱", 2: "منطقه ۲", 3: "منطقه ۳", 4: "منطقه ۴", 5: "منطقه ۵",
    6: "منطقه ۶", 7: "منطقه ۷", 8: "منطقه ۸", 9: "منطقه ۹", 10: "منطقه ۱۰",
    11: "منطقه ۱۱", 12: "منطقه ۱۲", 13: "منطقه ۱۳", 14: "منطقه ۱۴", 15: "منطقه ۱۵",
    16: "منطقه ۱۶", 17: "منطقه ۱۷", 18: "منطقه ۱۸", 19: "منطقه ۱۹", 20: "منطقه ۲۰",
    21: "منطقه ۲۱", 22: "منطقه ۲۲",
}

data = {
    "meta": {
        "title": "بنزین، مسکن و نابرابری فضایی در ایران",
        "built": "2026-09-03",
        "version": "0.1",
    },
    "annual": annual,
    "district_annual_rent": {str(k): v for k, v in district_annual.items()},
    "district_names": {str(k): v for k, v in district_names.items()},
    "periphery": periphery,
    "sources": {r["source_id"]: r for r in sources_rows},
    "assumptions": assumptions,
    "quarters": quarters,
    "series_status": {
        "gasoline": "OBSERVED",
        "house_price": "OBSERVED",
        "min_wage": "OBSERVED",
        "tehran_rent": "OBSERVED",
        "district_annual_rent": "OBSERVED",
        "periphery": "OBSERVED",
    },
}

with open(os.path.join(ROOT, "data", "data.js"), "w", encoding="utf-8") as f:
    f.write("// Generated by scripts/build_data.py from data/*.csv + data/assumptions.json\n")
    f.write("// Do not edit by hand — edit the CSVs and re-run the build script.\n")
    f.write("window.ARTICLE_DATA = ")
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")

print("Wrote data/tehran_rent_district.csv (%d rows)" % len(rent_long))
print("Wrote data/data.js")
print("Wrote assets/geo/tehran_districts.js (height %.1f units, %d districts)" % (H, len(districts)))
print("District annual rent coverage:")
for d in sorted(district_annual, key=lambda r: (len(district_annual[r]), r)):
    pass
yrs = sorted({y for v in district_annual.values() for y in v})
print("  years with any data:", yrs)
