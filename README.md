# ENSO Atlas
A source-honest weather exploration dashboard. A canvas globe plots actual city forecasts, not interpolated or illustrative weather fields. NOAA GFS daily temperature, precipitation and wind via Open-Meteo cover up to 16 days. Long-range guidance and experimental calibration are explicitly separated.

## Run
`python -m http.server 8080 --directory dist`

No build dependencies, API keys, subscriptions or paid services are required. Open index through HTTP rather than a file URL. Forecasts refresh when opened and cache locally for one hour; the refresh button requests new data. A dated source snapshot remains available if the API fails. Retrieval time is not forecast initialization; the GFS API does not expose cycle time.

## Data and terms
- Weather: NOAA GFS via https://open-meteo.com/en/docs/gfs-api ; attribution is shown in app. Open-Meteo free API is for non-commercial use and subject to their rate limits/terms. A monetized or high-traffic deployment requires reviewing https://open-meteo.com/en/terms and choosing an approved service. No purchase made.
- Geographic boundaries: Natural Earth, downloaded from datasets/geo-countries, simplified for display. https://github.com/datasets/geo-countries ; boundaries do not imply endorsement of territorial claims.
- ENSO context: dated NOAA CPC September 10, 2026 advisory. https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml
- All daily forecast dates are UTC. A deterministic run does not provide a calibrated confidence interval.

## Research
See `research/` for reproducible calibration and data preparation. No trained backbone or measured skill is claimed until an actual run is evaluated on independent data. Do not use for safety-critical decisions.

## Deployment
The static directory is portable to ordinary static hosting. The public source is portable and excludes private deployment configuration. Public GitHub source and website access are separate.

## Long-range products
The app includes real 8-week (56-day) aggregates from 60 days of NOAA CFSv2 member01, initialized 2026-09-29 00Z, plus official CPC 16-member weekly ensemble anomalies for weeks1–4, initial date2026-09-28. Select **Weeks1–8**, then product/field/week. There is no invented weeks5–8 ensemble anomaly. Raw precipitation is a mean instantaneous rate in mm/day-equivalent, never a verified accumulation or event probability. These long-range products are dated snapshots; they do not auto-refresh on page open. `ingestion/` contains exact reproducible recipes. Watch the listed run date and re-ingest a verified complete run to update.

The calibration model and honest evaluation scaffold are in `research/`. A completed real no-ENSO calibration pilot, paired dataset, small neural weights and six-model held-out results are in `research/pilot/`. It covers days15–28 only; the ENSO-conditioned PyTorch scaffold remains unrun. See the pilot README for measured results and limits.

## Validated refresh entrypoint
Install `ingestion/requirements.txt` from PyPI in an isolated environment, then run `python ingestion/refresh.py`. The resolver checks official indexes for the newest complete paired CFS 60-day run, extracts native-grid samples, discovers latest weekly anomaly files, reads CF time metadata, and refreshes observed ENSO. All products validate before any JSON is replaced. Individual writes are atomic; publish the complete source only after successful exit. If any source is missing, stale, malformed, or changes temporal statistics, the command fails and the previous published Site must remain unchanged. No accounts/keys are required.

This command updates local source, not a running website. Hosting publication or a separately configured daily update task is required. The browser does not claim that a scheduled update has run.

## Checks
`node --check dist/app.js`
`node tests/app-test.cjs`
`PYTHONPATH=research python -m unittest discover -s research/tests -v`

Desktop live UI tested with GFS refresh and CFS raw/anomaly switching. Responsive CSS is implemented; an actual mobile-browser viewport test was unavailable in the build environment.

## Model lab
The live Model lab displays genuine test-set RMSE for raw CFSv2, seasonal climatology, region bias correction, ridge, a686-parameter neural residual model and lagged observations. The retrospective pilot used six broad CONUS regions and a single temporal split; ridge slightly beat the neural model overall. This is not evidence of calibrated probabilities, weeks5–8 skill, local California skill or global-backbone fine-tuning. Dataset credit: SubseasonalClimateUSA, CC BY4.0.

## Interaction
The °C/°F toggle converts absolute temperature and differences correctly (anomalies/RMSE use scale only). Globe zoom supports buttons, wheel, pinch and reset, bounded65–270%. Percentiles require real member distributions; unsupported products display an unavailable selector rather than invented P10/P50/P90.

## Real ensemble percentiles
The4-member ensemble product uses same-cycle CFSv2 members01–04 from Sep29,2026 00Z. Select temperature or precipitation rate and P10/P50/P90. Quantiles use linear interpolation across the4 member temporal averages, with all8 source GRIB hashes in the JSON. The small, dependent ensemble provides uncalibrated model spread, not confidence bounds. Weeks1–8 cover56days; a separate Days57–60 window covers the remaining4days. `ingestion/ensemble/retrieve_ensemble.py --run YYYYMMDD00 --days 60` reproduces the product; see its README. This ensemble snapshot has its own run timestamp and is not changed by the GFS refresh button or the nonensemble refresh command.

## Day/night, cloud cover and atmospheric columns
Globe illumination uses approximate solar declination and UTC solar longitude at the selected forecast date/hour; for weekly products it uses the period midpoint. It is astronomical shading, not cloud imagery or a weather model. Daily high and daily low temperature remain daily statistics. The cloud layer plots real GFS hourly total cloud-cover percentages at city points and the selected UTC hour; it is not invented as a global cloud texture or long-range cloud forecast.

The Atmosphere view fetches29 actual GFS pressure levels above user-selected coordinates. It samples at a requested geopotential altitude ASL using reported heights, not a fixed lapse rate. Temperature/humidity interpolate linearly and wind uses vectors. Levels at/below returned model terrain, missing intermediate brackets, and out-of-range altitude/time are withheld. Model terrain is coarse and not a high-resolution DEM. Default San Francisco snapshot is dated; loading other coordinates retrieves live source data. Initialization time is not supplied by this API. This profile is not a safety-critical aviation product.
