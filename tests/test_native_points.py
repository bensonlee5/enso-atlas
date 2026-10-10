import unittest,json,pathlib,sys,numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'ingestion/ensemble'))
from native_points import nearest_points,CITIES
from quantiles import member_quantiles
class NativePoints(unittest.TestCase):
 def test_gaussian_palo_alto_distance_and_sample_agreement(self):
  rows=np.degrees(np.arcsin(np.polynomial.legendre.leggauss(190)[0]));cols=(np.arange(384)*360/384+180)%360-180
  lons,lats=np.meshgrid(cols,rows);idx,points=nearest_points(lats.ravel(),lons.ravel(),CITIES);p=next(p for p in points if p['name']=='Palo Alto')
  self.assertAlmostEqual(p['nativeGridCoordinate'][0],37.322684,places=5);self.assertAlmostEqual(p['distanceKm'],27.138,places=2)
  source=json.loads((ROOT/'dist/data/ensemble-percentiles.json').read_text());self.assertLess(max(min(abs(rows-c[0])) for c in source['gridCoordinates']),.000051)
  self.assertTrue(any(p['requestedCoordinate'][0]<0 for p in points));self.assertEqual(len(idx),20);self.assertEqual(p['nativeCellLongitudeHalfWidth'],.46875)
 def test_same_member_mean_quantile_semantics(self):
  means=np.arange(16*20).reshape(16,20)/10;quantiles=member_quantiles(means)
  self.assertEqual(len(quantiles['p50']),20);self.assertAlmostEqual(quantiles['p50'][0],15)
if __name__=='__main__':unittest.main()
