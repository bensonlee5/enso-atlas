# Genuine CFSv2 member percentiles for ENSO Atlas

## Output
`cfs-weekly-ensemble-percentiles.json` supplies genuine empirical P1/P5/P10/P50/P90/P95/P99 temperature and precipitation-rate quantiles at the same434 native sampled grid coordinates as the previous app data. Initialization2026-09-29 00Z, same-cycle members01,02,03,04. Not a lagged ensemble. There are8 full weeks (56days), plus `remainingDays57to60` for the separate last4days. Never call that partial interval a full ninth week.

The raw source contains240 six-hourly frames per member and variable through hour1440. Each forecast valid time and initialization is checked during decoding. Weekly28-frame averages are computed separately for every member, then NumPy `quantile(..., method='linear')` (Hyndman–Fan type7) is computed across the four member averages. No daily quantiles are averaged, and no member is presented as the median. P50 is the mean of the two central sorted members. For four sorted members, the type-7 interpolation rank is 3q: P1=0.97×minimum+0.03×second-lowest, P5=0.85×minimum+0.15×second-lowest, P10=0.7×minimum+0.3×second-lowest; upper tails follow the symmetric rule. P99 remains inside the sampled maximum. The extra tail selections do not add independent members or rare-event information. Each interval retains lossless member-by-location temporal averages in `memberMeans`, ordered by `memberIDs`, so quantiles can be reproduced without inferring members from summary percentiles. `availableQuantiles` and `quantileLevels` declare the seven output arrays; schema version is 2.

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

## Expanded-quantile QA (October 1, 2026)
The original September 29 00Z source members were retrieved again from NOAA, preserving the run and valid intervals. No tails were inferred from the older P10/P50/P90 summaries. All eight exact GRIB subsets total approximately112MB; this is CPU-only processing with no paid compute, new accounts or credentials. Public-data validation requires all seven finite ordered arrays, and rejects older three-array refreshes rather than silently removing supported tail selections. Existing immutable issuance archives are not rewritten; new archives retain every available quantile.

Run `PYTHONPATH=ingestion/ensemble python -m unittest discover -s tests -p test_ensemble_quantiles.py -v` for independent type-7 numerical expectations, permutation/equal-member checks and invalid-input rejection. `node tests/public-data-test.cjs` verifies bundle hashes and rejects missing tails or inverted ordering.

## 16-member lagged expansion (October 2026)

The default retrieval now uses four complete consecutive 00Z initializations,
with members 01–04 for each day (16 forecasts, not 16 independent outcomes).
The newest complete 00Z suite supplies the reference run. Older members download
through lead 60 + lag-days and discard the initial lag; every member then covers
exactly the same 240 six-hour valid instants. Temporal averaging happens after
this alignment, then seven empirical quantiles are computed from all 16 means.
Member IDs include initialization and perturbation number. Initialization range,
lag hours, first aligned GRIB record, and the unrounded member means are retained.
Missing or malformed members fail the whole refresh; no silent member reduction.

This is an application-defined lagged ensemble, not NOAA's published CPC ensemble
product. NOAA's seven-day rotating archive makes four days a bounded choice;
06/12/18Z perturbed runs are excluded because their shorter horizons cannot cover
all 60 days. See [NOAA CFSv2 documentation](https://cfs.ncep.noaa.gov/cfsv2/docs.html)
and [archive information](https://cfs.ncep.noaa.gov/cfsv2/downloads.html).

Members share a model, nearby initial conditions, and errors. Equal weights are
used; larger membership does not calibrate event probabilities. P1/P99 remain
interpolations near the sample extremes. This cannot substantiate 1% event odds,
provide a calibrated confidence interval, or correct model bias.

Expected full retrieval is about 450 MB across 32 paired temperature/rate GRIB
subsets, using at most two CPU decoding processes. There is no paid API or GPU.
The scheduled workflow keeps its existing daily 09:17 UTC target (GitHub may
start late), also runs after ingestion changes, and remains manually dispatchable.
It validates all products before one data-only Git commit. Failed downloads,
science checks, browser validation or merge conflicts never publish a partial
bundle. The Site checks the public hash-verified feed on open and hourly while
visible; it does not need a daily Site redeployment. Visible GFS daily forecasts
also refresh hourly directly from their existing Open-Meteo source.
