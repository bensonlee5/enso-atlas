# ENSO Atlas forecast deviations

This standard-library-only module computes **temperature proxy diagnostics**, not exact forecast skill or evidence of model ranking. It evaluates only genuine archived raw CFSv2 four-member p50 forecasts against genuine NOAA CPC analyses. The initial September 29, 2026 run has no completed valid period as of September 30: **all 90 location-period records are pending and every score is null**.

## Production CLI

From the Site repository after copying the module to `ingestion/verify_forecasts.py`:

```sh
python ingestion/verify_forecasts.py \
  --archive-dir dist/data/archive \
  --output dist/data/verification.json
```

There are no third-party Python dependencies, credentials, or API keys. Python 3.10+ is required.

Optional reproducible audit output:

```sh
python ingestion/verify_forecasts.py \
  --archive-dir dist/data/archive \
  --output verification-audit.json \
  --evidence-dir observation-evidence \
  --include-pairs
```

The default output omits per-pair rows, keeping the public dashboard summary small. The summary retains lead, location and joint aggregates; exact source response hashes; immutable forecast hashes; recipe hash; late-archive counts; errors and limitations. `--include-pairs` includes native/observation coordinates, exact observed dates, errors, late-capture flags and missing-day lists. `--evidence-dir` writes immutable content-addressed raw NOAA responses. Re-fetches identify source revisions with new response hashes; current results do not silently substitute a stale prior report. Keep the previous report/evidence separately if historical revision comparison matters.

`--as-of` can set a historical maturity cutoff; it cannot request a future cutoff. A historical cutoff does **not** reconstruct the observation version available on that historical date: NOAA observations are fetched as currently served, and their retrieval times/hashes are recorded. `--latency-days` defaults to 3 and cannot be set below 3.

## Exact official source endpoints

Dataset documentation: https://psl.noaa.gov/data/gridded/data.cpc.globaltemp.html

Dataset roots:

- https://psl.noaa.gov/thredds/dodsC/Datasets/cpc_global_temp/tmax.2026.nc
- https://psl.noaa.gov/thredds/dodsC/Datasets/cpc_global_temp/tmin.2026.nc

The client requests `.das` for units/grid/window metadata, `.dds` for available annual time count, and bounded `.ascii` point/date subsets. It validates the returned per-day time coordinates, not merely the response status or requested dates. Example actual point subset used in the successful live probe:

https://psl.noaa.gov/thredds/dodsC/Datasets/cpc_global_temp/tmax.2026.nc.ascii?tmax%5B261:1:267%5D%5B103:1:103%5D%5B476:1:476%5D

These URLs are public and require no authentication. On September 30, 2026 at 04:54 UTC, the live annual source dimensions included September 28 for both Tmax and Tmin. A real September 19–25 point sample was fetched successfully at CPC 38.25N, 121.75W. `evidence/live-source-probe.json` records actual values, timestamps and six source response SHA256 hashes. **The probe does not pair those historical observations to the September 29 forecast and does not compute forecast scores.**

Data provided by NOAA PSL, Boulder, Colorado, USA, from https://psl.noaa.gov .

## Scientific interpretation

- Raw CFS temperature p50 is the four-member median of each member's 28 instantaneous six-hourly temperature samples for a seven-day lead.
- Observed daily temperature is the CPC analysis midpoint `(Tmax + Tmin) / 2`, then averaged over all seven dates. Both variables must be finite on every date. This midpoint is a mean-temperature proxy, not a measured time-integrated daily mean.
- CPC metadata describes extrema windows as `6z to 6z`; CFS nominal periods start at midnight and contain samples from +6 hours through the nominal period end. Temporal definitions differ, so diagnostics are prominently labeled as a proxy comparison.
- Observations use the nearest CPC 0.5-degree cell to the native forecast point. The nominal city label does not imply a city-center station observation. Missing offshore/land-mask cells remain missing; there is no fallback to a nearby city or interpolated value.
- San Francisco and Sacramento use the same native model point in the seed archive. Their apparent separate deviations are duplicate spatial evidence, not independent tests.
- A valid period must have ended at least three full days before the cutoff. This is an application safety buffer, **not a NOAA delivery or quality-control guarantee**. Exact daily source coverage is still required.
- Days 57–60 are only four days. They receive a separate diagnostic in `temperature.partialDays57to60` and are excluded from full-week overall/lead/location aggregates.
- Positive bias means the forecast was warmer than the observed proxy: error = forecast − observed proxy; bias = mean(error); MAE = mean(abs(error)); RMSE = sqrt(mean(error²)). A forecast-location-period is one case. Overlapping daily model runs are not independent samples.
- An archive captured after a valid period began is flagged. The seed's ten Week1 cases carry that flag. This is not evidence that their original NOAA forecasts were issued late; it is a limit on the archive's strict prospective capture claim.
- Current precipitation is a sampled instantaneous rate in mm/day-equivalent, not a validated integral or accumulated rainfall. Its verification status is always `incompatible_statistic`; no rainfall score is invented.
- No anomalies, ENSO contribution, tail probabilities or probability calibration are evaluated.

## Input contract

`archive-dir/index.json` is a mutable active index with schemaVersion1 and up to400 `issuances` entries, each with `run`, `path`, `sha256`, `archivedAt`. Paths must resolve inside the archive directory. The SHA256 of every issuance file is checked before parsing its forecast values.

An immutable issuance has `schemaVersion`, `archivedAt`, `run`, `sourceProductSha256`, `model:"NOAA CFSv2"`, `memberCount:4`, units `{temperature:"°C",precipitationRate:"mm/day"}`, sources and up to10 locations. Each location includes its name, requested/native coordinates, grid index and periods. The verifier expects complete weeks1–8, plus optional four-day period9. Periods carry leadWeek, ISO8601 intervalStart/intervalEndExclusive, firstSampleHour, lastSampleHour, sampleCountPerMember and ordered finite p10/p50/p90 arrays for each field. Invalid hashes, units or changed temporal definitions fail closed without replacing a previous report.

The schema matches the supplied immutable seed archive `2026092900.json`.

## Bounds and outage behavior

- At most400 active issuances,10 unique native points and3 calendar years
- At most80 official source requests
-240-second total network deadline, with per-request timeout up to25seconds
-2MB maximum per response
- Batched point/year spans, so overlapping forecasts do not each cause network calls
- No observation calls at all if no period has matured
- Missing/failed observation retrieval yields explicit gaps and null scores; ordinary source latency/outage does not fail forecast ingestion
- Archive-integrity/schema problems are fatal, by design

The network deadline is checked before each request, and the remaining budget limits its socket timeout. Very slow streaming transport can make the wall-clock operation slightly exceed the nominal budget; it is not a hard OS-level kill timer.

## Validation

22 unit tests pass. All synthetic values are restricted to in-memory unit-test fixtures and are explicitly labeled synthetic in reports returned to tests. Cases cover maturity, complete-day requirements, missing/nonfinite data, bias sign, partial-period separation, archive capture timing, tamper detection, traversal, duplicate runs, unsupported sample statistics, NOAA failures, request bounds, nearest-grid mapping, invalid extrema and strict JSON serialization.

```sh
python -m unittest discover -s tests -p 'test_verify_forecasts.py' -v
```

When copying the test into a repository-level `tests/` directory, change its import path insertion to the repository's `ingestion/` directory. The live observed-source probe is separate from tests and from published skill metrics.
