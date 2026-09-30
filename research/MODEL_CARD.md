# Model card: ENSO-conditioned residual MLP calibration

## Status and intended use

Version 0.1.0 is a **training/evaluation scaffold**, not a trained forecast product. No real hindcast dataset, model weights, scientific accuracy estimate, or validated global/CONUS skill is supplied. Initial local verification passed 16 dependency-free software tests; one optional neural smoke test was skipped because PyTorch was absent. A successful software test is not meteorological validation.

Intended use: a bounded research experiment testing whether a small neural residual correction improves pre-existing regional temperature/precipitation anomaly forecasts over days 15–56. It may complement a dashboard's properly attributed public forecasts after independent validation.

Not intended for public safety, emergency response, agricultural/financial commitments, deterministic local weather promises, climate attribution, extrapolation to unknown regions, or unsupported weeks/units.

## Architecture and inputs

A fully connected PyTorch network with two 64-unit hidden layers (default), GELU activations, 0.1 dropout and a two-output linear layer. It predicts standardized temperature and precipitation residuals. Predictions are unscaled and added to archived raw anomalies.

Inputs: raw temperature/precipitation anomalies, issuance-to-verification lead, available-at-issuance ENSO index, valid-month sine/cosine, ENSO-season interactions, training-region one-hot encoding. A no-ENSO ablation masks the index and both interactions. This is supervised calibration, not backbone fine-tuning, a global grid emulator, a causal model, or a probabilistic forecast.

## Data and provenance

Requires a genuine user-supplied CSV with initialization/verification dates, stable region, two raw forecast anomalies, two matched observed anomalies, and a vintage-correct ENSO index. Whole-episode/block labels are optional but required for an event-independent claim. Source, units, aggregation periods, region masks, anomaly references, and ENSO availability must be documented in a manifest.

The loader checks structure and finite values. It cannot independently verify that source labels, index vintages, climatologies, or model hindcasts lack future information. The manifest's assertions must be supported by the researcher's archive preparation. Test fixtures have artificial values for software validation only; they are not training or evaluation evidence.

## Training and evaluation design

- CPU-only execution; no provider provisioning, external download, or payment code
- Fixed seed and deterministic PyTorch operations, with exact runtime version recorded
- Chronological partitions; purge verification windows/availability lags at boundaries
- Remove earlier-partition observations from any event spanning multiple partitions
- Fit feature/residual scaling and regional-month climatology using retained training data only
- Optimize normalized residual MSE using AdamW; select checkpoint using validation loss
- Evaluate the held-out test once after selecting the checkpoint
- Report physical-unit RMSE for raw, zero-anomaly, training-climatology, and calibrated predictions on identical rows
- Include descriptive week, region, and ENSO-index group metrics and counts

Default runtime cap is soft and checked after each epoch. Exact environment locking and immutable input artifacts are needed for repeatability. Validation estimates are affected by model selection. The seed alone is insufficient for cross-platform bitwise reproducibility.

## Results

**Not available.** No scientific training/evaluation has been run. No improvement over raw forecasts or climatology is claimed. No evidence yet demonstrates that ENSO features add value. No operating or training bill has been incurred by this package.

## Limitations and failure modes

ENSO events are rare, unequal, nonstationary, and correlated with other climate processes. A large row count can conceal a very small independent sample. Overlapping forecast windows, repeated verifying dates, regional correlations, and climatology construction can inflate apparent certainty. Nonstationary forecast versions, observation revisions, index vintage leakage, reference-period inconsistency, and precipitation skewness can invalidate comparisons.

This model lacks explicit ocean/atmosphere dynamics, remote spatial interactions, uncertainty propagation, probability reliability, extremes safeguards, downscaling, and causal identification. Region one-hot features support known training regions only. Unbounded anomaly predictions can be physically implausible. Precipitation anomaly values may be negative legitimately; translating them to absolute precipitation requires a separate documented baseline and physical validation.

A fixed temporal holdout can be unrepresentative. Complete-event exclusion can remove much of a short record; inspect split counts and ENSO coverage. The code fails on empty splits, but does not assert that any nonempty sample is scientifically adequate. Group RMSE differences are not confidence intervals or significance tests.

## Release criteria before operational use

1. Verify forecast/observation licenses, units, masks, time windows, source vintage, and anomaly references
2. Predeclare data partitions, observation latency, complete event blocks, acceptance thresholds and candidate settings
3. Demonstrate robust held-out gains against raw/climatology and simpler bias-correction/regression baselines
4. Run matched no-ENSO ablations, multiple seeds, rolling-origin evaluation and event/block uncertainty analysis
5. Check both targets separately across region, lead, season, extremes and relevant use cases
6. Independently reproduce outputs and preserve source hashes plus a locked software environment
7. Add appropriate uncertainty displays, stale/missing-data behavior, monitoring and retraining policy
8. Obtain explicit authorization before any paid provider or requester-pays transfer; user constraints are under $100/month operations and no more than $200 training

## Future option

ACE2-ERA5 evaluation or adaptation is a separate project, not part of this implementation. Review its official model card and input/forcing requirements, data-transfer costs, license, hindcast configuration and compute feasibility before proposing any purchase: https://huggingface.co/allenai/ACE2-ERA5/blob/main/README.md
