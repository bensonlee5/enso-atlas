"""CPU-first residual MLP training. Uses only supplied data; no download or spend."""
from __future__ import annotations
import argparse
import copy
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import random
import time

from .data import (load_rows, split_rows, split_summary, check_manifest, sha256_file,
                   fit_preprocessor, encode_rows, transform, climate_prediction)
from .metrics import evaluate
from .validate import arguments


def build_model(torch, features, width, dropout):
    model = torch.nn.Sequential(
        torch.nn.Linear(features, width), torch.nn.GELU(), torch.nn.Dropout(dropout),
        torch.nn.Linear(width, width), torch.nn.GELU(), torch.nn.Dropout(dropout),
        torch.nn.Linear(width, 2))
    torch.nn.init.zeros_(model[-1].weight)
    torch.nn.init.zeros_(model[-1].bias)
    return model


def train_experiment(args):
    # Fail on invalid data/provenance before importing the optional compute dependency.
    rows = load_rows(args.csv)
    manifest = check_manifest(args.manifest)
    splits, purged = split_rows(rows, args.validation_start, args.test_start,
                                args.observation_lag_days, args.holdout_events)
    pre = fit_preprocessor(splits["train"], use_enso=not args.no_enso)
    out = Path(args.output)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output must be new or empty, to preserve previous experiments")
    if min(args.epochs, args.patience, args.batch_size, args.width, args.threads) < 1:
        raise ValueError("Epochs, patience, batch size, width and threads must be positive")
    if not all(math.isfinite(v) for v in (args.dropout, args.lr, args.weight_decay, args.max_minutes)):
        raise ValueError("Numeric hyperparameters must be finite")
    if not 0 <= args.dropout < 1 or args.lr <= 0 or args.weight_decay < 0 or args.max_minutes <= 0:
        raise ValueError("Invalid dropout, learning rate, weight decay or runtime cap")
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("PyTorch is not installed. Install requirements in a local environment; no cloud service is required.") from exc
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    # Deliberately CPU-only: there is no automatic GPU/cloud provisioning.
    device = torch.device("cpu")
    x = {name: torch.tensor(encode_rows(part, pre), dtype=torch.float32, device=device)
         for name, part in splits.items() if name != "test"}
    y = {name: torch.tensor([transform([o - p for o, p in zip(r.observed, r.raw)], pre["residuals"])
                            for r in part], dtype=torch.float32, device=device)
         for name, part in splits.items() if name != "test"}
    model = build_model(torch, x["train"].shape[1], args.width, args.dropout).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    loss_fn = torch.nn.MSELoss()
    best, state, best_epoch, stale, history = math.inf, None, 0, 0, []
    started = time.monotonic()
    stop = "epoch_limit"
    for epoch in range(1, args.epochs + 1):
        model.train()
        permutation = torch.randperm(len(x["train"]))
        train_total = 0.0
        for start in range(0, len(permutation), args.batch_size):
            idx = permutation[start:start + args.batch_size]
            optimizer.zero_grad()
            loss = loss_fn(model(x["train"][idx]), y["train"][idx])
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite training loss; inspect inputs and scaling")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            train_total += float(loss.detach()) * len(idx)
        model.eval()
        with torch.no_grad():
            validation_loss = float(loss_fn(model(x["validation"]), y["validation"]))
        if not math.isfinite(validation_loss):
            raise ValueError("Nonfinite validation loss")
        history.append({"epoch": epoch, "train_normalized_residual_mse": train_total / len(x["train"]),
                        "validation_normalized_residual_mse": validation_loss})
        if validation_loss < best - 1e-8:
            best, best_epoch, stale = validation_loss, epoch, 0
            state = copy.deepcopy(model.state_dict())
        else:
            stale += 1
        if stale >= args.patience:
            stop = "validation_early_stop"
            break
        if time.monotonic() - started >= args.max_minutes * 60:
            stop = "runtime_cap_after_epoch"
            break
    model.load_state_dict(state)
    model.eval()
    metrics, all_predictions = {}, []
    # Only now touch test features and targets for scoring the selected checkpoint.
    for name in ("validation", "test"):
        part = splits[name]
        with torch.no_grad():
            residuals = model(torch.tensor(encode_rows(part, pre), dtype=torch.float32)).tolist()
        calibrated = [[r.raw[k] + residual[k] * pre["residuals"]["scale"][k]
                       + pre["residuals"]["mean"][k] for k in range(2)]
                      for r, residual in zip(part, residuals)]
        predictions = {"raw_forecast": [list(r.raw) for r in part],
                       "zero_anomaly_climatology": [[0.0, 0.0] for _ in part],
                       "train_region_month_climatology": [climate_prediction(r, pre) for r in part],
                       ("residual_mlp_no_enso" if args.no_enso else "enso_residual_mlp"): calibrated}
        metrics[name] = evaluate(part, predictions)
        for i, r in enumerate(part):
            record = {"split": name, "init_date": r.init_date.isoformat(),
                      "valid_date": r.valid_date.isoformat(), "region": r.region,
                      "week": r.week, "enso_index": r.enso_index, "enso_event_id": r.enso_event_id,
                      "observed_temperature": r.observed[0], "observed_precipitation": r.observed[1]}
            for model_name, pred in predictions.items():
                record[f"{model_name}_temperature"] = pred[i][0]
                record[f"{model_name}_precipitation"] = pred[i][1]
            all_predictions.append(record)
    report = {"experiment": ("Residual calibration with ENSO masked" if args.no_enso else
                             "ENSO-conditioned residual calibration"),
              "method_scope": "Small residual MLP; not backbone fine-tuning",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "data_sha256": sha256_file(args.csv), "manifest_sha256": sha256_file(args.manifest),
              "provenance": manifest, "config": {k: str(v) if hasattr(v, "isoformat") else v
                                                for k, v in vars(args).items()},
              "runtime": {"python": platform.python_version(), "torch": torch.__version__,
                          "device": "cpu", "seconds": time.monotonic() - started,
                          "stop_reason": stop, "best_epoch": best_epoch,
                          "parameter_count": sum(p.numel() for p in model.parameters())},
              "split_audit": split_summary(splits, purged), "metrics": metrics,
              "caveats": ["Single fixed temporal test; not nested cross-validation",
                           "Rows are correlated; RMSE differences are not significance tests",
                           "ENSO phase thresholds are descriptive, not an official event classification",
                           "No probabilities, reliability validation, global field model, or causal ENSO claim",
                           "No demonstrated value of ENSO without an independent no-ENSO ablation",
                           *( [] if rows[0].enso_event_id else
                              ["No event IDs supplied: event independence is NOT established"])]}
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    (out / "preprocessor.json").write_text(json.dumps(pre, indent=2, allow_nan=False) + "\n")
    (out / "training_history.json").write_text(json.dumps(history, indent=2, allow_nan=False) + "\n")
    with (out / "predictions.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_predictions[0]))
        writer.writeheader()
        writer.writerows(all_predictions)
    torch.save({"state_dict": model.state_dict(), "input_features": x["train"].shape[1],
                "width": args.width, "dropout": args.dropout}, out / "model.pt")
    return report


def main():
    parser = arguments(argparse.ArgumentParser(description=__doc__))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--dropout", type=float, default=.1)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--no-enso", action="store_true", help="Matched ablation: mask ENSO and its interactions")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--max-minutes", type=float, default=15)
    args = parser.parse_args()
    try:
        report = train_experiment(args)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"output": args.output, "runtime": report["runtime"],
                      "test_overall": report["metrics"]["test"]["overall"]}, indent=2))


if __name__ == "__main__":
    main()
