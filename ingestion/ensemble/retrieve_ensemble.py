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
from transport import separate_member_means, validate_member_artifact
from quantiles import member_quantiles, QUANTILE_KEYS, QUANTILE_LEVELS, align_valid_window
ROOT=pathlib.Path(__file__).parent
P=argparse.ArgumentParser();P.add_argument('--run',default='latest');P.add_argument('--days',type=int,default=60);P.add_argument('--cache-dir',type=pathlib.Path,default=pathlib.Path(tempfile.gettempdir())/'enso-atlas-cfs-cache');P.add_argument('--output',type=pathlib.Path,default=ROOT/'cfs-weekly-ensemble-percentiles.json');P.add_argument('--previous',type=pathlib.Path);P.add_argument('--locations-file',type=pathlib.Path);P.add_argument('--reference-date',help='Require this UTC reference date (YYYY-MM-DD), fail rather than reuse yesterday');P.add_argument('--workers',type=int,default=2);P.add_argument('--lag-days',type=int,default=4,choices=range(1,5));A=P.parse_args()
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
    limit=end-start+1 if start is not None else 2000000
    assert 0<limit<=64000000,'Source request exceeds bounded field size'
    data=r.read(limit+1);assert len(data)<=limit,'Oversized source response'
    if start is not None:assert len(data)==end-start+1
    return data
  except Exception:
   if attempt==attempts-1:raise
   time.sleep(2**attempt)
def latest_complete_suite():
 base='https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/'
 dates=sorted(set(re.findall(r'cfs\.(\d{8})/',get(base,timeout=20,attempts=1).decode())),reverse=True)
 if A.reference_date:
  expected=dt.date.fromisoformat(A.reference_date).strftime('%Y%m%d');dates=[day for day in dates if day==expected]
 for day in dates[:3]:
  run=day+'00'
  try:
   # Validate all 32 indexes before downloading GRIB. Cache only complete
   # indexes and reuse them for decoding/retries; two connections bound NOAA load.
   jobs=[]
   for lag_day in range(A.lag_days):
    source_day=(dt.datetime.strptime(day,'%Y%m%d')-dt.timedelta(days=lag_day)).strftime('%Y%m%d')
    source_run=source_day+'00'
    for member in ['01','02','03','04']:
     for var in ['tmp2m','prate']:
      url=f'{base}cfs.{source_day}/00/time_grib_{member}/{var}.{member}.{source_run}.daily.grb2.idx'
      index=CACHE/f'{var}.{member}.{source_run}.{A.days+lag_day}days.idx'
      jobs.append((url,index,N+4*lag_day))
   def check_index(job):
    url,index,count=job
    body=index.read_bytes() if index.exists() else get(url,timeout=30,attempts=2)
    if len(body.decode().splitlines())<=count:raise ValueError('Incomplete aligned member: '+url.rsplit('/',1)[-1])
    if not index.exists():index.write_bytes(body)
   with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(check_index,jobs))
   return run
  except Exception as ex:
   print('CFS suite discovery failed:',run,type(ex).__name__,str(ex)[:160],flush=True)
   continue
 raise ValueError('No complete aligned 00Z lagged suite among latest three dated runs')
def resolve_run():
 if A.run!='latest':return A.run
 attempts=3 if A.reference_date else 1
 for attempt in range(attempts):
  try:return latest_complete_suite()
  except Exception:
   if attempt==attempts-1:raise
   print('Required daily CFS suite is incomplete; retrying discovery in 60 seconds (no GRIB downloaded)',flush=True);time.sleep(60)
RUN=resolve_run()
INIT=dt.datetime.strptime(RUN,'%Y%m%d%H').replace(tzinfo=dt.timezone.utc)
assert RUN.endswith('00'), 'Only00Z members02–04 have seasonal-length forecasts'
assert dt.datetime.now(dt.timezone.utc)-INIT<dt.timedelta(days=4), 'Ensemble run stale'
def fetch_decode(pair):
 source_run,member,var=pair
 source_init=dt.datetime.strptime(source_run,'%Y%m%d%H').replace(tzinfo=dt.timezone.utc)
 lag=int((INIT-source_init).total_seconds()/21600);assert lag>=0 and lag%4==0
 count=N+lag
 url=f'https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/cfs.{source_run[:8]}/{source_run[8:]}/time_grib_{member}/{var}.{member}.{source_run}.daily.grb2'
 path=CACHE/f'{var}.{member}.{source_run}.{A.days+lag//4}days.grib2';idxpath=path.with_suffix('.idx')
 if not idxpath.exists():idxpath.write_bytes(get(url+'.idx'))
 rows=idxpath.read_text().splitlines();assert len(rows)>count
 end=int(rows[count].split(':')[1])-1
 if not path.exists():path.write_bytes(get(url,0,end))
 assert path.stat().st_size==end+1
 frames=[];metas=[];coordinates=None;mask=None
 with path.open('rb') as f:
  while (g:=e.codes_grib_new_from_file(f)):
   keys=['shortName','units','dataDate','dataTime','stepRange','stepType','startStep','endStep','validityDate','validityTime','productDefinitionTemplateNumber']
   meta={k:e.codes_get(g,k) for k in keys}
   assert str(meta['dataDate'])==source_run[:8] and meta['dataTime']==0
   assert meta['stepType']=='instant' and meta['productDefinitionTemplateNumber']==0
   assert e.codes_get(g,'numberOfMissing')==0, 'Missing global cells: reject rather than fabricate values'
   assert meta['shortName']==('2t' if var=='tmp2m' else 'prate'), 'Wrong forecast variable'
   assert e.codes_get(g,'typeOfLevel')==('heightAboveGround' if var=='tmp2m' else 'surface')
   assert e.codes_get(g,'level')==(2 if var=='tmp2m' else 0), 'Wrong vertical level'
   assert meta['endStep']==(len(frames)+1)*6
   valid=source_init+dt.timedelta(hours=meta['endStep'])
   assert meta['validityDate']==int(valid.strftime('%Y%m%d')) and meta['validityTime']==int(valid.strftime('%H%M'))
   if mask is None:
    lats=e.codes_get_array(g,'latitudes');lons=(e.codes_get_array(g,'longitudes')+180)%360-180
    la=np.unique(lats);lo=np.unique(lons)
    # Every fourth native Gaussian row/longitude: a complete periodic globe,
    # not regional samples extended into unsupported locations. Retain edge rows.
    latset=np.unique(np.r_[la[::4],la[-1]])
    lonset=lo[::4]
    mask=np.isin(lats,latset)&np.isin(lons,lonset);coordinates=np.column_stack([lats[mask],lons[mask]]).round(4).tolist()
   v=e.codes_get_values(g)[mask]
   if var=='tmp2m':assert meta['units']=='K';v=v-273.15
   else:assert meta['units']=='kg m**-2 s**-1';v=v*86400
   assert np.isfinite(v).all()
   frames.append(v);metas.append(meta);e.codes_release(g)
 assert len(frames)==count
 values=align_valid_window(frames,source_init,INIT,N);assert len(values)==N
 assert source_init+dt.timedelta(hours=metas[lag]['endStep'])==INIT+dt.timedelta(hours=6)
 provenance={'member':member,'memberID':source_run+'/'+member,'initialization':source_init.isoformat(),'lagHours':lag*6,'firstAlignedFrame':metas[lag],'variable':var,'source':url,'indexSource':url+'.idx','retrievedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'firstFrame':metas[0],'lastFrame':metas[-1],'frameCount':count,'alignedFrameCount':N}
 # Reduce the aligned time axis inside each decoder process. Returning all
 # 240 frames for32 sources would retain~290MB of unnecessary parent arrays.
 boundaries=[(i*28,(i+1)*28) for i in range(8)]+[(224,N)]
 period_means=np.array([values[a:b].mean(axis=0).round(6) for a,b in boundaries])
 print('Decoded',source_run,member,var,values.shape,'->',period_means.shape,flush=True)
 return source_run+'/'+member,var,period_means,coordinates,provenance
if __name__=='__main__':
 if A.previous and A.previous.exists():
  previous=json.loads(A.previous.read_text())
  if previous.get('schemaVersion')==3 and previous.get('coverage')=='global' and previous.get('lagDays')==A.lag_days and dt.datetime.fromisoformat(previous['run'].replace('Z','+00:00'))==INIT:
   validate_member_artifact(previous,A.previous.parent)
   A.output.parent.mkdir(parents=True,exist_ok=True)
   A.output.write_bytes(A.previous.read_bytes())
   artifact=previous['memberMeansArtifact']['file'];(A.output.parent/artifact).write_bytes((A.previous.parent/artifact).read_bytes())
   print('Unchanged complete CFS ensemble suite:',RUN,flush=True);sys.exit(0)
 runs=[(INIT-dt.timedelta(days=i)).strftime('%Y%m%d%H') for i in range(A.lag_days)]
 pairs=[(run,m,v) for run in runs for m in ['01','02','03','04'] for v in ['tmp2m','prate']]
 # ecCodes decoding runs in separate processes for thread safety.
 with concurrent.futures.ProcessPoolExecutor(max_workers=max(1,min(2,A.workers))) as pool:results=list(pool.map(fetch_decode,pairs))
 coords=results[0][3];assert 4000<=len(coords)<6000 and all(r[3]==coords for r in results)
 data={(m,v):a for m,v,a,c,p in results};members=[run+'/'+m for run in runs for m in ['01','02','03','04']]
 out={'schemaVersion':3,'coverage':'global','sampling':{'nativeGrid':'CFSv2 Gaussian 384 × 190','nativeStride':4,'displaySpacingDegrees':3.8,'longitudePeriodic':True,'latitudeBounds':[min(c[0] for c in coords),max(c[0] for c in coords)],'polarCaps':'No extrapolation beyond outermost native Gaussian latitude'},'memberMeanDecimalPlaces':6,'availableQuantiles':list(QUANTILE_KEYS),'quantileLevels':list(QUANTILE_LEVELS),'model':'NOAA CFSv2','run':INIT.isoformat(),'memberIDs':members,'memberCount':len(members),'initializationRange':[(INIT-dt.timedelta(days=A.lag_days-1)).isoformat(),INIT.isoformat()],'laggedEnsemble':A.lag_days>1,'lagDays':A.lag_days,'members':[{'id':run+'/'+m,'member':m,'initialization':dt.datetime.strptime(run,'%Y%m%d%H').replace(tzinfo=dt.timezone.utc).isoformat()} for run in runs for m in ['01','02','03','04']],'kind':f'{len(members)}-member lagged empirical model quantiles; uncalibrated, not event probabilities or certainty bounds','quantileMethod':'NumPy linear quantiles (Hyndman–Fan type7), q=[0.01,0.05,0.1,0.5,0.9,0.95,0.99], applied across valid-time-aligned member temporal averages. Equal member weights. P50 is the median of sorted member means.','method':'Each member is averaged over 28 instantaneous six-hourly forecast samples per week, THEN quantiles are computed across members. Precipitation is mean sampled instantaneous rate converted to mm/day; not a validated weekly accumulated amount. 00Z members01–04 across consecutive initialization days; older runs are cropped to the exact same 240 six-hour valid instants before any weekly averaging. This is a lagged ensemble: initial conditions and forecast lead ages differ and members are dependent. No bias correction or climatological calibration.','limitations':['A small correlated lagged ensemble cannot resolve rare-event probabilities. P1/P5/P95/P99 are empirical interpolations, not calibrated tail probabilities or certainty bounds; increasing member count does not remove model bias or dependence','Weekly averages based on6-hourly samples, not continuous temporal integration','Worldwide native-model points sampled every fourth grid row/column (~3.8 degrees); display interpolation adds no model resolution and is not an exact city forecast','All longitudes and both hemispheres, including oceans; unsampled polar caps stay empty','Weeks1–8 cover56days; final4days are separately supplied, not a full ninth week'],'units':{'temperature':'°C','precipitationRate':'mm/day'},'gridCoordinates':coords,'sources':[p['source'] for *_,p in results],'provenance':[p for *_,p in results],'weeks':[]}
 def interval(a,b,w):
  o={'week':w,'intervalStart':(INIT+dt.timedelta(hours=a*6)).isoformat(),'intervalEndExclusive':(INIT+dt.timedelta(hours=b*6)).isoformat(),'firstSampleHour':(a+1)*6,'lastSampleHour':b*6,'sampleCountPerMember':b-a,'memberCount':len(members)}
  for var,key in [('tmp2m','temperature'),('prate','precipitationRate')]:
   means=np.array([data[m,var][w-1] for m in members])
   o[key]=member_quantiles(means)
   # Retain member temporal means to 0.000001 units; all displayed quantiles
   # are reproducible from these means. This bounds transport without invented members.
   o.setdefault('memberMeans',{})[key]=means.tolist()
  return o
 for w in range(1,9):out['weeks'].append(interval((w-1)*28,w*28,w))
 if N>224:out['remainingDays57to60']=interval(224,N,9)
 old=A.locations_file or ROOT.parents[1]/'dist'/'data'/'cfs-weekly-raw-60days.json'
 if old.exists():
  out['sampledLocations']=[]
  for location in json.loads(old.read_text())['sampledLocations']:
   lat,lon=location['requestedCoordinate']
   index=min(range(len(coords)),key=lambda i:(coords[i][0]-lat)**2+((((coords[i][1]-lon+180)%360)-180)*np.cos(np.deg2rad(lat)))**2)
   out['sampledLocations'].append({'name':location['name'],'requestedCoordinate':[lat,lon],'nativeGridCoordinate':coords[index],'gridIndex':index})
 out['processingSeconds']=round(time.monotonic()-START,2);out['retrievedAt']=dt.datetime.now(dt.timezone.utc).isoformat()
 A.output.parent.mkdir(parents=True,exist_ok=True)
 out=separate_member_means(out,A.output.parent);validate_member_artifact(out,A.output.parent)
 stage=A.output.with_suffix('.json.tmp');stage.write_text(json.dumps(out,separators=(',',':'),allow_nan=False));os.replace(stage,A.output)
 print('Wrote',A.output,'in',out['processingSeconds'],'seconds',flush=True)
