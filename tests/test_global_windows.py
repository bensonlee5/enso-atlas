"""Window labels must preserve off-midnight CFS initialization times."""
import datetime,importlib.util,pathlib,sys,types,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('global_window_test',ROOT/'ingestion/global/extract_global.py')
module=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'eccodes':types.ModuleType('eccodes')}):spec.loader.exec_module(module)

class GlobalWindowTests(unittest.TestCase):
 def test_all_cycle_hours_and_rollover(self):
  for hour in (0,6,12,18):
   for day in (0,1,59):
    start=datetime.datetime(2026,10,2,hour,tzinfo=datetime.timezone.utc)
    window=module.cfs_daily_window(start,day)
    expected=start+datetime.timedelta(days=day)
    self.assertEqual(window['intervalStart'],expected.isoformat())
    self.assertEqual(window['intervalEndExclusive'],(expected+datetime.timedelta(days=1)).isoformat())
    self.assertEqual(window['firstSampleTime'],(expected+datetime.timedelta(hours=6)).isoformat())
    self.assertEqual(window['lastSampleTime'],window['intervalEndExclusive'])
    self.assertEqual(window['firstSampleHour'],day*24+6)
    self.assertEqual(window['lastSampleHour'],(day+1)*24)
    self.assertEqual(window['date'],expected.date().isoformat())

if __name__=='__main__':unittest.main()
