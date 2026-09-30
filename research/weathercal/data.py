"""Data checks, purged splits and train-only transforms; standard library only."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import re

NUMERIC = ("raw_temp_anomaly", "raw_precip_anomaly", "enso_index",
           "observed_temp_anomaly", "observed_precip_anomaly")
REQUIRED = ("init_date", "valid_date", "region") + NUMERIC


def parse_date(value: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"Expected YYYY-MM-DD, got {value!r}")
    return date.fromisoformat(value)


@dataclass(frozen=True)
class Row:
    init_date: date
    valid_date: date
    region: str
    raw_temp_anomaly: float
    raw_precip_anomaly: float
    enso_index: float
    observed_temp_anomaly: float
    observed_precip_anomaly: float
    enso_event_id: str = ""

    @property
    def lead_days(self):
        return (self.valid_date - self.init_date).days

    @property
    def week(self):
        return (self.lead_days - 1) // 7 + 1

    @property
    def raw(self):
        return (self.raw_temp_anomaly, self.raw_precip_anomaly)

    @property
    def observed(self):
        return (self.observed_temp_anomaly, self.observed_precip_anomaly)


def load_rows(path: str | Path) -> list[Row]:
    rows, keys = [], set()
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        names = reader.fieldnames or []
        if len(names) != len(set(names)):
            raise ValueError("Duplicate CSV column names")
        missing = set(REQUIRED) - set(names)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")
        has_events = "enso_event_id" in names
        for number, raw in enumerate(reader, 2):
            try:
                if None in raw or any(raw[k] is None for k in REQUIRED):
                    raise ValueError("Malformed CSV field count")
                values = {k: float(raw[k]) for k in NUMERIC}
                if not all(math.isfinite(v) for v in values.values()):
                    raise ValueError("All numeric values must be finite")
                region = raw["region"].strip()
                event = (raw.get("enso_event_id") or "").strip()
                if not region:
                    raise ValueError("Region cannot be blank")
                if has_events and not event:
                    raise ValueError("Every row needs an event/block ID when enso_event_id is present")
                row = Row(parse_date(raw["init_date"]), parse_date(raw["valid_date"]),
                          region, **values, enso_event_id=event)
                if not 15 <= row.lead_days <= 56:
                    raise ValueError("Supported lead is 15–56 days, inclusive (weeks 3–8)")
                key = (row.init_date, row.valid_date, row.region)
                if key in keys:
                    raise ValueError("Duplicate (init_date, valid_date, region) key")
                keys.add(key)
                rows.append(row)
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f"CSV line {number}: {exc}") from exc
    if not rows:
        raise ValueError("CSV contains no observations")
    return sorted(rows, key=lambda r: (r.init_date, r.valid_date, r.region))


def split_rows(rows, validation_start: date, test_start: date, observation_lag_days=0,
               holdout_events=()):
    """Assign by issuance; purge labels crossing next boundary and complete events.

    Event IDs must represent externally defined, complete episodes or neutral blocks.
    If an event appears in several splits, its earlier-split rows are removed.
    Explicit holdout_events restrict the final test to those IDs; they never enter dev.
    """
    if validation_start >= test_start or observation_lag_days < 0:
        raise ValueError("Require validation_start < test_start and nonnegative observation lag")
    holdout_events = set(holdout_events)
    any_events = any(r.enso_event_id for r in rows)
    if any_events and any(not r.enso_event_id for r in rows):
        raise ValueError("Event IDs must be complete")
    if holdout_events and not any_events:
        raise ValueError("Event holdout requested but enso_event_id is absent")
    missing = holdout_events - {r.enso_event_id for r in rows}
    if missing:
        raise ValueError(f"Requested events absent: {sorted(missing)}")
    splits = {"train": [], "validation": [], "test": []}
    purged = {"boundary": 0, "event_overlap": 0, "explicit_event_holdout": 0,
              "test_outside_requested_events": 0}
    lag = timedelta(days=observation_lag_days)
    for row in rows:
        if row.init_date < validation_start:
            name, boundary = "train", validation_start
        elif row.init_date < test_start:
            name, boundary = "validation", test_start
        else:
            name, boundary = "test", None
        if boundary and row.valid_date + lag >= boundary:
            purged["boundary"] += 1
        elif name != "test" and row.enso_event_id in holdout_events:
            purged["explicit_event_holdout"] += 1
        else:
            splits[name].append(row)
    if any_events:
        later = set()
        for name in ("test", "validation", "train"):
            kept = [r for r in splits[name] if r.enso_event_id not in later]
            purged["event_overlap"] += len(splits[name]) - len(kept)
            later.update(r.enso_event_id for r in splits[name])
            splits[name] = kept
    if holdout_events:
        kept = [r for r in splits["test"] if r.enso_event_id in holdout_events]
        purged["test_outside_requested_events"] = len(splits["test"]) - len(kept)
        splits["test"] = kept
        absent_test = holdout_events - {r.enso_event_id for r in kept}
        if absent_test:
            raise ValueError(f"Requested events have no test rows: {sorted(absent_test)}")
    for name, part in splits.items():
        if not part:
            raise ValueError(f"{name} is empty after purging; choose sufficient dates/events")
    regions = {r.region for r in splits["train"]}
    unseen = {r.region for name in ("validation", "test") for r in splits[name]} - regions
    if unseen:
        raise ValueError(f"Held-out regions not represented in training: {sorted(unseen)}")
    return splits, purged


def mean(values):
    return sum(values) / len(values)


def fit_scaler(vectors):
    columns = list(zip(*vectors))
    means = [mean(c) for c in columns]
    scales = [math.sqrt(mean([(v - m) ** 2 for v in c])) for c, m in zip(columns, means)]
    scales = [s if s > 1e-8 else 1.0 for s in scales]
    return {"mean": means, "scale": scales}


def transform(vector, scaler):
    return [(v - m) / s for v, m, s in zip(vector, scaler["mean"], scaler["scale"])]


def numeric_features(row, use_enso=True):
    angle = 2 * math.pi * (row.valid_date.month - 1) / 12
    enso = row.enso_index if use_enso else 0.0
    return [*row.raw, enso, row.lead_days,
            math.sin(angle), math.cos(angle),
            enso * math.sin(angle), enso * math.cos(angle)]


FEATURE_NAMES = ["raw_temp", "raw_precip", "enso", "lead_days", "valid_month_sin",
                 "valid_month_cos", "enso_x_month_sin", "enso_x_month_cos"]


def fit_preprocessor(train_rows, use_enso=True):
    """Never pass validation or test rows here."""
    regions = sorted({r.region for r in train_rows})
    residuals = [[o - p for o, p in zip(r.observed, r.raw)] for r in train_rows]
    climatology = {}
    for region in regions:
        part = [r for r in train_rows if r.region == region]
        climatology[region] = {
            "all_months": [mean([r.observed[k] for r in part]) for k in range(2)],
            "months": {str(month): [mean([r.observed[k] for r in part
                                           if r.valid_date.month == month]) for k in range(2)]
                       for month in sorted({r.valid_date.month for r in part})}}
    return {"regions": regions, "feature_names": FEATURE_NAMES, "use_enso": use_enso,
            "features": fit_scaler([numeric_features(r, use_enso) for r in train_rows]),
            "residuals": fit_scaler(residuals), "climatology": climatology}


def encode_rows(rows, preprocessor):
    regions = preprocessor["regions"]
    if any(r.region not in regions for r in rows):
        raise ValueError("Unknown region: retraining and independent validation required")
    return [transform(numeric_features(r, preprocessor["use_enso"]), preprocessor["features"])
            + [float(r.region == region) for region in regions] for r in rows]


def climate_prediction(row, preprocessor):
    climate = preprocessor["climatology"][row.region]
    return climate["months"].get(str(row.valid_date.month), climate["all_months"])


def check_manifest(path):
    manifest = json.loads(Path(path).read_text())
    for key in ("forecast_source", "observation_source", "temperature_units",
                "precipitation_units", "anomaly_reference", "aggregation_period",
                "enso_source", "enso_availability_method", "region_definitions"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            raise ValueError(f"Manifest requires nonempty string {key}")
    for key in ("enso_available_at_initialization", "anomaly_reference_excludes_heldout_data",
                "forecast_hindcasts_no_future_information"):
        if manifest.get(key) is not True:
            raise ValueError(f"Manifest must explicitly attest {key}=true")
    return manifest


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def split_summary(splits, purged):
    return {"purged_counts": purged, "partitions": {
        name: {"rows": len(rows), "unique_initializations": len({r.init_date for r in rows}),
               "init_min": min(r.init_date for r in rows).isoformat(),
               "init_max": max(r.init_date for r in rows).isoformat(),
               "valid_min": min(r.valid_date for r in rows).isoformat(),
               "valid_max": max(r.valid_date for r in rows).isoformat(),
               "events": sorted({r.enso_event_id for r in rows} - {""}),
               "regions": sorted({r.region for r in rows}),
               "weeks": sorted({r.week for r in rows})}
        for name, rows in splits.items()}}
