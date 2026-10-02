"""Stage and validate forecasts; immutable-object publication is a separate step.
Daily refreshes the 00Z lagged ensemble. Fast preserves that exact issuance.
"""
import argparse, datetime as dt, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, math
from archive_forecasts import archive_product
from ensemble.transport import ARTIFACT, validate_member_artifact
ROOT=pathlib.Path(__file__).resolve().parents[1]
FILES=('cfs-weekly-raw-60days.json','cfs-weekly-anomalies.json','enso-observations.json','ensemble-percentiles.json','cfs-global-60days.json','aifs-global-snapshots.json')
def manifest_for(folder):
 products={n:json.loads((folder/n).read_text()) for n in FILES}
 ens=products['ensemble-percentiles.json']
 assert ens['schemaVersion']==3 and ens['coverage']=='global' and ens['sampling']['longitudePeriodic']
 assert 4000<=len(ens['gridCoordinates'])<6000
 assert ens['memberCount'] in (4,8,12,16) and len(set(ens['memberIDs']))==ens['memberCount']
 assert all(frame['memberCount']==ens['memberCount'] for frame in ens['weeks']+[ens['remainingDays57to60']])
 validate_member_artifact(ens,folder)
 assert len(ens['weeks'])==8 and ens['remainingDays57to60']['sampleCountPerMember']==16
 for frame in ens['weeks']+[ens['remainingDays57to60']]:
  for field in ('temperature','precipitationRate'):
   arrays=[frame[field][p] for p in ('p1','p5','p10','p50','p90','p95','p99')]
   assert all(len(a)==len(ens['gridCoordinates']) and all(math.isfinite(v) for v in a) for a in arrays)
   assert all(all(a<=b for a,b in zip(row,row[1:])) for row in zip(*arrays))
 files={name:{'sha256':hashlib.sha256((folder/name).read_bytes()).hexdigest(),'bytes':(folder/name).stat().st_size} for name in (*FILES,*(['verification.json'] if (folder/'verification.json').exists() else []))}
 return {'schemaVersion':1,'generatedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'files':files,'initializations':{'raw':products[FILES[0]]['run'],'anomaly':products[FILES[1]]['initialDate'],'ensemble':ens['run'],'ensoObservation':products[FILES[2]]['observations'][-1]['date'],'globalCfs':products['cfs-global-60days.json']['run'],'aifs':products['aifs-global-snapshots.json']['run']},'source':'Public NOAA and ECMWF products; see each product for exact sources and statistical meaning'}
def copy_previous(previous,stage):
 for name in (*FILES,ARTIFACT,'verification.json'):
  path=previous/name
  if path.exists():shutil.copyfile(path,stage/name)
 if (previous/'archive').exists():shutil.copytree(previous/'archive',stage/'archive')
def run(script,*args,timeout=900):
 env={k:v for k,v in os.environ.items() if not (k.startswith('ACTIONS_') or k in ('GITHUB_TOKEN','GH_TOKEN'))}
 subprocess.run([sys.executable,str(ROOT/'ingestion'/script),*map(str,args)],check=True,timeout=timeout,env=env)
def refresh(output,mode):
 with tempfile.TemporaryDirectory(prefix='enso-noaa-') as tmp:
  tmp=pathlib.Path(tmp);stage=tmp/'data';stage.mkdir();copy_previous(output,stage)
  if mode=='fast' and not all((stage/n).exists() for n in (*FILES,ARTIFACT,'verification.json')):raise ValueError('Fast refresh requires an established complete feed; run a daily bootstrap first')
  run('global/refresh_global.py','--cache-dir',tmp/'aifs-cache','--output',stage/'aifs-global-snapshots.json','--previous',output/'aifs-global-snapshots.json',timeout=450)
  run('refresh.py','--output',stage,'--previous',output,'--global-output',stage/'cfs-global-60days.json','--compare-with',stage/'aifs-global-snapshots.json')
  if mode=='daily':
   cache=tmp/'cfs-cache'
   run('ensemble/retrieve_ensemble.py','--run','latest','--lag-days','4','--days','60','--cache-dir',cache,'--output',stage/'ensemble-percentiles.json','--previous',output/'ensemble-percentiles.json','--locations-file',stage/'cfs-weekly-raw-60days.json','--reference-date',dt.datetime.now(dt.timezone.utc).date().isoformat(),timeout=1500)
   ensemble=json.loads((stage/'ensemble-percentiles.json').read_text())
   previous=json.loads((output/'ensemble-percentiles.json').read_text()) if (output/'ensemble-percentiles.json').exists() else None
   if previous:archive_product(output/'ensemble-percentiles.json',stage/'archive')
   archive_product(stage/'ensemble-percentiles.json',stage/'archive')
   verification=stage/'verification.json';current=json.loads(verification.read_text()) if verification.exists() else {}
   if current.get('generatedAt','')[:10]!=dt.datetime.now(dt.timezone.utc).date().isoformat() or not previous or previous.get('run')!=ensemble['run']:
    run('verify_forecasts.py','--archive-dir',stage/'archive','--output',verification,timeout=600)
  manifest=manifest_for(stage)
  old=json.loads((output/'refresh-manifest.json').read_text()) if (output/'refresh-manifest.json').exists() else None
  if old and old.get('files')==manifest['files'] and old.get('initializations')==manifest['initializations']:manifest['generatedAt']=old['generatedAt']
  (stage/'refresh-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
  subprocess.run(['node',str(ROOT/'tests/public-data-test.cjs'),str(stage)],check=True,timeout=90)
  output.mkdir(parents=True,exist_ok=True)
  for path in stage.rglob('*'):
   if not path.is_file():continue
   dest=output/path.relative_to(stage);dest.parent.mkdir(parents=True,exist_ok=True)
   pending=dest.with_name(dest.name+'.tmp');pending.write_bytes(path.read_bytes());os.replace(pending,dest)
  print(json.dumps({'status':'validated','mode':mode,'initializations':manifest['initializations'],'generatedAt':manifest['generatedAt']}));return manifest
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,default=ROOT/'dist/data');p.add_argument('--mode',choices=('daily','fast'),default='daily');p.add_argument('--manifest-only',action='store_true');a=p.parse_args()
 if a.manifest_only:
  out=manifest_for(a.output);(a.output/'refresh-manifest.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));return
 refresh(a.output,a.mode)
if __name__=='__main__':main()
