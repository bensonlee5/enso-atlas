import sys, pathlib, urllib.request, json, re, datetime, concurrent.futures
ROOT=pathlib.Path(__file__).parent
sys.path.insert(0,str(ROOT/'python-packages'))
import eccodes as e
import numpy as np

def get(u, start=None, end=None):
 headers={} if start is None else {'Range':f'bytes={start}-{end}'}
 with urllib.request.urlopen(urllib.request.Request(u,headers=headers),timeout=120) as r:
  if start is not None and r.status!=206: raise RuntimeError(f'Range unsupported {r.status} {u}')
  return r.read()
def save(name,obj):
 (ROOT/name).write_text(json.dumps(obj,separators=(',',':')))
def decode(path):
 out=[]
 with open(path,'rb') as f:
  while (g:=e.codes_grib_new_from_file(f)):
   keys=['shortName','units','dataDate','dataTime','stepRange','stepType','validityDate','validityTime']
   meta={k:e.codes_get(g,k) for k in keys}
   lats=e.codes_get_array(g,'latitudes');lons=(e.codes_get_array(g,'longitudes')+180)%360-180;vals=e.codes_get_values(g)
   # Native 1 degree (CFS) or quarter degree (AIFS) subset, nearest sample every 2deg.
   latunique=np.unique(lats); lonunique=np.unique(lons)
   latset=np.unique([latunique[np.argmin(abs(latunique-target))] for target in range(24,51,2)])
   lonset=np.unique([lonunique[np.argmin(abs(lonunique-target))] for target in range(-126,-65,2)])
   mask=np.isin(lats,latset)&np.isin(lons,lonset)
   coords=np.column_stack((lats[mask],lons[mask])).round(4).tolist()
   v=vals[mask]
   if meta['units']=='K':v=v-273.15; meta['outputUnits']='°C'
   elif meta['shortName']=='tp':
    if meta['units']=='m':v=v*1000
    elif meta['units'] not in ['kg m**-2','mm']:raise ValueError('Unknown precipitation unit '+meta['units'])
    meta['outputUnits']='mm accumulated since initialization'
   elif meta['shortName']=='prate':v=v*86400;meta['outputUnits']='mm/day equivalent instantaneous rate'
   else:meta['outputUnits']=meta['units']
   out.append({'metadata':meta,'coordinates':coords,'values':v.round(2).tolist()});e.codes_release(g)
 return out

def cfs(v):
 b='https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/cfs.20260929/00/time_grib_01/'
 u=b+v+'.01.2026092900.daily.grb2'
 idx=get(u+'.idx').decode(); rows=idx.splitlines();end=int(rows[240].split(':')[1])-1
 path=ROOT/(v+'60days.grib2')
 if not path.exists():path.write_bytes(get(u,0,end))
 fields=decode(path)
 obj={'model':'NOAA CFSv2','run':'2026-09-29T00:00:00Z','member':'01','source':u,'retrievedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'horizonDays':60,'kind':'single-member raw forecast, not anomaly or probability','gridCoordinates':fields[0]['coordinates'],'frames':[{'metadata':x['metadata'],'values':x['values']} for x in fields]}
 save('cfs-'+v+'-60days.json',obj);print(v,len(fields),len(obj['gridCoordinates']),path.stat().st_size,fields[0]['metadata'],flush=True)

def aifs(step):
 b='https://data.ecmwf.int/forecasts/20260929/12z/aifs-single/0p25/oper/'
 u=b+f'20260929120000-{step}h-oper-fc'
 rows=[json.loads(l) for l in get(u+'.index').decode().splitlines()]
 data=[]
 for row in rows:
  if row.get('param') in ['2t','tp']:
   p=ROOT/f'aifs-{step}-{row["param"]}.grib2'
   if not p.exists():p.write_bytes(get(u+'.grib2',row['_offset'],row['_offset']+row['_length']-1))
   data.extend(decode(p))
 print('aifs',step,len(data),flush=True)
 return data

def sst():
 u='https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for';s=get(u).decode();(ROOT/'wksst9120.for').write_text(s)
 rows=[]
 for l in s.splitlines():
  m=re.match(r'\s*(\d{2}[A-Z]{3}\d{4})',l)
  if not m:continue
  n=list(map(float,re.findall(r'-?\d+\.\d+',l[m.end():])))
  rows.append({'date':datetime.datetime.strptime(m[1],'%d%b%Y').strftime('%Y-%m-%d'),'nino12':{'sst':n[0],'anomaly':n[1]},'nino3':{'sst':n[2],'anomaly':n[3]},'nino34':{'sst':n[4],'anomaly':n[5]},'nino4':{'sst':n[6],'anomaly':n[7]}})
 save('enso-observations.json',{'source':u,'units':'°C','baseline':'1991–2020','kind':'Observed weekly sea-surface temperature indices; not ONI','observations':rows[-104:]});print('sst',rows[-1],flush=True)

if __name__=='__main__':
 sst()
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as p:list(p.map(cfs,['tmp2m','prate']))
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:fields=[x for group in p.map(aifs,[24,168,336,360]) for x in group]
 save('aifs-sample.json',{'model':'ECMWF AIFS single','run':'2026-09-29T12:00:00Z','source':'https://data.ecmwf.int/forecasts/20260929/12z/aifs-single/0p25/oper/','attribution':'ECMWF open data, CC BY 4.0','kind':'Deterministic forecast snapshots, not daily means or anomalies','gridCoordinates':fields[0]['coordinates'],'frames':[{'metadata':x['metadata'],'values':x['values']} for x in fields]})
