# Genuine CONUS forecast–verification pairs for a bounded calibration pilot

Prepared 2026-09-30 UTC. No paid access, signup, login, or cloud compute purchase.

## Delivered

`pairs.csv`: 3,588 real regional pairs, 598 forecast initialization dates in 1999–2021. A calibration target is the difference between genuine archived CFSv2 and matched observed CPC outcomes. This is not a direct statistical weather generator and not a new global forecast backbone.

`prepare.py` reproducibly prepares the input. `download.py` retrieves five bounded public files. `source/download_manifest.json` records immutable raw-file SHA256 hashes and canonical unsigned URLs. `audit.json`, `region_grid.csv`, and `dropped_rows.json` document sample counts, masks, and omissions. The full raw downloads are about 1.2 GB; the pilot CSV is under 1 MB.

## Primary sources and attribution

- Dataset and license: https://github.com/microsoft/subseasonal_data (SubseasonalClimateUSA data CC BY 4.0; repository code MIT)
- Scientific definitions and original NOAA/IRI data citations: https://github.com/microsoft/subseasonal_data/blob/main/DATA.md
- Mouatadid et al., *SubseasonalClimateUSA: A Dataset for Subseasonal Forecasting and Benchmarking*, NeurIPS 2023: https://arxiv.org/abs/2109.10399
- CFSv2/SubX original source: https://doi.org/10.7916/D8PG249H; Saha et al. 2014, *The NCEP climate forecast system version 2*
- CPC temperature: Fan and Van den Dool 2008; CPC precipitation: Chen et al. 2008 and Xie et al. 2010, as listed in the archived DATA.md
- Date alignment implementation: https://github.com/microsoft/subseasonal_toolkit/blob/main/subseasonal_toolkit/models/subxpp/subxpp.ipynb and https://github.com/microsoft/subseasonal_toolkit/blob/main/subseasonal_toolkit/utils/experiments_util.py

The upstream README and DATA.md are retained in `source/`. Their described processing and this additional regional/time subsampling must be acknowledged when redistributing derived data. The dataset license is separate from the upstream MIT software license.

## Exact target, forecasts, and observations

- Both original fields use the same CONUS 1.5° grid (376 cells), matched exactly by latitude/longitude; no nearest-neighbor extrapolation
- Forecasts: `iri-cfsv2-{tmp2m,precip}-all-us1_5-ensembled.h5`, selected column `iri_cfsv2_{variable}-15.5d`
- Upstream averages the four daily six-hourly CFSv2 predictions and combines initialization t/lead l with initialization t−1/lead l+1, preserving the same target period
- `init_date` is archived model initialization date, not proof of a historical file publication timestamp
- `target_start = init_date + 15 days`; `target_end = init_date + 28 days`, inclusive 14-day period. This follows raw CFSv2 toolkit week3–4 configuration: first_day=1, first_lead=last_lead=15, get_forecast_delta(34w)=15
- Do not call these individual weekly outputs. They are a week3–4 fortnight target only, not weeks5–8
- Forecast/observed temperature is the 14-day mean in °C; CPC observed daily temperature is mean of daily min/max
- Forecast/observed precipitation is a 14-day total in mm
- Observations: `gt-us_{tmp2m,precip}_1.5x1.5-14d.h5`; their `start_date` is the aggregation start, explicitly shifted to the target end in our CSV
- Six coarse geographic regions are fixed by longitude west<255°, central255–<275°, east>=275° (0–360 coordinates), crossed with south<37.5° latitude and north>=37.5°. These are custom geographic bins, not official NOAA climate divisions. Each field is cosine-latitude weighted over the identical fixed grid. Exact cell masks/weights are in region_grid.csv
- Retain only every 14th initialization anchored 1999-01-01; target windows do not overlap within a region. Three absent source initializations in 2017 are omitted without imputation; see audit.json
- All fields must be finite at every fixed cell before a region/date is retained. No incomplete regional rows were encountered

## Baselines, splits, and scientific limits

Use raw CFSv2, a training-only seasonal climatology, a training-only simple bias correction, a small linear regression, and persistence alongside any neural model. Fit all scaling, anomaly references and model choices only on training data. CSV values are absolute physical values, not precomputed full-period anomalies.

`persistence_temp_c` and `persistence_precip_mm` use a preceding observed 14-day period whose end is init_date−30 days (start init_date−43). This conservative lag avoids future target information, but final revised CPC analyses are used. It is a retrospective lagged-observation baseline, not an audited real-time-vintage baseline.

Predeclared before any scoring: training initializations before 2015; validation 2015–2017; held-out test 2018–2021. Purge earlier-partition target labels close to the next partition (trainer must apply and report a >=14-day gap; larger observation-latency guard is permitted). Full-year temporal holdouts plus nonoverlap do not establish independent ENSO-event holdouts. Regional rows share weather events: report 598 distinct initializations rather than claiming 3,588 independent samples. The 2017 missing dates and other archive characteristics can affect comparisons.

CFSv2 is a retrospective forecast archive and the observation analyses can be revised. No claim is made that every historical verification value or forecast file was physically published on its nominal date. No false strict-provenance attestation is supplied to the prior scaffold. The pilot evaluates retrospective out-of-time calibration, not live operational skill.

`retrospective_mei_sensitivity_only.csv` contains the separately retained MEI.v2 archive feature looked up 60 days before initialization. The lag prevents an obvious future-month join but does NOT establish historical publication vintage: MEI is retrospectively revised. It is excluded from `pairs.csv` and the primary no-ENSO pilot. Any later use must be labeled retrospective sensitivity, not evidence of operational ENSO benefit. SST inputs have not been added. Genuine archived ENSO/SST publication vintages remain needed for an operational ENSO-aware claim.

A small neural model can underperform basic corrections. Retain all test outcomes, avoid tuning on test results, and do not connect these experimental values to the public forecast dashboard. Event-block uncertainty, independent periods, regional/seasonal diagnostics and extreme-event evaluation remain necessary before deployment.

## Reproduction

Install pandas, tables and numpy from PyPI. Run download.py, then prepare.py. Use an isolated virtual environment for the dependencies. Archive hashes and compare audit results after regeneration because upstream blobs can be updated. The trainer is included one directory above this data folder as `../train_pilot.py`; see `../README.md` for the full training command and dependencies.
