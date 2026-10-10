import unittest,tempfile,pathlib,json,sys,subprocess,importlib.util,urllib.error
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'ingestion'));import refresh_bundle as bundle
spec=importlib.util.spec_from_file_location('refresh_global',ROOT/'ingestion/global/refresh_global.py');aifs=importlib.util.module_from_spec(spec);spec.loader.exec_module(aifs)
class Resilience(unittest.TestCase):
 def test_failed_product_restores_bytes_and_marks_retained(self):
  with tempfile.TemporaryDirectory() as d:
   folder=pathlib.Path(d);(folder/'a.json').write_text('{"run":"2026-10-09"}');(folder/'audit.gz').write_bytes(b'original')
   def fail(*args,**kwargs):
    (folder/'a.json').write_text('broken');(folder/'audit.gz').write_bytes(b'broken');raise subprocess.CalledProcessError(1,'test')
   with patch.object(bundle,'run',side_effect=fail):self.assertFalse(bundle.refresh_product(folder,['a.json','audit.gz'],'test.py'))
   p=json.loads((folder/'a.json').read_text());self.assertEqual(p['run'],'2026-10-09');self.assertEqual(p['refreshStatus']['state'],'retained');self.assertEqual((folder/'audit.gz').read_bytes(),b'original')
   with patch.object(bundle,'run',return_value=None):self.assertTrue(bundle.refresh_product(folder,['a.json'],'test.py'))
   self.assertEqual(json.loads((folder/'a.json').read_text())['refreshStatus']['state'],'checked')
 def test_invalid_json_output_retains_previous(self):
  with tempfile.TemporaryDirectory() as d:
   folder=pathlib.Path(d);(folder/'a.json').write_text('{"run":"2026-10-09"}')
   def invalid(*args,**kwargs):(folder/'a.json').write_text('invalid')
   with patch.object(bundle,'run',side_effect=invalid):self.assertFalse(bundle.refresh_product(folder,['a.json'],'test.py'))
   self.assertEqual(json.loads((folder/'a.json').read_text())['run'],'2026-10-09')
 def test_bootstrap_fails_closed(self):
  with tempfile.TemporaryDirectory() as d,patch.object(bundle,'run',side_effect=subprocess.CalledProcessError(1,'test')):
   with self.assertRaises(RuntimeError):bundle.refresh_product(pathlib.Path(d),['missing.json'],'test.py')
 def test_rate_limit_bounded_and_respects_retry_after(self):
  err=urllib.error.HTTPError('https://data.ecmwf.int/',429,'limit',{'Retry-After':'90'},None)
  with patch.object(aifs.urllib.request,'urlopen',side_effect=err) as request,patch.object(aifs.time,'sleep') as sleep:
   with self.assertRaises(urllib.error.HTTPError):aifs.get('https://data.ecmwf.int/')
   self.assertEqual(request.call_count,3);self.assertEqual([x.args[0] for x in sleep.call_args_list],[90,90])
  err.headers={'Retry-After':'900'}
  with patch.object(aifs.urllib.request,'urlopen',side_effect=err) as request,patch.object(aifs.time,'sleep') as sleep:
   with self.assertRaises(urllib.error.HTTPError):aifs.get('https://data.ecmwf.int/')
   self.assertEqual(request.call_count,1);sleep.assert_not_called()
if __name__=='__main__':unittest.main()
