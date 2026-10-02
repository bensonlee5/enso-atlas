#!/usr/bin/env python3
"""Resolve latest complete public AIFS run and fetch first-week 6-hourly and sparse longer-range GRIB fields.
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
 p=argparse.ArgumentParser();p.add_argument('--cache-dir',type=pathlib.Path,default=pathlib.Path(tempfile.gettempdir())/'enso-aifs-cache');p.add_argument('--output',required=True,type=pathlib.Path);p.add_argument('--previous',type=pathlib.Path);p.add_argument('--cfs-run');p.add_argument('--cfs-cache-dir',type=pathlib.Path);p.add_argument('--cfs-output',type=pathlib.Path);a=p.parse_args()
 a.cache_dir.mkdir(parents=True,exist_ok=True);a.output.parent.mkdir(parents=True,exist_ok=True)
 run,jobs=resolve()
 if a.previous and a.previous.exists() and not any([a.cfs_run,a.cfs_cache_dir,a.cfs_output]):
  previous=json.loads(a.previous.read_text())
  previous_run=datetime.datetime.fromisoformat(previous['run'].replace('Z','+00:00')).strftime('%Y%m%d%H')
  if previous_run==run and previous.get('fineFirstWeek',{}).get('schemaVersion')==1:
   a.output.write_bytes(a.previous.read_bytes());print('Unchanged AIFS run:',run,flush=True);return
 helper=pathlib.Path(__file__).with_name('extract_global.py')
 fine_helper=pathlib.Path(__file__).with_name('build_fine.py')
 subprocess.run([sys.executable,str(fine_helper),'--run',run,'--cache-dir',str(a.cache_dir),'--output',str(a.output)],check=True)
 if any([a.cfs_run,a.cfs_cache_dir,a.cfs_output]):
  assert all([a.cfs_run,a.cfs_cache_dir,a.cfs_output]),'Supply all three CFS flags'
  subprocess.run([sys.executable,str(helper),'--model','cfs','--run',a.cfs_run,'--temperature',str(a.cfs_cache_dir/f'tmp2m.01.{a.cfs_run}.60days.grib2'),'--precipitation',str(a.cfs_cache_dir/f'prate.01.{a.cfs_run}.60days.grib2'),'--output',str(a.cfs_output)],check=True)
if __name__=='__main__':main()
