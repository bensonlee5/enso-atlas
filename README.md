# ENSO Atlas

**[Open the live ENSO Atlas →](https://enso-weather-atlas.bensonlee5.chatgpt.site/)**

A weather exploration dashboard that brings a city forecast, a global globe, and longer-range model guidance into one workspace. Compare temperature and precipitation across time horizons while keeping each product's source, initialization, valid period, and limitations visible.

## Screenshots

Live-app captures from October 2, 2026, before the worldwide ensemble update. Globe images show the Canvas2D compatibility view. Click an image to open it full size.

| City forecast | Global temperature field |
| --- | --- |
| [![Boston selected on the globe beside its GFS daily forecast and 16-day temperature trajectory](docs/screenshots/boston-local-forecast.jpg)](docs/screenshots/boston-local-forecast.jpg) | [![CFSv2 global temperature field and contours with Boston selected and a same-time AIFS comparison](docs/screenshots/global-cfs-temperature.jpg)](docs/screenshots/global-cfs-temperature.jpg) |
| Boston's gold location marker, daily high and low, rain, wind, and forecast trajectory. | CFSv2 member 01 sampled temperature field, labeled contours, and model context. |

<details>
<summary>Seven-day briefing</summary>

[![Seven daily Boston forecast cards with highs, lows, rain totals, maximum wind, and a days 8–16 extension](docs/screenshots/seven-day-briefing.jpg)](docs/screenshots/seven-day-briefing.jpg)

A day-by-day GFS briefing with UTC date windows and the longer-range extension kept separate.

</details>

## Explore the atlas

- **Your local outlook:** search a city or five-digit US ZIP code, choose a result, and get a seven-day GFS briefing with a separate days 8–16 extension. Temperature highs/lows, precipitation totals, and maximum wind also appear in a readable table.
- **A shared map and location:** the selected city's gold marker stays on the globe across daily, regional, and global views. Temperature and precipitation are the primary controls; Fahrenheit is the default, with a Celsius toggle.
- **Worldwide maps:** Daily maps open with global CFSv2 temperature fields; Weekly maps show all seven empirical quantiles from a16-member CFSv2 ensemble across both hemispheres and oceans. Regional raw/anomaly products remain explicitly labeled. A named region control moves the camera without replacing the selected weather location.
- **Forecast playback:** play, pause, scrub, change speed or loop the loaded forecast. Exact frames retain every source statistic; smooth display linearly interpolates numeric temperature and sampled precipitation-rate fields at their actual time spacing. AIFS six-hour rainfall totals, cumulative longer-range rain and local daily statistics stay exact.
- **Globe controls:** rotate, zoom, and explore smooth color fields and contours. Independent daylight controls visualize an astronomical instant without changing forecast validity. The WebGL surface has a Canvas2D compatibility fallback.
- **Atmosphere and model lab:** explore GFS pressure-level profiles, the historical calibration pilot, and archived-forecast temperature diagnostics when observations are ready.

The selected location, units, and horizon are remembered in the current browser. **Clear saved city** removes the saved location and its forecast cache and returns to the San Francisco sample. There is no account synchronization or GPS request. City/ZIP searches go to Open-Meteo only on submission; selected coordinates are sent for weather retrieval. ZIP results identify an associated city, not an address or exact postal-area centroid.

## Models and time horizons

| View | Source and coverage | How to read it |
| --- | --- | --- |
| City briefing | NOAA GFS via Open-Meteo, up to 16 days | Daily highs/lows, precipitation totals, and maximum wind; daily windows are UTC |
| Worldwide weekly maps | NOAA CFSv2 16-member lagged ensemble, weeks 1–8 plus separate days 57–60 | Empirical P1/P5/P10/P50/P90/P95/P99 at4,704 native-grid samples (~3.8°); temperature and mean precipitation rate |
| Regional raw outlook | NOAA CFSv2 single member, weeks 1–8 | US-region sampled means, separate from the worldwide ensemble |
| Weekly anomalies | Official NOAA CPC CFSv2 16-member ensemble-mean anomalies, weeks 1–4 | Departures from the product's model climatology; no weeks 5–8 anomaly values or member percentiles |
| Global models | CFSv2 daily sample averages through 60 days; ECMWF AIFS first-week six-hour steps, plus sparse longer-range snapshots at 336 and 360 hours | Sampled native-grid fields; AIFS first-week temperature is instantaneous; rainfall is a six-hour total. Later dates snap to sparse retained snapshots |
| Climate context | NOAA NCEP/NCAR monthly climatology, 1991–2020 | A monthly historical average beyond the selected model horizon, not weather for a future day |
| Historical dates | NOAA NCEP/NCAR Reanalysis 1, supported from 1948-01-01 through 2026-03-17 | Reconstructed weather, not a forecast issued on that date; gaps before current forecasts remain unavailable |

The worldwide ensemble combines members 01–04 from four consecutive 00Z initializations. Older runs are aligned to the same absolute valid times **before** period averaging. P1, P5, P10, P50, P90, P95, and P99 are calculated from the retained member means. The browser loads only map-ready quantiles (under4.5MB uncompressed). The compressed member-means artifact listed in the active storage manifest and its hash retain all member means to six decimals for independent reproduction; the daily pipeline recomputes every quantile before publication. These correlated, uncalibrated samples describe model spread; even P1/P99 do not establish rare-event probabilities or confidence bounds.

### Important interpretation limits

- **Rainfall statistics differ.** CFS precipitation is a mean of sampled instantaneous rates in mm/day-equivalent. AIFS first-week rainfall is differenced into preceding six-hour totals; the longer-range snapshots remain accumulated since initialization. Neither is interchangeable with the GFS daily precipitation total. Cross-model rainfall comparison and CFS rainfall verification are withheld.
- **Smooth maps do not add resolution.** Color fields and contours interpolate within genuine grid cells; missing cells, regional boundaries, and polar caps remain empty. Regional readouts use the nearest sampled point only inside that product's footprint. GFS city points are not interpolated into a global weather field.
- **Model disagreement is not accuracy.** The CFS/AIFS temperature comparison uses matching valid instants, but initialization times and sampled coordinates differ. It is not a skill ranking.
- **The Earth image and lighting are context.** NASA's October 2004 Blue Marble composite is background imagery, not live satellite weather or forecast data. Its archival date stays in the Background imagery attribution and footer. The prominently displayed forecast run comes from the selected model's loaded data, with its valid period shown separately; GFS uses a clearly labeled retrieval time because its API does not supply a model run time. Daylight is astronomical shading; the cloud layer uses GFS hourly city-point values, not a global cloud image.
- **Research is separate from live guidance.** The [calibration pilot](research/pilot/README.md) is a deterministic, no-ENSO experiment for days 15–28 across six broad CONUS regions. Ridge slightly outperformed its small neural model on held-out RMSE. It does not establish local accuracy, weeks 5–8 skill, calibrated probabilities, or a trained ENSO-aware forecast backbone.

This is an exploratory project. Do not use it for safety-critical weather or aviation decisions.

## Forecast playback and temporal interpolation

The playback toolbar is attached to the globe. Location search, model settings, source detail and playback options expand on demand; the selected city stays visible in a compact location row. Atmosphere requires loading the selected city before showing its column. On the weekly ensemble, the adjacent percentile selector offers clearly labeled colder/drier, median and warmer/wetter fields with their exact P1/P5/P10/P50/P90/P95/P99 values. Switching fields pauses while preserving the chosen forecast time. Choose **Percentiles · fixed period** to step through the seven stored percentile fields while holding the source period fixed; at 1× that sweep takes 12 seconds. These marginal gridpoint fields are not coherent storm trajectories or calibrated event odds. Deterministic products provide an explicit route to the weekly ensemble rather than invented percentiles. **Smooth display** is available for gridded temperature and CFS sampled precipitation-rate fields. **Exact frames** works for all loaded forecast products; local playback follows the selected next-seven-days or days-8–16 block. History, climate normals and unavailable sources are not animated. At 1×, the actual source-time span takes 48 seconds. Speed changes scale that duration; a loop holds the last exact frame, then jumps to the first without cross-boundary interpolation.

The display uses a timestamp-weighted convex combination, `(1 − α) × left + α × right`, on scalar values before color mapping. Exact endpoints retain the original arrays. There is no extrapolation, easing of weather time, invented wind advection, optical flow, spline overshoot or additional dynamical skill. Missing values stay missing, nonnegative rate endpoints stay nonnegative, and common weights preserve percentile ordering. Only a single adjacent field pair and its projected samples are cached. Rendering is capped at 12.5 updates/second. Playback preserves the paused contour levels, precision and up-to-320-pixel color raster; only active camera dragging uses its existing smaller raster. Contours follow each native cell’s actual bilinear level curve using an asymptotic saddle decider, then adaptively refine segments to a maximum scalar residual of 2% of the smallest contour interval (capped at 0.02 in the field’s units) and a conservative 0.3-CSS-pixel orthographic chord-error bound. Coordinate topology and one current contour field are cached; numeric buffers bound geometry storage, and conservatively hidden-hemisphere cells are skipped without simplifying visible contours. View buckets include a guard band so camera motion cannot expose culled geometry before the cache refreshes. A safety cap withholds affected fragments with a visible precision warning rather than silently loosening these limits. This does not guarantee device frame rate; slower devices may render fewer times. Bilinear derivatives can still change across native cell edges, so some genuine boundary kinks remain.

- CFS daily frames are rolling 24-hour sampled means, using their explicit interval bounds, including 06Z-to-06Z windows. Weekly frames are period means; the separate days57–60 tail is four days. Playback is paced between period centers, so week8 to the tail is5.5days, not7. Both source windows and the blend fraction are shown for an in-between field. The readout is a display blend of summaries, never an instantaneous forecast.
- CFS ensemble quantiles are blended at the same percentile. This is an interpolated quantile field, not the quantile of a new interpolated member distribution, a physical ensemble-member trajectory, or a newly calibrated probability.
- AIFS first-week temperature retains 29 actual instants from lead0 to168 hours, six hours apart. The globe samples every fourth node of the public0.25° output grid (1° spacing), preserving substantially more spatial detail than the former4° product. Values are compressed as0.1°C/mm integers, adding at most0.05 rounding after GRIB decoding. Smooth display linearly interpolates temperature between adjacent six-hour instants; it cannot reconstruct sub-six-hour dynamics. Beyond the first week the retained legacy snapshots remain sparse, with honest date snapping.
- CFS precipitation-rate blends retain mm/day-equivalent units. They are not converted to rainfall totals and are not claimed to preserve an integral of rainfall across source periods. AIFS first-week precipitation uses28 exact preceding-six-hour totals, obtained by differencing cumulative outputs. Negative differences inside the sum of endpoint GRIB packing-error bounds are zeroed; larger negative differences or invalid endpoints are missing. Missing rainfall is never treated as dry weather. No sub-six-hour timing is invented. Longer-range AIFS cumulative totals and GFS daily totals also remain exact-only. Local highs, lows and maxima are also exact-only because blending them would invent subdaily behavior.
- There is no autoplay. Reduced-motion visitors receive exact frames only. Pause, Escape, source/location/variable/unit/date changes, leaving the forecast view, hiding the page, or replacement of a source run stop active playback. Unit changes preserve the paused time and scalar field. Sunlight remains independently controlled.

The method follows the distinction between point values, means, sums and time bounds in the [CF cell-methods convention](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.12/cf-conventions.html#cell-methods). [ECMWF AIFS documentation](https://www.ecmwf.int/en/forecasts/datasets/aifs-machine-learning-data) describes the native output; this app retains six-hour first-week fields and sparse longer-range snapshots. The [SciPy interpolation guide](https://docs.scipy.org/doc/scipy/tutorial/interpolate/1D.html) explains linear versus higher-order interpolation and overshoot. These references motivate a transparent visualization choice; they do not validate in-between forecasts.

## Run locally

Use **Node.js 22+** for the full app, including historical-date retrieval. There are no runtime npm dependencies or API keys.

```sh
git clone https://github.com/bensonlee5/enso-atlas.git
cd enso-atlas
node scripts/serve.mjs
```

Open **http://localhost:8080**. Set `PORT` to use another port. The server builds the self-contained worker from the checked-in HTML, CSS, JavaScript, and bundled data.

For a static-only preview, Python 3 is enough:

```sh
python -m http.server 8080 --directory dist
```

Open the app over HTTP rather than a file URL. Static hosting supports the dashboard and bundled snapshots, but arbitrary historical-date requests require the `/api/history` server route. `node scripts/build-worker.mjs --forecast-storage` creates `dist/server/index.js` for a Cloudflare-compatible Worker deployment, with live forecast reads supplied by the approved object-storage feed. To run data-dependent tests locally, first restore the hash-verified feed with `python ingestion/publish_forecasts.py restore --data dist/data --state /tmp/enso-feed-state.json`. Generated forecast products are ignored by Git. Building or editing this repository does not itself publish the live site.

## Data freshness and refreshes

- **City forecasts:** fetched on open, cached locally for up to one hour, and refreshed hourly while the page is visible in the daily view. The refresh button requests new GFS data. Retrieval time is not model initialization; the GFS API response does not expose its cycle time.
- **Public model bundle:** the [GitHub Actions workflow](.github/workflows/refresh-weather.yml) checks faster-changing products at **03:17,09:17,15:17 and21:17 UTC**. The **15:17** job alone refreshes the daily CFS ensemble suite. It also runs on ingestion/workflow changes and supports manual dispatch. Validated immutable forecast files are published to object storage with short-lived workflow identity; no forecast products are committed to GitHub. Scheduling can be delayed or skipped by GitHub.
- **Browser updates:** the app checks the object-storage bundle on open and hourly while visible, using a one-hour cache plus schema and SHA-256 validation. Immutable content-addressed files and an atomic latest manifest prevent partial-bundle publication. Failed downloads or validation retain previous data with a warning. Older caches cannot replace a newer loaded run. The app flags CFS ensemble/anomaly runs older than40hours and faster model runs older than24hours while retaining their exact dates and last-good values. GitHub scheduling and upstream availability can delay updates; always inspect the displayed source dates.
- **Bundled fallbacks:** the city forecast and atmosphere snapshots are dated fallbacks, separate from the scheduled seven-product storage bundle. An available page is not proof of a fresh model run.

To reproduce the full ingestion pipeline, use Python 3.12 in an isolated environment and install the dependencies from [ingestion/requirements.txt](ingestion/requirements.txt):

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r ingestion/requirements.txt
python ingestion/refresh_bundle.py
python ingestion/verify_forecasts.py --archive-dir dist/data/archive --output dist/data/verification.json
python ingestion/refresh_bundle.py --manifest-only
node tests/public-data-test.cjs
```

These commands download and validate real upstream products and update local data; they do not publish. The authenticated publisher uploads only verified bytes and atomically promotes a complete bundle. See the storage pipeline instructions for daily/fast modes and bootstrap. The narrower `ingestion/refresh.py` refreshes the raw regional, weekly-anomaly, and observed-ENSO products; it is not the complete bundle entrypoint.

### Archive and verification

Object storage preserves CFS ensemble outlooks for ten sampled locations, not every global field or every searched city. Collection began September 30, 2026; some initial forecasts were captured after their valid periods began. Existing issuance files are not rewritten, and the active index keeps400 issuances. Previous stored objects and release manifests are retained; this version performs no destructive cleanup and does not claim a total-storage cap. Typical new data is approximately21MB/day (about0.6GB/month) if all four faster cycles change; actual usage and platform billing may differ.

Temperature diagnostics wait for completed periods and an observation-latency allowance. They compare forecast P50 with NOAA CPC's `(Tmax + Tmin) / 2` at the nearest observation land-grid point. This is a **proxy diagnostic**: daily windows, sampling, and grids differ. Pending periods have no scores. Daily GFS accuracy is not evaluated by this archive, and the retrospective training pilot is a separate experiment.

## Checks

Run these from the repository root. Python ensemble tests require NumPy from the ingestion requirements; the core research suite skips optional PyTorch checks when PyTorch is absent.

```sh
node --check dist/app.js
for test in app atmosphere-race briefing contours explorer-quality global-grid global-weather globe-renderer public-data public-data-cache smooth-field solar; do
  node "tests/$test-test.cjs" || exit 1
done
node tests/worker-test.mjs
python tests/archive-test.py
python -m unittest discover -s tests -p 'test_*.py' -v
PYTHONPATH=research python -m unittest discover -s research/tests -v
```

The DOM interaction tests require **jsdom as a test-only dependency**. Install it separately and set `JSDOM_MODULE` to its installed module path if it is not on Node's normal module search path:

```sh
node tests/integrated-workspace-test.cjs
node tests/location-search-test.cjs
node tests/location-edge-test.cjs
node tests/global-workspace-regression.cjs
node tests/forecast-storage-test.mjs
node tests/forecast-playback-test.cjs
node tests/forecast-playback-dom-test.cjs
node tests/forecast-playback-raster-test.cjs
node tests/forecast-provenance-test.cjs
node tests/adaptive-contours-test.cjs
node tests/contour-playback-detail-test.cjs
node tests/percentile-playback-test.cjs
node tests/aifs-fine-test.cjs
node tests/exploration-layout-test.cjs
```

These tests do not replace visual browser testing. The optional `python tests/gpu-egl-validation.py` requires EGL/Mesa and Pillow and validates the production shaders offscreen; it is not a browser/device frame-rate benchmark.

## Repository guide

- [dist/](dist/): browser app, bundled datasets, and provenance metadata
- [server/](server/) and [scripts/](scripts/): bounded historical-data endpoint, local server, and worker builder
- [ingestion/](ingestion/): reproducible retrieval, validation, archive, and verification code
- [Ensemble methodology](ingestion/ensemble/README.md) and [global products](ingestion/global/README.md): source formats, sampling, and scientific caveats; dated examples describe their recorded runs
- [research/](research/README.md), [model card](research/MODEL_CARD.md), and [completed pilot](research/pilot/README.md): experimental calibration and evaluation
- [tests/](tests/): product validation, interaction, rendering, and verification checks

## Sources and terms

Forecast values retain source URLs, valid periods, and processing details in their JSON assets and the app's source panels.

- **NOAA / Open-Meteo:** [GFS API](https://open-meteo.com/en/docs/gfs-api), [CPC weekly CFSv2 products](https://www.cpc.ncep.noaa.gov/products/CFSv2/weekly/), [observed ENSO indices](https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for), and [NOAA PSL datasets](https://psl.noaa.gov/data/gridded/)
- **Open-Meteo / GeoNames:** city geocoding and weather data require attribution. The free Open-Meteo service is for noncommercial use and has request limits; review its [terms and privacy](https://open-meteo.com/en/terms) and [pricing](https://open-meteo.com/en/pricing) before commercial or high-traffic deployment
- **ECMWF AIFS:** [ECMWF Open Data](https://www.ecmwf.int/en/forecasts/datasets/open-data), with CC BY 4.0 attribution
- **Map context:** [Natural Earth boundaries via geo-countries](https://github.com/datasets/geo-countries) and [NASA Blue Marble Next Generation](https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/); displayed boundaries do not imply endorsement of territorial claims
- **Pilot dataset:** Microsoft's [SubseasonalClimateUSA](https://github.com/microsoft/subseasonal_data), CC BY 4.0, with derived-data processing documented in the pilot

## Forecast writer security

The public Site serves forecast data read-only. Uploads require a short-lived, signed GitHub Actions OIDC token scoped to this exact repository ID, owner ID, main branch, workflow path, event allowlist and Site audience. Forks, pull-request events, unexpected caller contexts and expired/forged tokens are rejected. No long-lived storage API key is stored in GitHub.

The dependency-installing NOAA prepare job has no upload identity; the separate standard-library publisher obtains it only after validating this run’s transferred bytes. The Worker checks bounded filenames, payload hashes, complete product schemas, archive references, run chronology and per-source initialization monotonicity. Promotion is conditional on the exact previous manifest ETag. Failed or conflicting uploads leave the last good bundle visible.

The dedicated storage binding and narrowly scoped workflow trust were explicitly approved and activated on October 2, 2026. The first real [Actions upload and atomic manifest readback](https://github.com/bensonlee5/enso-atlas/actions/runs/37057524698) passed before the worldwide frontend switched to storage. Existing historical GitHub data remains in Git history; current generated forecasts are no longer committed.
