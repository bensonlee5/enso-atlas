import base64,gzip,unittest
import numpy as np
import sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ingestion/global'))
from build_fine import interval,pack
class FineTest(unittest.TestCase):
 def test_difference(self):
  d,q=interval(np.array([1.,1.,1.,float('nan'),-1.,0.]),np.array([2.,.99,.9,2.,2.,-.001]),.01,.01)
  np.testing.assert_allclose(d[:2],[1,0]);self.assertTrue(np.isnan(d[2:5]).all());self.assertEqual(d[5],0);self.assertEqual(q['missingCells'],3);self.assertEqual(q['packingNoiseClampedCells'],2)
 def test_packed_roundtrip(self):
  values=np.array([-80.,0.,27.34,100.,float('nan')]);q=np.frombuffer(gzip.decompress(base64.b64decode(pack(values))),dtype='<i2')
  self.assertEqual(q.tolist(),[-800,0,273,1000,-32768]);self.assertLessEqual(abs(q[2]*.1-values[2]),.05)
 def test_overflow(self):
  with self.assertRaises(ValueError):pack(np.array([4000.]))
if __name__=='__main__':unittest.main()
