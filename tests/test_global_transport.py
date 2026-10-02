import copy,json,pathlib,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ingestion/ensemble'))
from transport import separate_member_means,validate_member_artifact,KEYS
class GlobalTransportTest(unittest.TestCase):
 def test_shipped_worldwide_artifact_and_budget(self):
  path=ROOT/'dist/data/ensemble-percentiles.json';p=json.loads(path.read_text())
  self.assertLess(path.stat().st_size,4500000)
  self.assertEqual(p['memberCount'],16);self.assertEqual(len(p['gridCoordinates']),4704)
  self.assertEqual(p['coverage'],'global');self.assertEqual(len(p['provenance']),32)
  for w in p['weeks']+[p['remainingDays57to60']]:self.assertNotIn('memberMeans',w)
  artifact=validate_member_artifact(p,path.parent)
  self.assertEqual(len(artifact['periods']),9)
  for lat,lon in [(51,0),(35,140),(-34,151),(-34,18),(-24,-47),(0,180),(0,-180),(85,0),(-85,0)]:
   i=min(range(len(p['gridCoordinates'])),key=lambda i:(p['gridCoordinates'][i][0]-lat)**2+(((p['gridCoordinates'][i][1]-lon+180)%360)-180)**2)
   for frame in p['weeks']+[p['remainingDays57to60']]:
    values=[frame['temperature'][q][i] for q in KEYS];self.assertEqual(values,sorted(values))
 def test_tampering_member_means_or_quantiles_rejected(self):
  p=json.loads((ROOT/'dist/data/ensemble-percentiles.json').read_text())
  p['weeks'][0]['temperature']['p50'][0]+=1
  with self.assertRaisesRegex(AssertionError,'authentic member'):validate_member_artifact(p,ROOT/'dist/data')
if __name__=='__main__':unittest.main()
