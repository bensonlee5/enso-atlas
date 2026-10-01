import pathlib, sys, unittest
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ingestion/ensemble'))
from quantiles import member_quantiles, QUANTILE_KEYS, align_valid_window
class QuantileTests(unittest.TestCase):
    def test_four_members_type7(self):
        actual=member_quantiles([[0,10],[10,20],[20,30],[30,40]])
        self.assertEqual(tuple(actual),QUANTILE_KEYS)
        self.assertEqual([actual[k][0] for k in QUANTILE_KEYS],[.3,1.5,3,15,27,28.5,29.7])
    def test_permutation_and_equal_members(self):
        self.assertEqual(member_quantiles([[5],[5],[5],[5]]),{k:[5.] for k in QUANTILE_KEYS})
        self.assertEqual(member_quantiles([[8],[0],[4],[2]]),member_quantiles([[0],[2],[4],[8]]))
    def test_reject_missing_or_nonfinite_members(self):
        for a in ([[1]],[[1],[float('nan')]], [1,2,3]):
            with self.assertRaises(ValueError):member_quantiles(a)
    def test_lag_alignment_is_valid_time_not_lead(self):
        import datetime as dt
        start=dt.datetime(2026,10,1,tzinfo=dt.timezone.utc)
        newest=np.arange(240,dtype=float).reshape(-1,1)
        older=np.arange(-12,240,dtype=float).reshape(-1,1)
        np.testing.assert_array_equal(align_valid_window(older,start-dt.timedelta(days=3),start),newest)
        with self.assertRaises(ValueError):align_valid_window(older[:240],start-dt.timedelta(days=3),start)
        with self.assertRaises(ValueError):align_valid_window(older,start+dt.timedelta(hours=6),start)
    def test_sixteen_real_means(self):
        values=np.arange(16,dtype=float).reshape(-1,1)
        q=member_quantiles(values)
        self.assertEqual(q['p1'],[.15]);self.assertEqual(q['p50'],[7.5]);self.assertEqual(q['p99'],[14.85])
if __name__=='__main__':unittest.main()
