#!/usr/bin/env python3
"""Retrieve an explicit CFSv2 00Z suite, validate metadata, sample and derive quantiles.
Requires numpy/eccodes; optional ECCODES_PYTHON_PATH for an existing local install.
Never silently change cycle, replace members, or invent missing forecasts.
"""
import os,sys,pathlib,json,datetime as dt,urllib.request,concurrent.futures,time,hashlib,argparse,tempfile,re
if os.environ.get('ECCODES_PYTHON_PATH'):
 sys.path.insert(0,os.environ['ECCODES_PYTHON_PATH'])
import eccodes as e
import numpy as np
ROOT=pathlib.Path(__file__).parent
P=argparse.ArgumentParser();P.add_argument('--run',default='latest');P.add_argument('--days',type=int,default=60);P.add_argument('--cache-dir',type=pathlib.Path,default=pathlib.Path(tempfile.gettempdir())/'enso-atlas-cfs-cache');P.add_argument('--output',type=pathlib.Path,default=ROOT/'cfs-weekly-ensemble-percentiles.json');P.add_argument('--workers',type=int,default=2);A=P.parse_args()
CACHE=A.cache_dir;CACHE.mkdir(parents=True,exist_ok=True)
assert A.days==60, 'This app schema requires exactly60days'
N=A.days*4
START=time.monotonic()
def get(url,start=None,end=None,timeout=120,attempts=3):
 headers={'User-Agent':'CFS-research/1.0'}
 if start is not None:headers['Range']=f'bytes={start}-{end}'
 for attempt in range(attempts):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout) as r:
    if start is not None:assert r.status==206, f'Range unsupported: {r.status}'
    data=r.read()
    if start is not None:assert len(data)==end-start+1
    return data
  except Exception:
   if attempt==attempts-1:raise
   time.sleep(2**attempt)
def latest_complete_suite():
 base='https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/'
 dates=sorted(set(re.findall(r'cfs\.(\d{8})/',get(base,timeout=20,attempts=1).decode())),reverse=True)
 for day in dates[:3]:
  run=day+'00'
  try:
   for member in ['01','02','03','04']:
    for var in ['tmp2m','prate']:
     url=f'{base}cfs.{day}/00/time_grib_{member}/{var}.{member}.{run}.daily.grb2.idx'
     if len(get(url,timeout=20,attempts=1).decode().splitlines())<=N:raise ValueError('Incomplete member')
   return run
  except Exception:continue
 raise ValueError('No complete 00Z four-member suite among latest three dated runs')
RUN=latest_complete_suite() if A.run=='latest' else A.run
INIT=dt.datetime.strptime(RUN,'%Y%m%d%H').replace(tzinfo=dt.timezone.utc)
assert RUN.endswith('00'), 'Only00Z members02–04 have seasonal-length forecasts'
assert dt.datetime.now(dt.timezone.utc)-INIT<dt.timedelta(days=4), 'Ensemble run stale'
def fetch_decode(pair):
 member,var=pair
 url=f'https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/cfs.{RUN[:8]}/{RUN[8:]}/time_grib_{member}/{var}.{member}.{RUN}.daily.grb2'
 path=CACHE/f'{var}.{member}.{RUN}.{A.days}days.grib2';idxpath=path.with_suffix('.idx')
 if not idxpath.exists():idxpath.write_bytes(get(url+'.idx'))
 rows=idxpath.read_text().splitlines();assert len(rows)>N
 end=int(rows[N].split(':')[1])-1
 if not path.exists():path.write_bytes(get(url,0,end))
 assert path.stat().st_size==end+1
 frames=[];metas=[];coordinates=None;mask=None
 with path.open('rb') as f:
  while (g:=e.codes_grib_new_from_file(f)):
   keys=['shortName','units','dataDate','dataTime','stepRange','stepType','startStep','endStep','validityDate','validityTime','productDefinitionTemplateNumber']
   meta={k:e.codes_get(g,k) for k in keys}
   assert str(meta['dataDate'])==RUN[:8] and meta['dataTime']==0
   assert meta['stepType']=='instant'
   assert meta['endStep']==(len(frames)+1)*6
   valid=INIT+dt.timedelta(hours=meta['endStep'])
   assert meta['validityDate']==int(valid.strftime('%Y%m%d')) and meta['validityTime']==int(valid.strftime('%H%M'))
   if mask is None:
    lats=e.codes_get_array(g,'latitudes');lons=(e.codes_get_array(g,'longitudes')+180)%360-180
    la=np.unique(lats);lo=np.unique(lons)
    latset=np.unique([la[np.argmin(abs(la-t))] for t in range(24,51,2)])
    lonset=np.unique([lo[np.argmin(abs(lo-t))] for t in range(-126,-65,2)])
    mask=np.isin(lats,latset)&np.isin(lons,lonset);coordinates=np.column_stack([lats[mask],lons[mask]]).round(4).tolist()
   v=e.codes_get_values(g)[mask]
   if var=='tmp2m':assert meta['units']=='K';v=v-273.15
   else:assert meta['units']=='kg m**-2 s**-1';v=v*86400
   assert np.isfinite(v).all()
   frames.append(v);metas.append(meta);e.codes_release(g)
 assert len(frames)==N
 values=np.array(frames)
 provenance={'member':member,'variable':var,'source':url,'indexSource':url+'.idx','retrievedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'firstFrame':metas[0],'lastFrame':metas[-1],'frameCount':N}
 print('Decoded',member,var,values.shape,flush=True)
 return member,var,values,coordinates,provenance
if __name__=='__main__':
 pairs=[(m,v) for m in ['01','02','03','04'] for v in ['tmp2m','prate']]
 # ecCodes decoding runs in separate processes for thread safety.
 with concurrent.futures.ProcessPoolExecutor(max_workers=max(1,min(2,A.workers))) as pool:results=list(pool.map(fetch_decode,pairs))
 coords=results[0][3];assert len(coords)==434 and all(r[3]==coords for r in results)
 data={(m,v):a for m,v,a,c,p in results};members=['01','02','03','04']
 out={'model':'NOAA CFSv2','run':INIT.isoformat(),'memberIDs':members,'memberCount':4,'initializationRange':[INIT.isoformat(),INIT.isoformat()],'laggedEnsemble':False,'kind':'Sparse 4-member empirical model quantiles; uncalibrated, not event probabilities or certainty bounds','quantileMethod':'NumPy linear quantiles (Hyndman–Fan type7), q=[0.1,0.5,0.9], applied across four member temporal averages. Equal member weights. P50 is the average of the two central sorted members.','method':'Each member is averaged over 28 instantaneous six-hourly forecast samples per week, THEN quantiles are computed across members. Precipitation is mean sampled instantaneous rate converted to mm/day; not a validated weekly accumulated amount. Same initialized00Z suite members01–04; shared-model members are dependent. No bias correction or climatological calibration.','limitations':['Four-member tails are unstable and do not describe a calibrated10% or90% chance','Weekly averages based on6-hourly samples, not continuous temporal integration','Coarse native-model points sampled every~2degrees; no spatial interpolation and not exact city forecasts','CONUS bounding rectangle includes adjacent ocean and neighboring countries; client may mask geography','Weeks1–8 cover56days; final4days are separately supplied, not a full ninth week'],'units':{'temperature':'°C','precipitationRate':'mm/day'},'gridCoordinates':coords,'sources':[p['source'] for *_,p in results],'provenance':[p for *_,p in results],'weeks':[]}
 def interval(a,b,w):
  o={'week':w,'intervalStart':(INIT+dt.timedelta(hours=a*6)).isoformat(),'intervalEndExclusive':(INIT+dt.timedelta(hours=b*6)).isoformat(),'firstSampleHour':(a+1)*6,'lastSampleHour':b*6,'sampleCountPerMember':b-a,'memberCount':4}
  for var,key in [('tmp2m','temperature'),('prate','precipitationRate')]:
   means=np.array([data[m,var][a:b].mean(axis=0) for m in members]);q=np.quantile(means,[.1,.5,.9],axis=0,method='linear')
   assert (q[0]<=q[1]).all() and (q[1]<=q[2]).all()
   o[key]={name:arr.round(3).tolist() for name,arr in zip(['p10','p50','p90'],q)}
  return o
 for w in range(1,9):out['weeks'].append(interval((w-1)*28,w*28,w))
 if N>224:out['remainingDays57to60']=interval(224,N,9)
 old=ROOT.parents[1]/'dist'/'data'/'cfs-weekly-raw-60days.json'
 if old.exists():out['sampledLocations']=[{k:v for k,v in s.items() if k!='weeks'} for s in json.loads(old.read_text())['sampledLocations']]
 out['processingSeconds']=round(time.monotonic()-START,2);out['retrievedAt']=dt.datetime.now(dt.timezone.utc).isoformat()
 A.output.parent.mkdir(parents=True,exist_ok=True)
 stage=A.output.with_suffix('.json.tmp');stage.write_text(json.dumps(out,separators=(',',':'),allow_nan=False));os.replace(stage,A.output)
 print('Wrote',A.output,'in',out['processingSeconds'],'seconds',flush=True)
