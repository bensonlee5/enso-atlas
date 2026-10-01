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

def align_valid_window(values, source_init, reference_init, sample_count=240):
    """Crop older six-hourly series to the same valid instants, never same lead labels."""
    seconds=(reference_init-source_init).total_seconds()
    if seconds<0 or seconds%21600:
        raise ValueError('Initializations must align on nonnegative six-hour boundaries')
    offset=int(seconds//21600)
    values=np.asarray(values,dtype=float)
    if values.ndim!=2 or len(values)<offset+sample_count or not np.isfinite(values).all():
        raise ValueError('Incomplete or nonfinite aligned member window')
    return values[offset:offset+sample_count]
