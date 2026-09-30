"""Tiny artificial fixtures test software only; they are not forecast evidence."""
import csv
from dataclasses import replace
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from weathercal.data import (Row, REQUIRED, load_rows, split_rows, fit_preprocessor,
                             encode_rows, fit_scaler, climate_prediction, check_manifest)
from weathercal.metrics import rmse, evaluate


def row(init="2010-01-01", event="", **changes):
    init = date.fromisoformat(init)
    original = Row(init, init + timedelta(days=20), "CONUS", 1., 2., .8, 2., 4., event)
    return replace(original, **changes)


def partition_fixture():
    return [row("2010-01-01", "A"), row("2012-01-01", "B"), row("2014-01-01", "C")]


class DataTests(unittest.TestCase):
    def csvfile(self, rows):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "test.csv"
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=REQUIRED)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def rawdict(self, **values):
        return {"init_date": "2010-01-01", "valid_date": "2010-01-21", "region": "CONUS",
                **{k: 1 for k in REQUIRED[3:]}, **values}

    def test_valid_input(self):
        rows = load_rows(self.csvfile([self.rawdict()]))
        self.assertEqual(rows[0].week, 3)

    def test_bad_inputs_fail(self):
        for change in ({"enso_index": "nan"}, {"raw_temp_anomaly": "inf"},
                       {"region": " "}, {"valid_date": "2010-01-10"},
                       {"valid_date": "2010-03-20"}, {"init_date": "20100101"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                load_rows(self.csvfile([self.rawdict(**change)]))

    def test_duplicate_fails(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            load_rows(self.csvfile([self.rawdict(), self.rawdict()]))

    def test_boundary_purging(self):
        rows = partition_fixture() + [row("2011-12-20", "D"), row("2013-12-20", "E")]
        splits, purged = split_rows(rows, date(2012, 1, 1), date(2014, 1, 1))
        self.assertEqual(purged["boundary"], 2)
        self.assertEqual([len(v) for v in splits.values()], [1, 1, 1])
        self.assertLess(max(r.valid_date for r in splits["train"]), date(2012, 1, 1))

    def test_observation_latency_is_purged(self):
        rows = partition_fixture() + [row("2011-12-01", "D")]
        _, purged = split_rows(rows, date(2012, 1, 1), date(2014, 1, 1), 14)
        self.assertEqual(purged["boundary"], 1)

    def test_whole_event_overlap_is_purged(self):
        rows = partition_fixture() + [row("2011-09-01", "B"), row("2013-08-01", "C")]
        splits, purged = split_rows(rows, date(2012, 1, 1), date(2014, 1, 1))
        self.assertEqual(purged["event_overlap"], 2)
        ids = [{r.enso_event_id for r in rows} for rows in splits.values()]
        self.assertFalse(ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])

    def test_explicit_event_selection(self):
        rows = partition_fixture() + [row("2015-01-01", "D")]
        splits, purged = split_rows(rows, date(2012, 1, 1), date(2014, 1, 1), holdout_events=["C"])
        self.assertEqual({r.enso_event_id for r in splits["test"]}, {"C"})
        self.assertEqual(purged["test_outside_requested_events"], 1)

    def test_invalid_event_and_empty_split(self):
        for ids in (["missing"], ["A"]):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                split_rows(partition_fixture(), date(2012, 1, 1), date(2014, 1, 1), holdout_events=ids)
        with self.assertRaises(ValueError):
            split_rows([row()], date(2012, 1, 1), date(2014, 1, 1))

    def test_unknown_region_rejected(self):
        rows = partition_fixture()
        rows[-1] = replace(rows[-1], region="unseen")
        with self.assertRaisesRegex(ValueError, "regions"):
            split_rows(rows, date(2012, 1, 1), date(2014, 1, 1))

    def test_fit_uses_training_rows_only(self):
        training = [row(observed_temp_anomaly=2.), row("2010-02-01", observed_temp_anomaly=4.)]
        pre = fit_preprocessor(training)
        before = json.dumps(pre, sort_keys=True)
        heldout = row("2014-07-01", observed_temp_anomaly=99999.)
        encode_rows([heldout], pre)
        self.assertEqual(json.dumps(pre, sort_keys=True), before)
        self.assertEqual(climate_prediction(heldout, pre)[0], 3.)
        self.assertEqual(pre["residuals"]["mean"][0], 2.)

    def test_constant_feature_stability(self):
        self.assertEqual(fit_scaler([[2], [2]])["scale"], [1.0])

    def test_no_enso_ablation_masks_all_enso_inputs(self):
        pre = fit_preprocessor([row()], use_enso=False)
        a = encode_rows([row(enso_index=-20)], pre)
        b = encode_rows([row(enso_index=20)], pre)
        self.assertEqual(a, b)

    def test_provenance_cannot_be_silently_asserted(self):
        template = Path(__file__).parents[1] / "examples/provenance.template.json"
        with self.assertRaisesRegex(ValueError, "explicitly attest"):
            check_manifest(template)


class MetricTests(unittest.TestCase):
    def test_rmse_exact(self):
        scores = rmse([[2, 4], [4, 8]], [[1, 2], [3, 6]])
        self.assertEqual(scores, {"temperature_rmse": 1., "precipitation_rmse": 2.})

    def test_metric_bad_inputs(self):
        for observed, predicted in [([], []), ([[1, 2]], []), ([[1, 2]], [[float("nan"), 2]])]:
            with self.subTest(), self.assertRaises(ValueError):
                rmse(observed, predicted)

    def test_group_counts_and_weeks(self):
        rows = [row(), row("2010-02-01", enso_index=-1)]
        result = evaluate(rows, {"raw": [r.raw for r in rows]})
        self.assertEqual(result["overall"]["rows"], 2)
        self.assertEqual(result["week_3"]["rows"], 2)
        self.assertEqual(result["enso:cold"]["rows"], 1)


@unittest.skipUnless(importlib.util.find_spec("torch"), "PyTorch is not installed; neural execution unverified")
class NeuralSmokeTests(unittest.TestCase):
    def test_two_epoch_training_creates_finite_artifacts(self):
        # Artificial values for execution testing only. Never publish these as skill.
        from argparse import Namespace
        from weathercal.train import train_experiment
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / "fixture.csv"
            with path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=REQUIRED)
                writer.writeheader()
                for year in [2010, 2012, 2014]:
                    for day in range(1, 5):
                        init = date(year, 1, day)
                        writer.writerow({"init_date": str(init), "valid_date": str(init + timedelta(days=20)),
                                         "region": "CONUS", "raw_temp_anomaly": day / 10,
                                         "raw_precip_anomaly": day / 20, "enso_index": .7,
                                         "observed_temp_anomaly": day / 10 + .2,
                                         "observed_precip_anomaly": day / 20 - .1})
            manifest = json.loads((Path(__file__).parents[1] / "examples/provenance.template.json").read_text())
            manifest = {k: True if isinstance(v, bool) else "ARTIFICIAL TEST FIXTURE ONLY" for k, v in manifest.items()}
            manifest_path = folder / "provenance.json"
            manifest_path.write_text(json.dumps(manifest))
            args = Namespace(csv=str(path), manifest=str(manifest_path), output=str(folder / "run"),
                             validation_start=date(2012, 1, 1), test_start=date(2014, 1, 1),
                             observation_lag_days=0, holdout_events=[], epochs=2, patience=2,
                             batch_size=4, width=8, dropout=0., lr=.001, weight_decay=.0001,
                             seed=42, threads=1, max_minutes=1, no_enso=False)
            report = train_experiment(args)
            self.assertEqual(report["runtime"]["device"], "cpu")
            self.assertTrue((folder / "run/model.pt").is_file())
            self.assertEqual(report["metrics"]["test"]["overall"]["rows"], 4)
            self.assertGreater(report["runtime"]["parameter_count"], 0)


if __name__ == "__main__":
    unittest.main()
