"""Empirical quantiles from actual member means, never from summary quantiles."""
import numpy as np
QUANTILE_LEVELS = (0.01, 0.05, 0.10, 0.50, 0.90, 0.95, 0.99)
QUANTILE_KEYS = ('p1', 'p5', 'p10', 'p50', 'p90', 'p95', 'p99')
def member_quantiles(means):
    means = np.asarray(means, dtype=float)
    if means.ndim != 2 or means.shape[0] < 2 or not np.isfinite(means).all():
        raise ValueError('Expected finite member-by-location temporal averages')
    values = np.quantile(means, QUANTILE_LEVELS, axis=0, method='linear')
    assert (np.diff(values, axis=0) >= 0).all()
    return {key: row.round(3).tolist() for key, row in zip(QUANTILE_KEYS, values)}
