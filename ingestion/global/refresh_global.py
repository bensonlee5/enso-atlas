#!/usr/bin/env python3
"""Resolve latest complete public AIFS run and fetch 8 individual GRIB messages.
Dependencies: numpy, eccodes; extract_global.py adjacent. No secrets/services.
python refresh_global.py --cache-dir ./weather-cache --output ./aifs-global-snapshots.json
Optionally reuse CFS cache: --cfs-run YYYYMMDDHH --cfs-cache-dir ./ensemble-cache --cfs-output ./cfs-global-60days.json
"""
import argparse,concurrent.futures,datetime,hashlib,json,pathlib,re,subprocess,sys,urllib.request,tempfile
BASE='https://data.ecmwf.int/forecasts/'
LEADS=(24,168,336,360)
def get(url,start=None,length=None):
 headers={'User-Agent':'ENSOAtlas-public-weather-refresh/1.0'}
 if start is not None:headers['Range']=f'bytes={start}-{start+length-1}'
 with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=90) as r:
  if start is not None:
   assert r.status==206,'Upstream ignored Range; refusing full GRIB'
   assert r.headers.get('Content-Range','').startswith(f'bytes {start}-{start+length-1}/'),'Wrong Range'
  limit=length if length is not None else 2000000
  data=r.read(limit+1);assert len(data)<=limit,'Oversized upstream response'
  if length is not None:assert len(data)==length,'Truncated GRIB message'
  return data

def resolve():
 html=get(BASE).decode();dates=sorted(set(re.findall(r'/forecasts/(20\d{6})/',html)),reverse=True)
 assert dates,'No dates found in official ECMWF listing'
 for date in dates[:3]:
  try:listing=get(BASE+date+'/').decode()
  except Exception:continue
  hours=sorted(set(re.findall(r'(?<!\d)(00|06|12|18)z(?:/|["\'])',listing)),reverse=True)
  for hour in hours:
   run=date+hour;prefix=f'{BASE}{date}/{hour}z/aifs-single/0p25/oper/';jobs=[]
   try:
    for lead in LEADS:
     stem=prefix+f'{run}0000-{lead}h-oper-fc'
     rows=[json.loads(x) for x in get(stem+'.index').decode().splitlines() if x.strip()]
     for var in ['2t','tp']:
      chosen=[r for r in rows if r.get('param')==var];assert len(chosen)==1
      row=chosen[0];offset=int(row['_offset']);length=int(row['_length']);assert 0<length<10000000 and offset>=0
      jobs.append({'run':run,'lead':lead,'param':var,'source':stem+'.grib2','indexSource':stem+'.index','offset':offset,'bytes':length})
    print('Latest complete indexed AIFS run:',run,flush=True);return run,jobs
   except Exception as ex:print('Skipping incomplete run',run,str(ex)[:120],file=sys.stderr,flush=True)
 raise RuntimeError('No complete AIFS run among latest 3 listed dates')

def main():
 p=argparse.ArgumentParser();p.add_argument('--cache-dir',type=pathlib.Path,default=pathlib.Path(tempfile.gettempdir())/'enso-aifs-cache');p.add_argument('--output',required=True,type=pathlib.Path);p.add_argument('--cfs-run');p.add_argument('--cfs-cache-dir',type=pathlib.Path);p.add_argument('--cfs-output',type=pathlib.Path);a=p.parse_args()
 a.cache_dir.mkdir(parents=True,exist_ok=True);a.output.parent.mkdir(parents=True,exist_ok=True)
 run,jobs=resolve()
 def download(job):
  path=a.cache_dir/f'aifs.{run}.{job["lead"]}.{job["param"]}.grib2'
  if not path.exists() or path.stat().st_size!=job['bytes']:
   data=get(job['source'],job['offset'],job['bytes']);assert data[:4]==b'GRIB' and data[-4:]==b'7777'
   tmp=path.with_suffix('.tmp');tmp.write_bytes(data);tmp.replace(path)
  job['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();job['cacheFile']=path.name;return path
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:paths=list(pool.map(download,jobs))
 helper=pathlib.Path(__file__).with_name('extract_global.py');staged=a.output.with_suffix(a.output.suffix+'.validated-stage')
 cmd=[sys.executable,str(helper),'--model','aifs','--run',run,'--temperature']+[str(p) for p,j in zip(paths,jobs) if j['param']=='2t']+['--precipitation']+[str(p) for p,j in zip(paths,jobs) if j['param']=='tp']+['--output',str(staged)]
 subprocess.run(cmd,check=True)
 data=json.loads(staged.read_text());assert len(data['frames'])==8
 for f in data['frames']:
  m=f['metadata'];lead=m['endStep'];assert lead in LEADS
  valid=datetime.datetime.strptime(run,'%Y%m%d%H')+datetime.timedelta(hours=lead)
  assert m['validityDate']==int(valid.strftime('%Y%m%d')) and m['validityTime']==int(valid.strftime('%H%M'))
  if m['shortName']=='2t':assert m['stepType']=='instant'
  elif m['shortName']=='tp':assert m['stepType']=='accum'
  else:raise ValueError('Unexpected AIFS variable')
 data['provenance']=jobs;data['sourceResolution']='Latest official listed run with all four lead indexes and both variables; all eight GRIB messages metadata-validated';tmp=a.output.with_suffix('.tmp');tmp.write_text(json.dumps(data,separators=(',',':'),allow_nan=False));tmp.replace(a.output);staged.unlink()
 print('Verified',run,'8 GRIB messages',sum(j['bytes'] for j in jobs),'bytes; output',a.output,flush=True)
 if any([a.cfs_run,a.cfs_cache_dir,a.cfs_output]):
  assert all([a.cfs_run,a.cfs_cache_dir,a.cfs_output]),'Supply all three CFS flags'
  subprocess.run([sys.executable,str(helper),'--model','cfs','--run',a.cfs_run,'--temperature',str(a.cfs_cache_dir/f'tmp2m.01.{a.cfs_run}.60days.grib2'),'--precipitation',str(a.cfs_cache_dir/f'prate.01.{a.cfs_run}.60days.grib2'),'--output',str(a.cfs_output)],check=True)
if __name__=='__main__':main()
