# ENSO Atlas historical calibration pilot

This is an **actually trained, deterministic, no-ENSO residual neural network**, not a forecast backbone fine-tune. It calibrates six coarse regional CFSv2 temperature and precipitation forecasts for one **14-day weeks 3–4 target** (initialization +15 through +28 days). It is a historical experiment, not a deployed live model or evidence of operational ENSO skill.

## Main finding

On untouched test initializations in 2018–2021, neural calibration improved raw CFSv2 error, but **did not beat the simple ridge baseline on either variable's RMSE**. Neural precipitation MAE was slightly lower. These small model differences have not been tested for statistical significance. No hyperparameter was changed after viewing test scores.

| Model | Temperature RMSE °C | Temperature MAE °C | Precipitation RMSE mm/14d | Precipitation MAE mm/14d |
|---|---:|---:|---:|---:|
| Raw CFSv2 | 2.23782 | 1.70245 | 18.26130 | 14.33237 |
| Training seasonal climatology | 2.00087 | 1.51476 | 15.83100 | 11.54318 |
| Training regional bias correction | 2.01211 | 1.50072 | 17.39561 | 12.84124 |
| Ridge residual | **1.93456** | **1.45002** | **15.77789** | 11.52649 |
| Neural residual, no ENSO | 1.94064 | 1.45678 | 15.81491 | **11.49495** |
| Lagged-observation persistence | 8.35074 | 7.14148 | 21.63655 | 16.51320 |

Scores weight each region/date equally after the original grid cells are area-weighted within each region. They are not grid-area-weighted continental errors. No probabilities, coverage, Brier score, CRPS, or reliability diagram are supplied: the model is deterministic.

## Exact sample and splits

Source CSV: 3,588 rows / 598 distinct initializations, 1999-01-01 through 2021-12-31. Six fixed custom longitude/latitude bins cover 376 CONUS 1.5° cells; they are not official climate divisions. Masks and weights are in `data/region_grid.csv`. Every 14th initialization is sampled; targets do not overlap within a region. Three absent 2017 initializations were omitted, with no imputation.

- Training: 2,490 rows / 415 initializations, 1999-01-01 to 2014-11-14; target dates 1999-01-16 to 2014-12-12
- Validation: 432 rows / 72 initializations, 2015-01-09 to 2017-11-10; target dates 2015-01-24 to 2017-12-08
- Test: 630 rows / 105 initializations, 2018-01-05 to 2021-12-31; target dates 2018-01-20 to 2022-01-28
- Purged: 36 rows / 6 initializations at the training and validation end boundaries, enforcing at least 14 days between the earlier split's last target and the next split's first initialization

Splits are fixed by full initialization years. Verification can extend into the next calendar year; the last test period ends January 2022. Correlated regions are not independent samples or ENSO episodes. There is no event-independent ENSO holdout.

## Model, selection and baselines

A 14-input residual MLP, two tanh hidden layers of 24 and 12 units, and two linear outputs has 686 fitted parameters. Inputs are the two raw physical forecasts, their differences from training-only seasonal climatology, four seasonal harmonic values, and six region indicators. There are no MEI, ENSO, SST, future observation or persistence inputs. Target calendar position is known at issue time. Output residual scaling and feature scaling are fit on training only.

The seasonal baseline fits an intercept and two annual sine/cosine harmonics separately for each region using training observations. The additive baseline fits each region's mean forecast error. Ridge fits normalized forecast residuals on the same feature matrix, fixed alpha 10. All corrected precipitation predictions are clipped to nonnegative totals; raw CFSv2 is not altered.

Fixed experiment: seed 42; Adam learning rate 0.001; neural alpha 0.01; minibatch 128; maximum 400 epochs; early stopping after 40 epochs without validation improvement. A checkpoint is selected by two-variable standardized residual MSE on validation. Test features/scoring occur only after checkpoint selection. Best epoch 59; 99 epochs run. One CPU training run took 0.88 seconds in this environment. No paid compute was used. `run/frozen_experiment.json` records the predetermined settings and input hashes; `training_history.json` records all epochs.

The safe, readable `run/model.json` holds weights and preprocessing; there is no pickle or executable model serialization. `neural_json_predict` reproduces the saved network using NumPy, verified against sklearn to 1e-10 absolute tolerance during training. It is only for matching archived product/units/regions/horizon, not for application to a different live product.

## Reproduce

From this directory, with Python 3.12 and the pinned dependencies in requirements.txt:

```sh
python -m pip install -r requirements.txt
python train_pilot.py --csv data/pairs.csv --manifest data/provenance.json --output reproduced_run
python -m unittest -v
```

`--output` must be new or empty. A deterministic rerun can be compared with `run/report.json`, `run/model.json` and `run/predictions.csv`. CPU library/platform changes may affect floating-point results. The included CSV is genuine derived data, sufficient to reproduce training without downloading the 1.2 GB raw archive. Rebuilding the CSV requires `data/download.py`, `data/prepare.py`, pandas/PyTables, and upstream sources; see `data/README.md` and the SHA256 download manifest. Archived raw files are not bundled.

## Validation and limitations

Four tests pass: real split/lead/purge integrity; duplicate rejection; overlapping-target rejection; saved JSON inference and recomputed heldout metrics. Each training run additionally checks finite values, fixed target length, no negative precipitation, region coverage and inference agreement. This is tested model code, not a scientific certification.

Data are final retrospective CPC analyses and an archived CFSv2 product; exact historical forecast publication and observation revision vintages are not certified. The persistence baseline has a 30-day observation lag but uses final revised observations. This experiment does not simulate operational retraining at every issue date. Revised MEI is deliberately excluded because a lag alone cannot establish what was known at historical issuance.

Coarse regional averages suppress local extremes. One seed and a single chronological split do not establish generalization across independent ENSO events or future climate, local forecasting accuracy, regional extremes, or neural superiority. The neural model remains an experimental artifact and should not modify the live dashboard forecast values. Actual ENSO-aware calibration requires independently validated issuance-time index vintages and matched no-ENSO testing.

## Provenance and attribution

Derived from Microsoft's [SubseasonalClimateUSA dataset](https://github.com/microsoft/subseasonal_data), licensed CC BY 4.0, with CFSv2/SubX forecasts and CPC verification. See [source documentation](https://github.com/microsoft/subseasonal_data/blob/main/DATA.md), `data/README.md`, `data/provenance.json`, and `data/source/download_manifest.json` for source citations, exact processing, hashes and canonical download URLs. Attribution and notice of modifications must be retained when redistributing this derived dataset. The upstream software MIT license in `data/source/LICENSE` does not replace the dataset's CC BY 4.0 terms. Regional averaging, temporal subsampling, baseline fitting and neural calibration are additional processing in this pilot.
