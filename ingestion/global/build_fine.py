#!/usr/bin/env python3
"""First-week AIFS actual grid-node extraction; no interpolation or invented data."""
import argparse,base64,concurrent.futures,datetime,gzip,hashlib,json,pathlib,sys,time
import numpy as np
import eccodes as e
from refresh_global import get,resolve
ROOT=pathlib.Path(__file__).parent
LEADS=list(range(0,169,6))+[336,360]

def pack(v):
 good=np.isfinite(v); q=np.full(v.shape,-32768,dtype='<i2'); rounded=np.rint(v[good]*10)
 if np.any((rounded<-32767)|(rounded>32767)):raise ValueError('Quantization overflow')
 q[good]=rounded.astype('<i2')
 return base64.b64encode(gzip.compress(q.tobytes(),compresslevel=9,mtime=0)).decode()

def interval(a,b,ea,eb):
 """Packing-error bound sums independent endpoint absolute error bounds."""
 d=b-a; tolerance=ea+eb+1e-9
 invalid=~np.isfinite(a)|~np.isfinite(b)|(a < -ea-1e-9)|(b < -eb-1e-9)|(d < -tolerance)
 tiny=(d<0)&~invalid
 d[tiny]=0;d[invalid]=np.nan
 return d,{'missingCells':int(invalid.sum()),'packingNoiseClampedCells':int(tiny.sum()),'packingToleranceMm':tolerance}

def decode(path,run,lead,param):
 with open(path,'rb') as f:g=e.codes_grib_new_from_file(f)
 try:
  keys=['shortName','units','dataDate','dataTime','stepRange','stepType','startStep','endStep','validityDate','validityTime','packingType','packingError','iDirectionIncrementInDegrees','jDirectionIncrementInDegrees']
  m={k:e.codes_get(g,k) for k in keys}
  assert str(m['dataDate'])==run[:8] and m['dataTime']==int(run[8:])*100
  assert m['shortName']==param and m['endStep']==lead
  expected=datetime.datetime.strptime(run,'%Y%m%d%H')+datetime.timedelta(hours=lead)
  assert m['validityDate']==int(expected.strftime('%Y%m%d')) and m['validityTime']==int(expected.strftime('%H%M'))
  assert m['iDirectionIncrementInDegrees']==m['jDirectionIncrementInDegrees']==0.25
  if param=='2t':assert m['units']=='K' and m['stepType']=='instant'
  else:assert m['units'] in ('m','kg m**-2','mm') and m['stepType']=='accum' and m['startStep']==0
  la=e.codes_get_array(g,'latitudes');lo=(e.codes_get_array(g,'longitudes')+180)%360-180
  idx=np.flatnonzero(np.isclose(la,np.round(la),atol=1e-8)&np.isclose(lo,np.round(lo),atol=1e-8))
  idx=idx[np.lexsort((lo[idx],-la[idx]))]
  assert len(idx)==181*360
  assert np.array_equal(la[idx],np.repeat(np.arange(90,-91,-1),360)) and np.array_equal(lo[idx],np.tile(np.arange(-180,180),181))
  allv=e.codes_get_values(g);v=allv[idx].copy();missing=e.codes_get(g,'missingValue');v[v==missing]=np.nan
  if param=='2t':v-=273.15
  factor=1000 if m['units']=='m' else 1
  if param=='tp':v*=factor
  return m,v,float(m['packingError'])*factor
 finally:e.codes_release(g)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--run');parser.add_argument('--cache-dir',type=pathlib.Path,default=ROOT/'cache');parser.add_argument('--output',type=pathlib.Path,default=ROOT/'aifs-global-snapshots.json');args=parser.parse_args()
 run=args.run or resolve()[0]
 cache=args.cache_dir;cache.mkdir(parents=True,exist_ok=True);args.output.parent.mkdir(parents=True,exist_ok=True)
 prefix=f'https://data.ecmwf.int/forecasts/{run[:8]}/{run[8:]}z/aifs-single/0p25/oper/'
 def index(lead):
  stem=prefix+f'{run}0000-{lead}h-oper-fc'; rows=[json.loads(s) for s in get(stem+'.index').decode().splitlines() if s.strip()]
  jobs=[]
  for param in ('2t','tp'):
   chosen=[r for r in rows if r.get('param')==param];assert len(chosen)==1,(lead,param)
   row=chosen[0];jobs.append(dict(run=run,lead=lead,param=param,source=stem+'.grib2',indexSource=stem+'.index',offset=int(row['_offset']),bytes=int(row['_length'])))
  return jobs
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:jobs=sum(list(pool.map(index,LEADS)),[])
 def download(j):
  path=cache/f'aifs.{run}.{j["lead"]}.{j["param"]}.grib2'
  if not path.exists() or path.stat().st_size!=j['bytes']:
   for attempt in range(3):
    try:data=get(j['source'],j['offset'],j['bytes']);break
    except Exception:
     if attempt==2:raise
     time.sleep(2)
   assert data[:4]==b'GRIB' and data[-4:]==b'7777';path.write_bytes(data)
  j['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();j['cacheFile']=path.name
  print('Downloaded',j['lead'],j['param'],flush=True)
  return path
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:paths=list(pool.map(download,jobs))
 # Build unchanged legacy representation from only original leads.
 import subprocess
 legacy=args.output.with_suffix('.legacy-stage.json')
 cmd=[sys.executable,str(ROOT/'extract_global.py'),'--model','aifs','--run',run,'--temperature']+[str(p) for p,j in zip(paths,jobs) if j['param']=='2t' and j['lead'] in (24,168,336,360)]+['--precipitation']+[str(p) for p,j in zip(paths,jobs) if j['param']=='tp' and j['lead'] in (24,168,336,360)]+['--output',str(legacy)]
 subprocess.run(cmd,check=True);out=json.loads(legacy.read_text())
 init=datetime.datetime.strptime(run,'%Y%m%d%H').replace(tzinfo=datetime.timezone.utc)
 fine={'schemaVersion':1,'grid':{'rows':181,'columns':360,'latitudeStart':90,'longitudeStart':-180,'latitudeStep':-1,'longitudeStep':1,'order':'latitude-major, longitude ascending'},'sourceGridDegrees':0.25,'sampleSpacingDegrees':1,'spatialMethod':'Every fourth native open-data grid node; no spatial interpolation','encoding':'gzip-base64-int16-le','scale':0.1,'quantization':'Nearest 0.1°C or 0.1mm after GRIB decoding and precipitation differencing; maximum additional rounding error 0.05 in output units','missingValue':-32768,'temperatureUnit':'°C','precipitationUnit':'mm per preceding 6 hours','temperature':[],'precipitation':[],'precipitationMethod':'Difference of successive cumulative fields from the same initialization; small negative differences within the sum of endpoint GRIB packingError bounds become zero; larger negatives and invalid endpoints are missing'}
 previous=None
 for p,j in zip(paths,jobs):
  m,v,err=decode(p,run,j['lead'],j['param'])
  if j['lead']>168:continue
  lead=j['lead'];valid=(init+datetime.timedelta(hours=lead)).isoformat()
  if j['param']=='2t':fine['temperature'].append({'leadHours':lead,'validTime':valid,'valuesPacked':pack(v),'missingCells':int((~np.isfinite(v)).sum())})
  else:
   if previous is not None:
    d,quality=interval(previous[0],v,previous[1],err)
    fine['precipitation'].append({'leadHours':lead,'intervalStart':(init+datetime.timedelta(hours=lead-6)).isoformat(),'intervalEnd':valid,'valuesPacked':pack(d),**quality})
   previous=(v,err)
 out['fineFirstWeek']=fine;out['provenance']=jobs;out['sourceResolution']='Official run with all first-week 6h indexes and sparse long-range indexes; all fields independently metadata-validated'
 result=json.dumps(out,separators=(',',':'),allow_nan=False).encode();assert len(result)<=5000000,len(result);tmp=args.output.with_suffix('.tmp');tmp.write_bytes(result);tmp.replace(args.output);legacy.unlink()
 print('RESULT',run,len(result),'bytes; missing',sum(f['missingCells'] for f in fine['precipitation']),flush=True)
 (args.output.with_suffix('.report.json')).write_text(json.dumps({'run':run,'sizeBytes':len(result),'eccodesVersion':e.codes_get_api_version(),'precipitationMissingCells':sum(f['missingCells'] for f in fine['precipitation']),'packingNoiseClampedCells':sum(f['packingNoiseClampedCells'] for f in fine['precipitation'])},indent=2))
if __name__=='__main__':main()
