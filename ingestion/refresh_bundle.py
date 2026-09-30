"""Generate validated public NOAA data and a hash manifest. Does not push or deploy."""
import argparse, datetime as dt, hashlib, json, os, pathlib, subprocess, sys, tempfile
from archive_forecasts import archive_product
ROOT=pathlib.Path(__file__).resolve().parents[1]
FILES=('cfs-weekly-raw-60days.json','cfs-weekly-anomalies.json','enso-observations.json','ensemble-percentiles.json')
def manifest_for(folder):
 products={n:json.loads((folder/n).read_text()) for n in FILES}
 ens=products['ensemble-percentiles.json']
 assert ens['memberCount']==4 and ens['memberIDs']==['01','02','03','04']
 assert len(ens['weeks'])==8 and ens['remainingDays57to60']['sampleCountPerMember']==16
 for frame in ens['weeks']+[ens['remainingDays57to60']]:
  for field in ('temperature','precipitationRate'):
   lo,mid,hi=[frame[field][p] for p in ('p10','p50','p90')]
   assert len(lo)==len(ens['gridCoordinates'])==len(mid)==len(hi)
   assert all(a<=b<=c for a,b,c in zip(lo,mid,hi))
 files={name:{'sha256':hashlib.sha256((folder/name).read_bytes()).hexdigest(),'bytes':(folder/name).stat().st_size} for name in (*FILES,*(['verification.json'] if (folder/'verification.json').exists() else []))}
 return {'schemaVersion':1,'generatedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'files':files,'initializations':{'raw':products[FILES[0]]['run'],'anomaly':products[FILES[1]]['initialDate'],'ensemble':ens['run'],'ensoObservation':products[FILES[2]]['observations'][-1]['date']},'source':'Public NOAA products; see each product for exact sources and statistical meaning'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,default=ROOT/'dist/data');p.add_argument('--manifest-only',action='store_true',help='Validate and hash existing products without download');a=p.parse_args()
 if a.manifest_only:
  out=manifest_for(a.output);(a.output/'refresh-manifest.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));return
 with tempfile.TemporaryDirectory(prefix='enso-noaa-') as tmp:
  stage=pathlib.Path(tmp)/'data';stage.mkdir()
  subprocess.run([sys.executable,str(ROOT/'ingestion/refresh.py'),'--output',str(stage)],check=True,timeout=900)
  subprocess.run([sys.executable,str(ROOT/'ingestion/ensemble/retrieve_ensemble.py'),'--run','latest','--days','60','--cache-dir',str(pathlib.Path(tmp)/'cache'),'--output',str(stage/'ensemble-percentiles.json')],check=True,timeout=900)
  # Archive both previously displayed and newly retrieved issuance before replacement.
  previous=a.output/'ensemble-percentiles.json'
  if previous.exists(): archive_product(previous,a.output/'archive')
  archive_product(stage/'ensemble-percentiles.json',a.output/'archive')
  manifest=manifest_for(stage);(stage/'refresh-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
  # All science/provenance checks pass before destination is changed. A single
  # later Git commit publishes all five files atomically; no commit on failure.
  a.output.mkdir(parents=True,exist_ok=True)
  for name in (*FILES,'refresh-manifest.json'):
   dest=a.output/name;pending=dest.with_suffix('.json.tmp');pending.write_bytes((stage/name).read_bytes());os.replace(pending,dest)
  print(json.dumps({'status':'success',**manifest}))
if __name__=='__main__':main()
