import importlib.util,json,pathlib,tempfile,unittest
root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('archive',root/'ingestion/archive_forecasts.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ArchiveTest(unittest.TestCase):
 def test_immutable(self):
  with tempfile.TemporaryDirectory() as tmp:
   src=root/'dist/data/ensemble-percentiles.json';p=module.archive_product(src,tmp);first=p.read_bytes();module.archive_product(src,tmp)
   self.assertEqual(first,p.read_bytes());j=json.loads(first);self.assertEqual(len(j['locations']),10);self.assertEqual(len(j['locations'][0]['periods']),9)
   self.assertEqual(j['locations'][0]['periods'][-1]['sampleCountPerMember'],16)
   self.assertEqual(len(json.loads((pathlib.Path(tmp)/'index.json').read_text())['issuances']),1)
if __name__=='__main__':unittest.main()
