"""SYNTHETIC UNIT FIXTURES ONLY. Nothing in this file is observed weather evidence."""
import copy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ingestion'))
import verify_forecasts as v

UTC = timezone.utc


def synthetic_issuance(with_partial=True):
    run = datetime(2025, 1, 1, tzinfo=UTC)
    periods = []
    for lead in range(1, 10 if with_partial else 9):
        days = 4 if lead == 9 else 7
        periods.append({'leadWeek': lead, 'intervalStart': v.iso(run + timedelta(days=(lead-1)*7)), 'intervalEndExclusive': v.iso(run + timedelta(days=(lead-1)*7+days)), 'firstSampleHour': (lead-1)*168+6, 'lastSampleHour': (lead-1)*168+days*24, 'sampleCountPerMember': days*4, 'temperature': {'p10': 19, 'p50': 22, 'p90': 25}, 'precipitationRate': {'p10': 0, 'p50': 1, 'p90': 2}})
    return {'schemaVersion':1, 'run':v.iso(run), 'archivedAt':v.iso(run+timedelta(hours=1)), 'model':'NOAA CFSv2', 'memberCount':4, 'sourceProductSha256':'a'*64, 'units':{'temperature':'°C','precipitationRate':'mm/day'}, 'sources':['https://example.invalid/SYNTHETIC-UNIT-TEST-ONLY'], 'locations':[{'name':'SYNTHETIC TEST LOCATION', 'requestedCoordinate':[38.25,-121.75], 'nativeGridCoordinate':[38.2676,-121.8753], 'gridIndex':188,'periods':periods}], '_archivePath':'SYNTHETIC-TEST.json','_archiveSha256':'b'*64}


class SyntheticFixtureProvider:
    kind='synthetic_unit_test_fixture'
    def __init__(self, missing=None, value=20):
        self.missing=missing or set()
        self.value=value
        self.provenance=[]
        self.errors=[]
        self.latest_available_dates={}
        self.requested=[]
    def prepare(self, requests):
        self.requested=requests
    def daily(self, point, day):
        return None if day in self.missing else self.value


class VerificationTests(unittest.TestCase):
    def test_before_maturity_no_network_or_metrics(self):
        source=SyntheticFixtureProvider()
        d=v.build_report([synthetic_issuance()],v.utc('2025-01-10T23:59:59Z'),source)
        self.assertEqual(d['counts']['pending'],9)
        self.assertEqual(source.requested,[])
        self.assertIsNone(d['temperature']['overall']['mae'])

    def test_three_full_days_and_seven_observations(self):
        d=v.build_report([synthetic_issuance()],v.utc('2025-01-11T00:00:00Z'),SyntheticFixtureProvider())
        self.assertEqual(d['counts']['verified'],1)
        self.assertEqual(d['temperature']['overall'],{'n':1,'bias':2,'mae':2,'rmse':2})
        self.assertIn('SYNTHETIC',d['warnings'][0])
        self.assertEqual(d['temperature']['pairs'][0]['daysObserved'],7)
        self.assertTrue(d['temperature']['pairs'][0]['archivedAfterValidStart'])
        self.assertFalse(d['temperature']['pairs'][1]['archivedAfterValidStart'])

    def test_missing_one_day_is_not_scored(self):
        d=v.build_report([synthetic_issuance()],v.utc('2025-01-11T00:00:00Z'),SyntheticFixtureProvider({date(2025,1,3)}))
        self.assertEqual(d['counts']['missingObservations'],1)
        self.assertEqual(d['counts']['verified'],0)
        self.assertEqual(d['temperature']['pairs'][0]['missingDates'],['2025-01-03'])
        self.assertEqual(d['status'],'observations_unavailable')

    def test_missing_or_nonfinite_never_becomes_zero(self):
        for value in (None,float('nan'),float('inf')):
            d=v.build_report([synthetic_issuance()],v.utc('2025-01-11T00:00:00Z'),SyntheticFixtureProvider(value=value))
            self.assertEqual(d['counts']['verified'],0)
            json.dumps(d,allow_nan=False)

    def test_signed_bias(self):
        d=v.metrics([-2,4])
        self.assertEqual(d['bias'],1)
        self.assertEqual(d['mae'],3)
        self.assertAlmostEqual(d['rmse'],10**.5)

    def test_partial_period_is_separate(self):
        d=v.build_report([synthetic_issuance()],v.utc('2025-03-06T00:00:00Z'),SyntheticFixtureProvider())
        self.assertEqual(d['counts']['verified'],9)
        self.assertEqual(d['temperature']['overall']['n'],8)
        self.assertEqual(d['temperature']['partialDays57to60']['n'],1)
        self.assertEqual(d['temperature']['pairs'][-1]['daysExpected'],4)
        self.assertEqual(len(d['temperature']['byLead']),8)
        self.assertEqual(d['precipitation']['status'],'incompatible_statistic')
        self.assertIsNone(d['precipitation']['rmse'])

    def test_archive_timestamp_after_asof_excluded(self):
        d=v.build_report([synthetic_issuance()],v.utc('2025-01-01T00:30:00Z'),SyntheticFixtureProvider())
        self.assertEqual(d['counts']['invalidAsOf'],9)
        self.assertEqual(d['counts']['verified'],0)

    def test_latency_cannot_be_reduced(self):
        with self.assertRaises(ValueError):
            v.build_report([],v.utc('2025-01-01T00:00:00Z'),SyntheticFixtureProvider(),2)

    def test_empty_archive(self):
        d=v.build_report([],v.utc('2025-01-01T00:00:00Z'),SyntheticFixtureProvider())
        self.assertEqual(d['status'],'no_archived_forecasts')
        self.assertEqual(d['counts']['temperatureForecasts'],0)

    def write_archive(self, root, issuance=None):
        issuance=issuance or synthetic_issuance()
        raw=json.dumps(issuance).encode()
        (root/'one.json').write_bytes(raw)
        index={'schemaVersion':1,'issuances':[{'run':issuance['run'],'path':'one.json','sha256':hashlib.sha256(raw).hexdigest(),'archivedAt':issuance['archivedAt']}]}
        (root/'index.json').write_text(json.dumps(index))
        return index

    def test_valid_immutable_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.write_archive(root)
            self.assertEqual(len(v.load_archive(root)),1)

    def test_lagged_member_identity_validation(self):
        for count in (4, 8, 12, 16):
            item = synthetic_issuance()
            run = v.utc(item['run'])
            days = count // 4
            item.update(memberCount=count, lagDays=days, laggedEnsemble=days > 1,
                        initializationRange=[v.iso(run-timedelta(days=days-1)), v.iso(run)])
            item['members'] = [{'id':(run-timedelta(days=day)).strftime('%Y%m%d%H')+'/'+member,
                                'member':member, 'initialization':v.iso(run-timedelta(days=day))}
                               for day in range(days) for member in ('01','02','03','04')]
            item['memberIDs'] = [m['id'] for m in item['members']]
            v.validate_ensemble(item, run)
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);self.write_archive(root,item)
                self.assertEqual(v.load_archive(root)[0]['memberCount'],count)
            duplicate=copy.deepcopy(item);duplicate['members'][-1]=duplicate['members'][0]
            duplicate['memberIDs'][-1]=duplicate['memberIDs'][0]
            with self.assertRaisesRegex(ValueError,'Duplicate'):v.validate_ensemble(duplicate,run)
            wrong_range=copy.deepcopy(item);wrong_range['initializationRange'][0]=v.iso(run-timedelta(days=days))
            with self.assertRaisesRegex(ValueError,'range'):v.validate_ensemble(wrong_range,run)
            wrong_id=copy.deepcopy(item);wrong_id['members'][0]['initialization']=v.iso(run+timedelta(days=1))
            with self.assertRaisesRegex(ValueError,'identity'):v.validate_ensemble(wrong_id,run)
        for count in (8,12,16):
            item=synthetic_issuance();item['memberCount']=count
            with self.assertRaises(ValueError):v.validate_ensemble(item,v.utc(item['run']))

    def test_current_product_archive_roundtrip(self):
        # Production data is read-only input; all generated archives stay temporary.
        from archive_forecasts import archive_product
        product=Path(__file__).resolve().parents[1]/'dist/data/ensemble-percentiles.json'
        original=json.loads(product.read_text())
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=archive_product(product,root);first=path.read_bytes()
            issuance=v.load_archive(root)[0]
            self.assertEqual(issuance['memberCount'],original['memberCount'])
            self.assertEqual(issuance.get('members'),original.get('members'))
            self.assertEqual(issuance.get('initializationRange'),original.get('initializationRange'))
            self.assertEqual(issuance.get('provenance'),original.get('provenance'))
            archive_product(product,root)
            self.assertEqual(path.read_bytes(),first)
            report=v.build_report([issuance],v.utc(issuance['archivedAt']),SyntheticFixtureProvider())
            self.assertEqual(report['temperature']['memberCounts'],[original['memberCount']])
            self.assertNotIn('Four-member',report['temperature']['forecastStatistic'])

    def test_tampered_archive_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.write_archive(root)
            with (root/'one.json').open('a') as file:file.write(' ')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):v.load_archive(root)

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);index=self.write_archive(root)
            index['issuances'][0]['path']='../outside.json';(root/'index.json').write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError,'inside archive-dir'):v.load_archive(root)

    def test_duplicate_initialization_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);index=self.write_archive(root)
            index['issuances'].append(index['issuances'][0]);(root/'index.json').write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError,'Duplicate'):v.load_archive(root)

    def test_invalid_temporal_statistics_rejected(self):
        for key,value in [('sampleCountPerMember',27),('intervalEndExclusive','2025-01-09T00:00:00Z')]:
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);item=synthetic_issuance();item['locations'][0]['periods'][0][key]=value;self.write_archive(root,item)
                with self.assertRaises(ValueError):v.load_archive(root)

    def test_nonfinite_quantile_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);item=synthetic_issuance();item['locations'][0]['periods'][0]['temperature']['p50']=float('nan');self.write_archive(root,item)
            with self.assertRaises(ValueError):v.load_archive(root)

    def test_nearest_native_grid(self):
        self.assertEqual(v.CPCProvider.nearest_grid((38.2676,-121.8753)),(103,476,38.25,238.25))
        self.assertEqual(v.CPCProvider.nearest_grid((25.9842,-79.6879)),(128,560,25.75,280.25))

    def test_noaa_failure_yields_gap_not_fake_score(self):
        source=v.CPCProvider()
        with patch.object(source,'request',side_effect=OSError('TEST SOURCE OUTAGE')):
            d=v.build_report([synthetic_issuance()],v.utc('2025-01-11T00:00:00Z'),source)
        self.assertEqual(d['counts']['verified'],0)
        self.assertEqual(d['counts']['missingObservations'],1)
        self.assertEqual(len(d['sourceErrors']),2)

    def test_network_budget_enforced_before_fetch(self):
        source=v.CPCProvider();source.deadline=0
        with self.assertRaisesRegex(TimeoutError,'budget exhausted'):
            source.request(v.SOURCE_ROOT+'/tmax.2025.nc.das')

    def test_source_target_allowlist(self):
        with self.assertRaises(ValueError):v.CPCProvider().request('https://example.invalid')

    def test_tmax_lower_than_tmin_rejected(self):
        source=v.CPCProvider();point=(1,1);day=date(2025,1,1)
        source._points[(point,day,'tmax')]=10;source._points[(point,day,'tmin')]=20
        self.assertIsNone(source.daily(point,day))

    def test_ascii_parser(self):
        # Synthetic scalar-grid response; dates use genuine NetCDF convention, values are invented.
        text='Dataset {}\n-----\ntmax.tmax[2][1][1]\n[0][0], 10\n[1][0], -9.96921E36\n\ntmax.time[2]\n0, 24\n\ntmax.lat[1]\n38.25\n\ntmax.lon[1]\n238.25\n'
        times,values,point=v.parse_ascii(text,'tmax')
        self.assertEqual(times,[0,24]);self.assertEqual(values,[10,-9.96921e36]);self.assertEqual(point,(38.25,238.25))
        with self.assertRaises(ValueError):v.parse_ascii(text.replace('[1][0]','[2][0]'),'tmax')
        with self.assertRaises(ValueError):v.parse_ascii(text.replace('[2][1][1]','[2][2][1]'),'tmax')

    def test_report_strict_json_roundtrip(self):
        d=v.build_report([synthetic_issuance()],v.utc('2025-01-11T00:00:00Z'),SyntheticFixtureProvider())
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json';v.write_report(path,d);self.assertEqual(json.loads(path.read_text()),d)


if __name__=='__main__':unittest.main()
