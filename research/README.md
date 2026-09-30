# ENSO-aware subseasonal calibration experiment

A CPU-first PyTorch experiment for calibrating **regional temperature and precipitation anomalies at days 15–56 (weeks 3–8)**. It learns a small residual correction to an existing forecast, conditioned on an ENSO index available at forecast initialization. It is a calibration network, not a newly trained global atmospheric model or backbone fine-tune.

**Current status: scaffold implemented; no real hindcast dataset supplied; no fitted model or scientific skill scores exist.** Local checks passed 16 software tests; one neural smoke test is skipped because PyTorch is not installed in the build environment. The artificial values inside unit tests are software fixtures, never forecast evidence.

## What is included

- Strict chronological train/validation/test splits, with observations crossing a later boundary removed
- Optional observation-availability lag and complete ENSO-event/block holdouts
- Training-only feature/residual standardization and regional/monthly climatology
- Two-hidden-layer residual MLP, validation early stopping, fixed seed, deterministic CPU execution
- Matched `--no-enso` ablation
- Paired temperature/precipitation RMSE for raw forecasts, zero-anomaly climatology, training-only regional/month climatology, and the calibrated MLP
- Separate week, region, and descriptive ENSO-index phase diagnostics
- Input hashes, provenance, configuration, preprocessing, checkpoint, predictions, and training history saved per run
- No service signup, network download, cloud provisioning, paid compute, or purchase in the code

## 1. Supply genuine hindcasts and observations

Start with `examples/hindcasts.schema.csv`, which contains headers only. Required columns:

| Column | Meaning |
| --- | --- |
| `init_date` | Forecast issuance date, `YYYY-MM-DD` |
| `valid_date` | Verification date, or **end** of the defined averaging period |
| `region` | Stable region ID with a documented spatial mask |
| `raw_temp_anomaly` | Archived model temperature anomaly |
| `raw_precip_anomaly` | Archived model precipitation anomaly |
| `enso_index` | Numeric ENSO index in a documented definition and vintage available by `init_date` |
| `observed_temp_anomaly` | Matched verified temperature anomaly |
| `observed_precip_anomaly` | Matched verified precipitation anomaly |
| `enso_event_id` | Optional complete episode/block label; must be populated for every row if the column exists |

Remove the optional event column entirely if event labels are unavailable. That permits temporal validation but **does not establish event-independent skill**. Use neutral-period block IDs too; do not label every neutral row across decades with one shared event ID. Define IDs from an external event chronology, prior to examining model errors. Do not derive event IDs from the response variables or from individual rows' ENSO sign alone.

Data preparation requirements:

1. Use a consistent forecast system/version and matched forecast/observation anomaly units, averaging periods, region masks, and area weights. Separate incompatible products into separate experiments. Missing, infinite, malformed, duplicate, and out-of-range rows are rejected rather than silently imputed.
2. Standardize anomaly references without using held-out data. This code receives anomalies; it **cannot repair or detect leakage already introduced by upstream anomaly construction**. Use training-only reference estimates or an explicitly justified fixed operational baseline that excludes held-out information. Archive that choice.
3. ENSO predictors must be genuinely available at issuance. A retrospective centered seasonal index joined on the target month can contain future information. Use archived publication vintages or a justified lag. The software requires an attestation, not a claim that it has independently verified publication dates.
4. Weekly averages must use `valid_date` as their period end. The horizon grouping is relative to issuance: days 15–21 are week 3, 22–28 week 4, through 50–56 week 8. Do not mix daily values and weekly means in one dataset. Verify forecast and observation windows externally.
5. Labels must have arrived before the next partition begins. Set `--observation-lag-days` conservatively for the selected observation product. Default zero means immediate availability and is unsuitable if labels are delayed.
6. Freeze dataset, test dates/events, region coverage, hyperparameters, and acceptance criteria before looking at test results. Many correlated rows do not substitute for many independent ENSO episodes.

The header-only CSV deliberately contains no invented hindcast data. This package does not automatically acquire data or establish a public forecast license.

## 2. Record provenance

Copy `examples/provenance.template.json` to your own manifest, replace every descriptive placeholder, and verify the three boolean attestations before setting them true. Training rejects the template's false attestations. These are researcher declarations; they are not an automated provenance audit.

Record any available DOI/archive URL, product version, climatology period, region masks, averaging definitions, observation latency, ENSO index definition and historical publication policy. Keep the source dataset immutable.

## 3. Validate without any extra dependencies

Python 3.10+ is required. Run from this folder:

```bash
python -m unittest discover -s tests -v
python -m weathercal.validate --csv data/hindcasts.csv \
  --manifest data/provenance.json \
  --validation-start 2018-01-01 --test-start 2022-01-01 \
  --observation-lag-days 30
```

The dates above illustrate CLI syntax only; choose your cutoffs from actual coverage and a predeclared experiment. Validation prints row counts, date ranges, unique initializations, events, regions, horizon weeks, and purge counts. It does not print any made-up skill estimate.

Split behavior:

- Train: `init_date < validation_start`, with `valid_date + lag < validation_start`
- Validation: `validation_start <= init_date < test_start`, with `valid_date + lag < test_start`
- Test: `init_date >= test_start`
- Rows failing label-availability boundaries are excluded, not moved into later partitions
- If event IDs exist, any event spanning partitions is removed from earlier partitions; no retained event is shared across splits
- `--holdout-events EVENT_A EVENT_B` additionally restricts the test to those IDs and excludes them from development; every requested ID must have test rows
- Empty partitions and regions present only in held-out partitions fail validation

There is no random row split. Shuffling occurs only inside the already isolated training partition.

## 4. Run the local neural experiment when ready

Create a local virtual environment and install PyTorch from its official package source. This step is not performed by the delivered scaffold. No paid service is needed for this small model.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m weathercal.train --csv data/hindcasts.csv \
  --manifest data/provenance.json \
  --validation-start 2018-01-01 --test-start 2022-01-01 \
  --observation-lag-days 30 --output runs/enso-seed42
```

To pre-register a matched no-ENSO comparison, run the same command with `--no-enso` and a separate output directory. ENSO and its seasonal interactions are all masked. Use the same dates, events, network size, optimization budget, and seeds. A successful single network does not demonstrate that ENSO contributes skill.

Defaults: two width-64 hidden layers, GELU, dropout 0.1, AdamW, batch size 256, up to 200 epochs, patience 20, two CPU threads, seed 42. The learning objective is the average of training-standardized temperature and precipitation residual MSE. Reported RMSE remains in each variable's original anomaly units; the two physical units are never combined into one reported RMSE.

`--max-minutes 15` checks a soft runtime limit **after each completed epoch**. Data loading and one long epoch may exceed this limit. This is not a monetary budget guard or a scheduler kill switch. The program uses local CPU only and has no payment/cloud API. Requested limits of under $100/month operating cost and at most $200 training spend remain constraints, not verified cost estimates. Any future hosted run needs separately approved provider, service, total limit, and billing controls. No purchase has been made.

For reproducibility, retain `report.json`, input hashes, the immutable source CSV/manifest, and an exact environment lock from the verified machine (`python -m pip freeze > runs/enso-seed42/environment.lock.txt`). The broad requirement in `requirements.txt` is an installation compatibility range, **not a fully locked environment**. Bit-for-bit results are not promised across PyTorch releases or CPU architectures.

## 5. Read the outputs honestly

A new or empty output directory is required. The experiment writes:

- `report.json`: data/provenance SHA-256, full configuration, environment, stopping reason, selected epoch, split audit, separate validation/test RMSE
- `preprocessor.json`: training-only means/scales, region vocabulary, climatology, ENSO masking state
- `model.pt`: local PyTorch state dict and architecture metadata
- `predictions.csv`: per-row paired outputs from every baseline/model for independent audit
- `training_history.json`: training and validation normalized residual MSE

The test is scored only after checkpoint selection. Validation performance is tuning performance, not an unbiased final estimate. Repeatedly changing the setup after reading the test invalidates its role as an untouched test.

The zero-anomaly baseline predicts the input anomaly reference. Training climatology predicts the training mean observed anomaly for a region and valid month; an unseen month falls back to that region's all-month training mean. Both may differ if the input reference has nonzero residual biases. Climatology and scores are row-weighted, so repeated valid dates/overlapping forecast windows are correlated.

There are **no confidence intervals, probability calibration, field skill maps, extremes evaluation, or significance claims**. Before any deployment, perform rolling-origin multi-period validation, episode/block bootstrap confidence intervals, matched no-ENSO ablation, meaningful simpler regression/bias-correction baselines, and region/season/lead diagnostics. Predefine a minimum meaningful gain and assess both variables separately. Never claim ENSO causality from a feature association.

## Deployment and future model work

Do not label this scaffold as an operational forecast or connect an untrained/random model to the dashboard. Keep official/public forecast provenance, issue time, valid time, units, geographical coverage, and experimental outputs visibly separate. Missing experimental results should remain explicitly unavailable.

The code does not fine-tune ACE2-ERA5 or another weather backbone. ACE2-ERA5 is a future research option only, requiring checkpoint/license review, full atmospheric inputs and forcings, a separate hindcast design, and a realistic compute/data-transfer budget. Its documented training-data bucket is requester-pays; do not trigger such access without explicit spending authorization. Start with calibration of existing forecasts before considering that much larger project.

## Primary references

- NOAA CPC index definitions and source listings: https://www.cpc.ncep.noaa.gov/data/indices/
- NOAA historical ONI description (centered base periods and three-month means): https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/
- NOAA daily preliminary index methodology: https://github.com/noaa-nws-cpc/realtime-oni
- ACE2 original research: https://www.nature.com/articles/s41612-025-01090-0
- ACE2-ERA5 official model card, including data access details: https://huggingface.co/allenai/ACE2-ERA5/blob/main/README.md

Consult those definitions when selecting an ENSO index; the software's ±0.5 grouping is merely descriptive and is not an official episode classification.
