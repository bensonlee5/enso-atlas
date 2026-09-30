"""Refresh public NOAA products into dist/data; fail closed before replacing any product.
Usage: python ingestion/refresh.py [--output dist/data]
Dependencies: eccodes numpy h5py. No accounts or keys. No hosting or GitHub writes.
"""
import argparse, concurrent.futures, datetime as dt, json, math, os, pathlib, re, tempfile
import numpy as np
import h5py
from download_process import get, decode
UTC=dt.timezone.utc
BASE='https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/'
CPC='https://www.cpc.ncep.noaa.gov/products/CFSv2/weekly/'
LOCATIONS=[('Los Angeles',34.05,-118.24),('San Francisco',37.77,-122.42),('Sacramento',38.58,-121.49),('San Diego',32.72,-117.16),('Fresno',36.74,-119.79),('New York',40.71,-74.01),('Chicago',41.88,-87.63),('Dallas',32.78,-96.8),('Miami',25.76,-80.19),('Seattle',47.61,-122.33)]
def discover_cfs():
 dates=sorted(set(re.findall(r'cfs\.(\d{8})/',get(BASE).decode())),reverse=True)
 if not dates: raise ValueError('No CFS dated directories')
 for day in dates[:3]:
  for hour in ['18','12','06','00']:
   root=f'{BASE}cfs.{day}/{hour}/time_grib_01/'
   urls=[root+f'{v}.01.{day}{hour}.daily.grb2' for v in ['tmp2m','prate']]
   try:
    indexes=[get(u+'.idx').decode().splitlines() for u in urls]
    if all(len(x)>=241 for x in indexes): return day,hour,urls,indexes
   except Exception: continue
 raise ValueError('No complete paired 60-day CFS run among latest three days')
def raw(tmp):
 day,hour,urls,indexes=discover_cfs();init=dt.datetime.strptime(day+hour,'%Y%m%d%H').replace(tzinfo=UTC)
 def download(i):
  p=tmp/f'cfs-{i}.grib2';p.write_bytes(get(urls[i],0,int(indexes[i][240].split(':')[1])-1));return decode(p)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:fields=list(pool.map(download,[0,1]))
 coords=fields[0][0]['coordinates']
 for i,frames in enumerate(fields):
  if len(frames)!=240:raise ValueError('Expected exactly 240 six-hour fields')
  for n,f in enumerate(frames):
   m=f['metadata'];valid=dt.datetime.strptime(str(m['validityDate'])+str(m['validityTime']).zfill(4),'%Y%m%d%H%M').replace(tzinfo=UTC)
   if valid!=init+dt.timedelta(hours=(n+1)*6):raise ValueError('Noncontiguous forecast valid times')
   if f['coordinates']!=coords or m['stepType']!='instant':raise ValueError('Grid or temporal statistic changed')
   if any(not math.isfinite(v) for v in f['values']):raise ValueError('Nonfinite CFS values')
 out={'model':'NOAA CFSv2','run':init.isoformat().replace('+00:00','Z'),'member':'01','retrievedAt':dt.datetime.now(UTC).isoformat(),'kind':'single-member raw forecast; not calibrated anomaly or probability','method':'Arithmetic means of 28 six-hourly instantaneous forecast samples per week at native model grid points. Coordinates selected by nearest native latitude/longitude to roughly 2-degree spacing; no spatial interpolation. Precipitation is mean instantaneous rate expressed in mm/day, not a verified weekly accumulation.','units':{'temperature':'°C','precipitationRate':'mm/day equivalent'},'sources':urls,'gridCoordinates':coords,'weeks':[],'sampledLocations':[]}
 for w in range(8):
  frame={'week':w+1,'intervalStart':(init+dt.timedelta(days=w*7)).isoformat(),'intervalEndExclusive':(init+dt.timedelta(days=(w+1)*7)).isoformat(),'firstSampleHour':w*168+6,'lastSampleHour':(w+1)*168,'sampleCount':28}
  for key,frames in zip(['temperature','precipitationRate'],fields):frame[key]=np.mean([f['values'] for f in frames[w*28:(w+1)*28]],axis=0).round(2).tolist()
  out['weeks'].append(frame)
 for name,la,lo in LOCATIONS:
  j=min(range(len(coords)),key=lambda i:(coords[i][0]-la)**2+(math.cos(math.radians(la))*(coords[i][1]-lo))**2)
  out['sampledLocations'].append({'name':name,'requestedCoordinate':[la,lo],'nativeGridCoordinate':coords[j],'gridIndex':j,'weeks':[{'week':w['week'],'temperature':w['temperature'][j],'precipitationRate':w['precipitationRate'][j]} for w in out['weeks']]})
 return out

def text_attr(x):return x.decode() if isinstance(x,bytes) else str(x)
def anomaly(tmp):
 html=get(CPC).decode();dates=sorted(set(re.findall(r'CFSv2\.(?:prec|tmpsfc)\.(\d{8})\.wkly\.anom\.nc',html)),reverse=True)
 if not dates:raise ValueError('Cannot discover current weekly anomaly product')
 day=dates[0];out={'model':'NOAA CPC CFSv2 weekly ensemble anomalies','initialDate':str(dt.datetime.strptime(day,'%Y%m%d').date()),'ensembleMembers':16,'kind':'Published ensemble-mean anomaly, not probability','retrievedAt':dt.datetime.now(UTC).isoformat(),'fields':{}}
 for v in ['prec','tmpsfc']:
  url=f'{CPC}data/CFSv2.{v}.{day}.wkly.anom.nc';p=tmp/f'{v}.nc';p.write_bytes(get(url))
  with h5py.File(p) as f:
   a=f['anom'];initial=text_attr(a.attrs['initial_time'])
   if initial!=day:raise ValueError('Anomaly initialization mismatch')
   baseline=text_attr(a.attrs['climatoloy_period']);out['baseline']=baseline+' model climatology'
   epoch=re.search(r'days since (\d{4}-\d{2}-\d{2})',text_attr(f['time'].attrs['units']))
   if not epoch:raise ValueError('Unsupported time units')
   origin=dt.date.fromisoformat(epoch[1]);lon=(f['lon'][:]+180)%360-180;lat=f['lat'][:];xx,yy=np.meshgrid(lon,lat);mask=(xx>=-126)&(xx<=-66)&(yy>=24)&(yy<=50);coords=np.column_stack((yy[mask],xx[mask])).tolist()
   if 'gridCoordinates' in out and coords!=out['gridCoordinates']:raise ValueError('Anomaly grids mismatch')
   out['gridCoordinates']=coords;frames=[];fill=float(np.asarray(a.attrs['_FillValue']).ravel()[0])
   if len(f['time'])!=4:raise ValueError('Expected four weekly anomaly frames')
   for i,t in enumerate(f['time'][:]):
    start=origin+dt.timedelta(days=int(t));vals=a[0,i,0,:,:][mask];frames.append({'week':i+1,'startDate':str(start),'endDate':str(start+dt.timedelta(days=6)),'values':[round(float(x),3) if np.isfinite(x) and x!=fill else None for x in vals]})
   out['fields'][v]={'unit':'mm/day' if v=='prec' else '°C anomaly','source':url,'frames':frames}
 return out

def enso():
 url='https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for';rows=[]
 for line in get(url).decode().splitlines():
  m=re.match(r'\s*(\d{2}[A-Z]{3}\d{4})',line)
  if not m:continue
  n=list(map(float,re.findall(r'-?\d+\.\d+',line[m.end():])))
  if len(n)!=8:raise ValueError('ENSO index row changed')
  row={'date':dt.datetime.strptime(m[1],'%d%b%Y').date().isoformat()}
  for k,i in [('nino12',0),('nino3',2),('nino34',4),('nino4',6)]:row[k]={'sst':n[i],'anomaly':n[i+1]}
  rows.append(row)
 if not rows:raise ValueError('Empty ENSO observations')
 return {'source':url,'units':'°C','baseline':'1991–2020','kind':'Observed weekly sea-surface temperature indices; not ONI','observations':rows[-104:]}

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,default=pathlib.Path(__file__).parents[1]/'dist/data');args=p.parse_args();now=dt.datetime.now(UTC)
 with tempfile.TemporaryDirectory() as temp:
  temp=pathlib.Path(temp);products={'cfs-weekly-raw-60days.json':raw(temp),'cfs-weekly-anomalies.json':anomaly(temp),'enso-observations.json':enso()}
  if now-dt.datetime.fromisoformat(products['cfs-weekly-raw-60days.json']['run'].replace('Z','+00:00'))>dt.timedelta(days=4):raise ValueError('Latest complete CFS run is over four days old')
  if now.date()-dt.date.fromisoformat(products['cfs-weekly-anomalies.json']['initialDate'])>dt.timedelta(days=14):raise ValueError('Weekly anomaly product is over fourteen days old')
  if now.date()-dt.date.fromisoformat(products['enso-observations.json']['observations'][-1]['date'])>dt.timedelta(days=21):raise ValueError('ENSO observations are over21days old')
  # Validate every product before replacing. Each file uses atomic rename. Deployment
  # is an external all-files transaction and must only occur after successful exit.
  args.output.mkdir(parents=True,exist_ok=True)
  for name,data in products.items():
   dest=args.output/name;stage=dest.with_suffix('.json.tmp');stage.write_text(json.dumps(data,separators=(',',':'),allow_nan=False));os.replace(stage,dest)
  print(json.dumps({'status':'success','refreshedAt':now.isoformat(),'cfsRun':products['cfs-weekly-raw-60days.json']['run'],'anomalyInitialDate':products['cfs-weekly-anomalies.json']['initialDate'],'ensoDate':products['enso-observations.json']['observations'][-1]['date'],'files':list(products)}))
if __name__=='__main__':main()
