# Genuine CFSv2 member percentiles for ENSO Atlas

## Output
`cfs-weekly-ensemble-percentiles.json` supplies genuine empirical P10/P50/P90 temperature and precipitation-rate quantiles at the same434 native sampled grid coordinates as the previous app data. Initialization2026-09-29 00Z, same-cycle members01,02,03,04. Not a lagged ensemble. There are8 full weeks (56days), plus `remainingDays57to60` for the separate last4days. Never call that partial interval a full ninth week.

The raw source contains240 six-hourly frames per member and variable through hour1440. Each forecast valid time and initialization is checked during decoding. Weekly28-frame averages are computed separately for every member, then NumPy `quantile(..., method='linear')` (Hyndman–Fan type7) is computed across the four member averages. No daily quantiles are averaged, and no member is presented as the median. P50 is the mean of the two central sorted members. P10=0.7×minimum+0.3×second-lowest, P90=0.3×second-highest+0.7×maximum.

These4 related forecasts share a model and are not independent calibrated outcomes. Tail percentiles are particularly unstable with so few members. They are empirical model quantiles, not confidence intervals or statements of a10%/90% event probability. There is no climatological bias correction, hindcast calibration, downscaling, or spatial interpolation.

## Units and temporal meaning
Temperature is instantaneous2m air temperature inK, converted to°C before averaging. Source precipitation is `PRATE`, units`kg m**-2 s**-1`, GRIB `stepType=instant`, product template0, `startStep=endStep`. Multiply by86400 to express sampled rates inmm/day. The output is the mean sampled instantaneous precipitation rate. It is NOT a verified accumulated total; do not multiply by7 and label it a forecast weekly rainfall accumulation without additional justification. Although the NOAA filename says`daily`, the index and GRIB metadata verify six-hourly records.

Period boundaries are nominal start/end dates. Samples are at the right endpoints: week1 hours6 through168 inclusive; week2 hours174 through336, etc. `intervalEndExclusive` preserves the app's interval-label convention, while `firstSampleHour` and `lastSampleHour` are the authoritative sample coverage. The final sample is exactly at the labelled interval end.

The434 points are a rectangular CONUS-area sample (latitudes24–50, longitudes−126 to−66, native nearest coordinates), including neighboring ocean/countries. Land-only display requires a geographic mask. `sampledLocations` contains the previous app's nearest-grid city lookup indices, not local observations.

## Provenance and reproducibility
Each source URL, SHA256, byte count, frame count and first/last GRIB metadata is embedded in JSON. Official ensemble design is described in AppendixC of [NCEP's CFSv2 paper](https://cfs.ncep.noaa.gov/cfsv2.info/CFSv2_paper.pdf):00Z includes one long control plus three seasonal perturbed forecasts. Other cycles' perturbed members have only45days; do not switch cycle and silently promise60days.

Run:
`python retrieve_ensemble.py --run 2026092900 --days 60`

Install official PyPI `eccodes` and `numpy` in your environment, or optionally set `ECCODES_PYTHON_PATH` to an existing local installation. No paid service or credentials are used. It checks HTTP206 byte-range responses and file lengths; downloads only the first240 GRIB messages of each source. Existing exact files are reused. It fails rather than changing member set or fabricating missing data.

For a refresh, `--run latest` discovers a complete four-member 00Z suite from the [NOAA rotating archive](https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/); archive retention is short, so preserve dated data. The repository workflow calls this script daily at 09:17 UTC after resolving a complete suite. You can also pass an explicit historical run while NOAA still retains it.

## Measured cost and QA
This retrieval completed in30.4seconds with28MB of existing exact member01 data reused;84MB downloaded. All8 source subsets total112,242,142bytes. Output JSON167,888bytes. This is local CPU processing, no paid compute/services. Fresh-run wall time depends on NOAA/network throughput; budget several minutes rather than assuming the observed cached timing. Native GRIB reading dominates work; publishing the167KB processed JSON is cheap. Runtime defaults to two decoding workers.

QA checked all23,436 values across9periods×2variables×3quantiles×434points are finite, P10≤P50≤P90 everywhere, and precipitation nonnegative. All8 source files have distinct SHA256 hashes. There are240 complete aligned forecast frames per source. Member forecasts differ; example week1 San Francisco nearest-grid temperature P10/P50/P90=21.645/22.330/23.103°C.
