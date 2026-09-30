# Authentic global forecast, climatology and replay assets
Verified 2026-09-30. Public primary sources; no accounts, payment or secrets. Native-grid sampling only, no sparse-city interpolation. The app serves these fields with product-specific provenance and temporal-statistic labels.

## Assets and schema
All `gridCoordinates` are `[latitude,longitude]`; parallel value arrays exactly match coordinate ordering.
- `cfs-global-60days.json`: 4050 global 4° sampled native 1° cells, 60 daily groups. `days[{date, firstSampleHour, lastSampleHour, temperatureC[], precipitationMmDay[]}]`. NOAA CFSv2 initialized 2026-09-29 00Z, **member 01 only**, not an ensemble percentile or probability. Four 6-hourly instantaneous fields averaged per period, hours 6/12/18/24 for day1. mm/day is the average of sampled instantaneous rates, not exact accumulated rain. ~2.7MB JSON. Raw preexisting source GRIB ~28MB reused without downloads.
- `aifs-global-snapshots.json`: 4050 global cells sampled every4° from native0.25°. `frames[{metadata,values[]}]`, 2t temperature °C and tp accumulated precipitation mm, valid hours24/168/336/360, initialized 2026-09-29 12Z. **Snapshots only**, missing lead times must stay unavailable. ECMWF CC BY4.0; attribution required. 238KB. Do not compare cumulative tp directly with daily rates; only matching accumulation windows can be differenced.
- `climatology-global-monthly.json`: 4512 native Gaussian-grid samples; `months[{month:1..12,temperatureC[],precipitationMmDay[]}]`. NOAA NCEP/NCAR R1 monthly long-term means **1991–2020**. Temperature and precipitation separately downloaded from their own source NetCDFs (~2MB total). ~3.8° latitude /3.75°longitude sampled; latitude isn't uniform. Climatology is seasonal context, never a daily forecast or future simulation. Precipitation is model-generated mean rate, not observed rain gauge normals. 664KB JSON.
- `history-2025-09-30.json`:4512 cells, daily `temperatureC[]` and `precipitationMmDay[]`. True daily reanalysis fields, **weather reconstruction, not an archived issued forecast or station observation**. 123KB JSON.

## Reproduce and arbitrary history dates
Use `extract_global.py` with explicit cached GRIB paths and initialization, as described in its CLI docstring. The daily bundle reuses its validated member01 cache for global CFS, avoiding additional CFS downloads.

`server/history.mjs` provides `getHistory(date)` for the bounded `/api/history` route, using small OPeNDAP ASCII responses (~43KB temperature). It validates input, returned dates, shapes, matching grids, and limits upstream to NOAA. No extra dependencies. `parseAscii` tested against NCSS NetCDF values; maximum0.01°C difference from decimal/rounding conventions. It uses only date-derived URLs, not arbitrary URL forwarding. Cache immutable historical results by date, deduplicate concurrent requests and use 30second upstream timeout. Return unavailable on failure; never substitute another date. Network fetch latency observed ~5–10seconds. Request no authentication.

NOAA NCSS and OPeNDAP both tested with an Origin header: HTTP200 **without Access-Control-Allow-Origin**, so direct cross-origin browser fetch is not viable. The app routes these requests through its bounded server handler.

## Sources, terms, limits
- NOAA product and date range: https://psl.noaa.gov/data/gridded/data.ncep.reanalysis.html
- Discontinuation: https://psl.noaa.gov/news/2026/r1datanotice.html
- NOAA data reuse/public-domain guidance and attribution: https://psl.noaa.gov/data/help/index.html
- Climatology directory: https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis/Monthlies/surface_gauss/
- ECMWF attribution/license: https://www.ecmwf.int/en/forecasts/datasets/open-data
- Original source URLs embedded in every JSON.

Global model comparison requires matching valid time, temporal statistic and units. CFS daily four-snapshot mean, AIFS instantaneous 2t and accumulated tp, and reanalysis daily means are distinct. They may appear in separate quick-switch layers with honest labels; do not subtract them as if like-for-like. GFS global grid not newly downloaded in this pass; existing sparse global city GFS is not a global raster. Never show a model with unsupported fields or time range using another model's data. For date beyond forecast horizon, explicitly switch product mode to monthly climate normals; do not quietly extend forecast days.

## Portable daily-refresh integration
Use `extract_global.py` in the existing refresh job after its downloader obtains the latest **complete** official cache. It has no fixed source date or workspace paths, requires only numpy/ecCodes, checks initialization and lead sequence, and atomically replaces output. Temperature/precipitation flags accept one or multiple existing GRIB paths. CFS inputs must be member01; this output deliberately stays single-member. AIFS input list defines available snapshots and must use identical lead times for both variables. Match the existing resolver's run string, never infer availability from the clock. Example:

`python extract_global.py --model cfs --run "$RUN" --temperature "$TMP_CACHE" --precipitation "$PRATE_CACHE" --output public/data/cfs-global-60days.json`

`python extract_global.py --model aifs --run "$AIFS_RUN" --temperature "$T24" "$T168" "$T336" "$T360" --precipitation "$P24" "$P168" "$P336" "$P360" --output public/data/aifs-global-snapshots.json`

Verified against existing cached CFS240fields each variable and AIFS24h pair. The climatology is fixed baseline and needs no daily refresh. Historical dates before termination are fixed and cacheable. No GFS raster was generated; keep its unsupported state explicit rather than painting interpolated city points globally.
