"""Unweighted paired RMSE. No independence or significance claim is implied."""
from collections import defaultdict
import math


def rmse(observed, predicted):
    if not observed or len(observed) != len(predicted):
        raise ValueError("Need nonempty, paired observations and predictions")
    if any(len(v) != 2 for v in [*observed, *predicted]):
        raise ValueError("Expected temperature and precipitation pairs")
    if not all(math.isfinite(x) for pair in [*observed, *predicted] for x in pair):
        raise ValueError("Metrics require finite values")
    return {name: math.sqrt(sum((a[k] - b[k]) ** 2 for a, b in zip(observed, predicted))
                           / len(observed))
            for k, name in enumerate(("temperature_rmse", "precipitation_rmse"))}


def evaluate(rows, predictions):
    if any(len(p) != len(rows) for p in predictions.values()):
        raise ValueError("Every model needs one prediction per row")
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        phase = "warm" if row.enso_index >= .5 else "cold" if row.enso_index <= -.5 else "neutral"
        for group in ("overall", f"week_{row.week}", f"region:{row.region}", f"enso:{phase}"):
            groups[group].append(i)
    results = {}
    for group, indices in sorted(groups.items()):
        results[group] = {"rows": len(indices),
                          "unique_initializations": len({rows[i].init_date for i in indices}),
                          "models": {name: rmse([rows[i].observed for i in indices],
                                                [values[i] for i in indices])
                                     for name, values in predictions.items()}}
    return results
