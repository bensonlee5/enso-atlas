# ENSO Atlas
A source-honest weather exploration dashboard. A GPU-shaded globe plots actual city forecasts, not interpolated or illustrative weather fields. NOAA GFS daily temperature, precipitation and wind via Open-Meteo cover up to 16 days. Long-range guidance and experimental calibration are explicitly separated.

## Run
`python -m http.server 8080 --directory dist`

Node.js 22+ and Python are sufficient; no npm dependencies, API keys, subscriptions or paid services are required. Open index through HTTP rather than a file URL. Forecasts refresh when opened and cache locally for one hour; the refresh button requests new data. A dated source snapshot remains available if the API fails. Retrieval time is not forecast initialization; the GFS API does not expose cycle time.

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
The app includes real 8-week (56-day) aggregates from 60 days of NOAA CFSv2 member01, initialized 2026-09-29 00Z, plus official CPC 16-member weekly ensemble anomalies for weeks1–4, initial date2026-09-28. Select **Weeks1–8**, then product/field/week. There is no invented weeks5–8 ensemble anomaly. Raw precipitation is a mean instantaneous rate in mm/day-equivalent, never a verified accumulation or event probability. Bundled snapshots are fallbacks; the daily GitHub workflow refreshes the public data feed. The page checks that feed on open and hourly while visible, with hash validation. `ingestion/` contains reproducible recipes. Always watch the listed initialization date.

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
The4-member ensemble product uses same-cycle CFSv2 members01–04 from Sep29,2026 00Z. Select temperature or precipitation rate and P10/P50/P90. Quantiles use linear interpolation across the4 member temporal averages, with all8 source GRIB hashes in the JSON. The small, dependent ensemble provides uncalibrated model spread, not confidence bounds. Weeks1–8 cover56days; a separate Days57–60 window covers the remaining4days. `ingestion/ensemble/retrieve_ensemble.py --run YYYYMMDD00 --days 60` reproduces the product; see its README. This ensemble has its own run timestamp and is refreshed with the daily public bundle. The GFS refresh button updates the shorter-range point forecast separately.

## Day/night, cloud cover and atmospheric columns
Globe illumination uses approximate solar declination and UTC solar longitude at the selected forecast date/hour; for weekly products it uses the period midpoint. It is astronomical shading, not cloud imagery or a weather model. Daily high and daily low temperature remain daily statistics. The cloud layer plots real GFS hourly total cloud-cover percentages at city points and the selected UTC hour; it is not invented as a global cloud texture or long-range cloud forecast.

The Atmosphere view fetches29 actual GFS pressure levels above user-selected coordinates. It samples at a requested geopotential altitude ASL using reported heights, not a fixed lapse rate. Temperature/humidity interpolate linearly and wind uses vectors. Levels at/below returned model terrain, missing intermediate brackets, and out-of-range altitude/time are withheld. Model terrain is coarse and not a high-resolution DEM. Default San Francisco snapshot is dated; loading other coordinates retrieves live source data. Initialization time is not supplied by this API. This profile is not a safety-critical aviation product.

## Movable sunlight and isolines
The independent sunlight slider moves the astronomical day/night boundary in15-minute UTC steps; Play animates it. It does not change forecast values or the separately selected cloud hour. For weekly guidance, shading uses the selected period's midpoint date and chosen sunlight hour.

CFSv2 maps support Points, Contours, or Both. Isotherms and constant precipitation-rate contours use marching squares with linear interpolation only inside the real sampled rectilinear grid (raw/4-member products14×31, published anomalies11×24). They do not add model resolution. Missing cells, large grid gaps and the data boundary are not extrapolated; projected back-side segments are suppressed. Labels follow °C/°F, including anomaly scaling, and mm/day-equivalent rates; these are not accumulated-rainfall isohyets. The GFS city-point view explicitly disables contours rather than fitting a fictitious spatial field.

`node tests/contours-test.cjs` validates planar/missing/constant fields and authentic ensemble bounds.

### Daily refresh and observed deviations

The scheduled GitHub workflow runs at 09:17 UTC daily (GitHub scheduling is best-effort). It uses the public repository's standard Linux runner, no paid GPU and no external credentials. Only its job-scoped `GITHUB_TOKEN` has `contents: write`; the commit allowlist is limited to validated forecast JSON, issuance archives and verification output. A 25-minute timeout and concurrency group bound execution. The site checks the public repository hourly while open, validates hashes and schemas, and retains previous data if validation fails. Source timestamps remain visible; a scheduled job is not a freshness guarantee. GitHub may disable inactive scheduled workflows after 60 days.

Before replacement, both the previous and new CFS ensemble issuance are archived immutably for the ten displayed sampled locations, including quantiles and exact valid intervals. The active index keeps 400 issuances; older small files stay available. This archives the location outlooks, not every global-grid field. A rerun never rewrites an existing issuance. Collection began September 30, 2026; the initial September 29 forecast was captured after initialization, so this is not an operational issue-time archive from that earlier date.

The observation check waits for completed target periods and a source-latency allowance. Temperature verification compares P50 with NOAA CPC's mean of daily Tmax/Tmin at the nearest observation land-grid point, explicitly a diagnostic proxy for the forecast's mean of six-hourly samples. Spatial and daily-window differences remain. Precipitation verification is withheld because the displayed sampled instantaneous rate is not an accumulated rainfall forecast. Pending cases have no invented error metrics. This live archive is separate from the historical training pilot.


### Global models, climate averages and historical dates

The Global models / history view switches between genuine sampled native global CFSv2 and ECMWF AIFS fields. CFS exposes daily averages of four six-hour instantaneous samples through60days. AIFS exposes actual24/168/336/360-hour snapshots; selecting another in-range date explicitly snaps to the nearest available snapshot. Their initialization times and temporal statistics remain visible. CFS precipitation is an instantaneous-rate sample mean; AIFS precipitation is accumulated since initialization. They must not be compared as equal rainfall statistics. These deterministic global fields do not provide ensemble percentiles; the existing CONUS ensemble remains separate.

Automatic date selection uses a1991–2020 monthly NOAA NCEP/NCAR climatology beyond the selected model horizon. This is a historical monthly climate average, not weather for the chosen future day and not a projection of climate change. Historical dates use real NCEP/NCAR Reanalysis1 daily grids from1948-01-01 through2026-03-17. This product ended in March2026. Dates in the gap before current forecast initialization are explicitly unavailable. Reanalysis reconstructs conditions from observations and a model; it is distinct from a forecast issued at that time and from the immutable issued-forecast archive.

The public `/api/history?date=YYYY-MM-DD` route fetches only the two fixed official NOAA temperature/precipitation datasets. Strict date bounds, response-size caps, timeouts, limited concurrency and bounded caching protect the upstream and runtime. No credentials or arbitrary URL proxy are provided. `node scripts/build-worker.mjs` creates a self-contained Cloudflare-compatible Worker while preserving the plain HTML/JS app. `node scripts/serve.mjs` runs the same handler locally, including historical retrieval.


### Explorer usability and matched-time comparison

The control dock now precedes the map. Product banners distinguish forecasts, historical reconstruction, climate averages and unavailable fields. Every failed/loading state clears stale legends and source links; source-update failures retain dated data with a visible warning. Phone layouts use readable source text and generous targets. Touch scrolling stays available over the globe until Explore globe is selected; keyboard arrows pan, +/- zoom and0resets.

A temperature comparison uses actual instantaneous CFS member01 samples at the exact AIFS valid timestamp. Both are2m temperature in the chosen units, with distinct initialization and native sample coordinates disclosed. The difference is model disagreement, never an accuracy score or confidence interval. The map retains its selected daily/instantaneous statistic. Rainfall comparison is withheld because CFS sampled rates and AIFS accumulation differ. The existing daily job extracts these matching CFS fields from its downloaded cache, without extra CFS network traffic.

## Mobile daylight controls
The city picker includes Palo Alto (37.4419, -122.143), with its own GFS request and the returned model coordinate disclosed. The standalone 13-city `forecast.json` fallback is not part of the daily seven-product NOAA/GitHub bundle; GFS refreshes on page open and on demand.

The visible Daylight card controls an independent astronomical instant. Choose a date, time and UTC or Pacific time; changing timezone preserves the instant. Now resets to the current instant, Play advances in 15-minute steps across midnight, and Use forecast date selects noon UTC on the daily date or long-range midpoint. Weather validity does not change. Nonexistent and ambiguous Pacific DST times require a different time or explicit UTC. Solar declination and equation of time use the approximate NOAA equations at https://gml.noaa.gov/grad/solcalc/solareqns.PDF for visualization.

## GPU rendering pass (October 2026)
The planet uses a dependency-free WebGL fragment renderer with a smooth astronomical terminator, ocean reflectance and a thin atmospheric limb. Geographic labels and actual sampled weather points/isolines remain an independent Canvas2D scientific overlay. No weather interpolation, model fields, or source timestamps are changed by the surface renderer. WebGL failure/context loss falls back to the existing compatibility globe. Camera selection uses short great-longitude-path easing; reduced-motion preferences skip that animation. Rendering is on demand, pixel ratio is capped at 1.5, and animations stop when the document is hidden.

Basemap: NASA Earth Observatory, Blue Marble Next Generation, October **2004** cloud-free composite (2048×1024 derivative). This is historical reference surface imagery, **not current satellite weather**, cloud observations, or a forecast. Terrain appearance comes from the source composite; the renderer adds no elevation forecast or synthetic clouds. Source: https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/ ; original https://assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/bmng-base/october/world.200410.3x5400x2700.jpg .

The forecast timeline sits below the globe. On small screens, Location details opens the current point's full readout; independent sunlight date/time controls are collapsible. All model/historical/climatology labels and uncertainty caveats remain.

Renderer QA: `node tests/globe-renderer-test.cjs` checks setup/fallback/projection. Optional `python tests/gpu-egl-validation.py` compiles and links the exact production GLSL ES shaders in an independent Mesa EGL context, renders the actual NASA asset offscreen, and saves `/tmp/enso-gpu-shader-validation.png`. It requires system EGL/Mesa and Pillow. Its software-render microbenchmark is not browser/device frame rate.
