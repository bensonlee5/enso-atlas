"""Storage protocol tests use tiny fabricated protocol bytes, never forecast values."""
import copy,gzip,hashlib,importlib.util,json,pathlib,sys,tempfile,types,unittest,urllib.error,urllib.request
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ingestion'))
import publish_forecasts as p
from ensemble.transport import validate_member_artifact

class MemoryClient:
 def __init__(self):self.objects={};self.manifest=None;self.etag=None;self.calls=[];self.fail_path=None;self.conflict=False;self.readback_wrong=False
 def request(self,path,method='GET',body=None,headers=None,limit=p.MAX_MANIFEST_BYTES,authenticated=False,**kw):
  self.calls.append((path,method,authenticated,headers));headers=headers or {}
  if path==self.fail_path:raise RuntimeError('Simulated upstream failure')
  if path==p.API+'/manifest':
   return (200,{'ETag':self.etag},p.canonical(self.manifest)) if self.manifest else (404,{},b'')
  if path==p.API+'/promote':
   if self.conflict or headers.get('If-Match')!=self.etag or (self.manifest is None and headers.get('If-None-Match')!='*'):return 412,{},b''
   self.manifest=json.loads(body);self.etag='"'+self.manifest['releaseID']+'"';return 200,{},b'{}'
  if method=='PUT':self.objects[path]=body;return 201,{},b'{}'
  data=self.objects.get(path)
  return (200,{},b'' if method=='HEAD' else data) if data is not None else (404,{},b'')

def seed(folder):
 folder.mkdir(exist_ok=True)
 for name in p.BROWSER_FILES:(folder/name).write_bytes(p.canonical({'fixture':'protocol only','name':name}))
 (folder/p.AUDIT).write_bytes(b'protocol-test-audit-bytes')
 (folder/'archive').mkdir();(folder/'archive/index.json').write_bytes(p.canonical({'schemaVersion':1,'issuances':[]}))
 m={'schemaVersion':1,'generatedAt':'2026-10-02T00:00:00Z','files':{n:p.metadata((folder/n).read_bytes()) for n in p.BROWSER_FILES},'initializations':{k:'2026-10-02T00:00:00Z' for k in ('raw','anomaly','ensemble','ensoObservation','globalCfs','aifs')}}
 (folder/'refresh-manifest.json').write_bytes(p.canonical(m))
 return p.build_manifest(folder)

class ForecastStorageTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name);self.folder=self.root/'data';self.manifest=seed(self.folder);self.state=self.root/'state.json';self.client=MemoryClient()
  with patch.object(p,'bootstrap_archives'):p.restore(self.client,self.folder,self.state,True)
 def tearDown(self):self.temp.cleanup()
 def test_publish_restore_idempotency(self):
  m=p.publish(self.client,self.folder,self.state)
  self.assertEqual(m['releaseID'],self.manifest['releaseID']);self.assertTrue(all(c[2] for c in self.client.calls if c[1] in ('PUT','POST')))
  dest=self.root/'restored';p.restore(self.client,dest,self.state)
  before=len(self.client.calls);p.publish(self.client,dest,self.state);self.assertEqual(len(self.client.calls),before+1)
  self.assertEqual((dest/p.AUDIT).read_bytes(),(self.folder/p.AUDIT).read_bytes())
 def test_failed_upload_never_promotes(self):
  name=sorted(self.manifest['objects'])[0];self.client.fail_path=p.object_path(name,self.manifest['objects'][name])
  with self.assertRaisesRegex(RuntimeError,'Simulated'):p.publish(self.client,self.folder,self.state)
  self.assertIsNone(self.client.manifest);self.assertFalse(any(c[1]=='POST' for c in self.client.calls))
 def test_cas_conflict_does_not_retry_with_new_predecessor(self):
  self.client.conflict=True
  with self.assertRaisesRegex(RuntimeError,'Manifest race'):p.publish(self.client,self.folder,self.state)
  self.assertEqual(sum(c[1]=='POST' for c in self.client.calls),1)
 def test_missing_feed_requires_explicit_bootstrap(self):
  with self.assertRaisesRegex(RuntimeError,'explicitly'):p.restore(self.client,self.root/'absent',self.state)
 def test_tampered_restore_keeps_previous_local_files(self):
  p.publish(self.client,self.folder,self.state)
  name=next(iter(self.manifest['objects']));self.client.objects[p.object_path(name,self.manifest['objects'][name])]=b'broken'
  target=self.root/'keep';target.mkdir();(target/'sentinel').write_text('old')
  with self.assertRaisesRegex(ValueError,'digest mismatch'):p.restore(self.client,target,self.state)
  self.assertEqual(list(x.name for x in target.iterdir()),['sentinel'])
 def test_paths_sizes_and_release_integrity(self):
  for name in ('../secret','archive/../../secret','archive/2026100206.json','x.py','archive/index.json/extra'):
   self.assertFalse(p.allowed_name(name))
  for alter in ('hash','size','name','browser'):
   m=copy.deepcopy(self.manifest);name=next(iter(m['objects']))
   if alter=='hash':m['objects'][name]['sha256']='0'*64
   elif alter=='size':m['objects'][name]['bytes']=p.MAX_FILE_BYTES+1
   elif alter=='name':m['objects']['../outside']=m['objects'].pop(name)
   else:m['files']={}
   with self.assertRaises(ValueError):p.validate_manifest(m)
 def test_fixed_origin_and_redirects(self):
  with self.assertRaises(ValueError):p.Client('https://evil.example')
  with self.assertRaises(urllib.error.HTTPError):p.NoRedirect().redirect_request(urllib.request.Request(p.SITE),None,302,'redirect',{},'https://evil.example')
 def test_timestamp_only_change_has_same_release(self):
  m=json.loads((self.folder/'refresh-manifest.json').read_text());m['generatedAt']='2026-10-03T00:00:00Z';(self.folder/'refresh-manifest.json').write_bytes(p.canonical(m))
  self.assertEqual(p.build_manifest(self.folder)['releaseID'],self.manifest['releaseID'])
 def test_bootstrap_archive_tamper_rejected_before_write(self):
  with self.assertRaisesRegex(ValueError,'hash mismatch'):p.bootstrap_archives(self.root/'migration',lambda name:b'changed')
  self.assertFalse((self.root/'migration/archive').exists())
 def test_workflow_scopes_upload_identity_and_frequency(self):
  source=(ROOT/'.github/workflows/refresh-weather.yml').read_text();prepare,publish=source.split('\n  publish:\n')
  self.assertNotIn('id-token: write',prepare);self.assertIn('id-token: write',publish)
  self.assertNotIn('pip install',publish);self.assertIn('artifact-ids: ${{ needs.prepare.outputs.artifact-id }}',publish)
  self.assertIn("cron: '17 15 * * *'",source);self.assertIn("cron: '17 3,9,21 * * *'",source);self.assertIn('retention-days: 1',source)
  self.assertNotIn('git push',source);self.assertNotIn('contents: write',source)
 def test_unchanged_raw_and_global_cycle_skips_grib_download(self):
  # Exercise the early reuse path without needing native decoder packages.
  dependency=types.ModuleType('download_process')
  dependency.get=lambda *a,**k: (_ for _ in ()).throw(AssertionError('Unexpected download'))
  dependency.decode=lambda *a,**k: (_ for _ in ()).throw(AssertionError('Unexpected decode'))
  spec=importlib.util.spec_from_file_location('refresh_skip_test',ROOT/'ingestion/refresh.py');module=importlib.util.module_from_spec(spec)
  with patch.dict(sys.modules,{'download_process':dependency,'h5py':types.ModuleType('h5py')}):spec.loader.exec_module(module)
  module.discover_cfs=lambda:('20261002','00',[],[])
  previous={'run':'2026-10-02T00:00:00Z'};global_file=self.root/'global.json';global_file.write_text(json.dumps({'run':'2026-10-02T00:00:00+00:00'}))
  self.assertIs(module.raw(self.root,previous,global_file),previous)
 def test_compressed_artifact_expansion_is_bounded(self):
  body=gzip.compress(b'0'*20_000_001,mtime=0);(self.folder/p.AUDIT).write_bytes(body)
  product={'memberMeansArtifact':{'file':p.AUDIT,'format':'gzip-json','decimalPlaces':6,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}}
  with self.assertRaisesRegex(AssertionError,'bounded size'):validate_member_artifact(product,self.folder)

if __name__=='__main__':unittest.main()
