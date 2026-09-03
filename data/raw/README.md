# data/raw — vendored raw inputs

These files are **external inputs** to `scripts/build_data.py`, vendored here so that a fresh clone can
reproduce `data/data.js` and `assets/geo/tehran_districts.js` with a single command and no external download.

| File | Source | What it is |
|---|---|---|
| `regions8800.geojson` | Ali Tayebi — «تغییر توان اجاره‌نشینی در تهران» · https://github.com/alitayebi/maps/tree/master/rent (raw file: `rent/data/regions8800.geojson`) | GeoJSON of Tehran's 22 municipal districts; each feature carries quarterly average rent per m² (rials) by quarter key `1..50` (Spring 1388 → Summer 1400), plus `region` id 1–22. Underlying rent data: Iran Statistics Center (مرکز آمار ایران). |
| `infl.json` | Same project (raw file: `rent/data/infl.json`) | Per-quarter wage-calibration factors (Rate1/Rate2) used by the source project to convert income across years; vendored for provenance/reproducibility. |

## Attribution / license note

The data are used for an open, non-commercial data-journalism article. Credit:

> District geometry and quarterly district rents derived from the open project «تغییر توان اجاره‌نشینی در تهران» by Ali Tayebi, which in turn uses Iran Statistics Center rental statistics. See `data/sources.csv` (S1/S4) and the article footer for full citations.

If you redistribute, please retain this note and the source URLs. The exact license of the source repository was not separately recorded; check the upstream repo before commercial reuse.

## Reproduce

```bash
python3 scripts/build_data.py          # reads data/raw/*, writes data/data.js + assets/geo/*
```
