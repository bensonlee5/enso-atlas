import pathlib, sys, unittest
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ingestion/ensemble'))
from quantiles import member_quantiles, QUANTILE_KEYS
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
if __name__=='__main__':unittest.main()
