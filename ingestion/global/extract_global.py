#!/usr/bin/env python3
"""Portable extraction of already-downloaded native global forecast GRIB caches.
Requires numpy, eccodes. No network calls. Fail closed on missing/wrong-run fields.
python extract_global.py --model cfs --run 2026092900 --temperature tmp.grib2 --precipitation prate.grib2 --output cfs-global.json
python extract_global.py --model aifs --run 2026092912 --temperature aifs-24-2t.grib2 aifs-168-2t.grib2 --precipitation aifs-24-tp.grib2 aifs-168-tp.grib2 --output aifs-global.json
"""
import argparse,datetime,json,pathlib
import numpy as np,eccodes as e

def read(paths,run,var,stride=4):
 frames=[];coords=None
 for path in paths:
  with open(path,'rb') as f:
   while (g:=e.codes_grib_new_from_file(f)):
    try:
     m={k:e.codes_get(g,k) for k in ['shortName','units','dataDate','dataTime','stepRange','stepType','endStep','validityDate','validityTime']}
     assert str(m['dataDate'])==run[:8] and m['dataTime']==int(run[8:])*100,'Mixed initialization'
     la=e.codes_get_array(g,'latitudes');lo=(e.codes_get_array(g,'longitudes')+180)%360-180
     las=np.unique(la);los=np.unique(lo)
     sela=np.unique([las[np.argmin(abs(las-x))] for x in range(-88,89,stride)]);selo=np.unique([los[np.argmin(abs(los-x))] for x in range(-180,180,stride)])
     idx=np.flatnonzero(np.isin(la,sela)&np.isin(lo,selo));c=np.column_stack((la[idx],lo[idx])).round(4).tolist()
     if coords is None:coords=c
     else:assert coords==c,'Grid mismatch'
     v=e.codes_get_values(g)[idx];assert np.isfinite(v).all()
     if var=='temperature':assert m['units']=='K';v-=273.15;m['outputUnits']='°C'
     elif m['shortName']=='prate':assert m['units']=='kg m**-2 s**-1';v*=86400;m['outputUnits']='mm/day equivalent instantaneous rate'
     elif m['shortName']=='tp':
      assert m['units'] in ['m','kg m**-2','mm']
      if m['units']=='m':v*=1000
      m['outputUnits']='mm accumulated since initialization'
     else:raise ValueError('Unexpected precipitation variable')
     frames.append({'metadata':m,'values':v})
    finally:e.codes_release(g)
 return coords,sorted(frames,key=lambda x:x['metadata']['endStep'])

def main():
 p=argparse.ArgumentParser();p.add_argument('--model',choices=['cfs','aifs'],required=True);p.add_argument('--run',required=True);p.add_argument('--temperature',nargs='+',required=True);p.add_argument('--precipitation',nargs='+',required=True);p.add_argument('--output',required=True);p.add_argument('--days',type=int,default=60);p.add_argument('--compare-with',help='Validated AIFS JSON whose valid instants should be matched by real CFS temperature samples');a=p.parse_args()
 init=datetime.datetime.strptime(a.run,'%Y%m%d%H').replace(tzinfo=datetime.timezone.utc)
 c,t=read(a.temperature,a.run,'temperature');cp,r=read(a.precipitation,a.run,'precipitation');assert c==cp
 out={'model':'NOAA CFSv2' if a.model=='cfs' else 'ECMWF AIFS single','run':init.isoformat(),'gridCoordinates':c,'retrievedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Global native grid sampled every 4 degrees; no city interpolation'}
 if a.model=='cfs':
  n=a.days*4;assert len(t)>=n and len(r)>=n
  for frames in [t,r]:
   for i,f in enumerate(frames[:n]):assert f['metadata']['endStep']==(i+1)*6 and f['metadata']['stepType']=='instant'
  out.update(member='01',kind='single-member four-snapshot daily average',days=[])
  for i in range(a.days):
   out['days'].append({'date':(init+datetime.timedelta(days=i)).date().isoformat(),'firstSampleHour':i*24+6,'lastSampleHour':(i+1)*24,'temperatureC':np.mean([f['values'] for f in t[i*4:i*4+4]],axis=0).round(2).tolist(),'precipitationMmDay':np.mean([f['values'] for f in r[i*4:i*4+4]],axis=0).round(2).tolist()})
  out['method']+='; 4 instantaneous 6-hour samples averaged per day; precipitation average rate is not exact accumulated rainfall'
  out['sources']=[f'https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/cfs.{a.run[:8]}/{a.run[8:]}/time_grib_01/{v}.01.{a.run}.daily.grb2' for v in ['tmp2m','prate']]
  if a.compare_with:
   other=json.loads(pathlib.Path(a.compare_with).read_text());other_init=datetime.datetime.fromisoformat(other['run'].replace('Z','+00:00'))
   requested=sorted({other_init+datetime.timedelta(hours=int(f['metadata']['endStep'])) for f in other['frames'] if f['metadata']['shortName']=='2t'})
   out['comparisonSnapshots']=[]
   for valid in requested:
    hours=(valid-init).total_seconds()/3600
    matched=[f for f in t if f['metadata']['endStep']==hours]
    if len(matched)==1:
     f=matched[0];m=f['metadata'];assert m['stepType']=='instant'
     assert m['validityDate']==int(valid.strftime('%Y%m%d')) and m['validityTime']==int(valid.strftime('%H%M'))
     out['comparisonSnapshots'].append({'validTime':valid.isoformat(),'leadHours':int(hours),'temperatureC':f['values'].round(2).tolist(),'statistic':'instantaneous 2m air temperature'})
   out['comparisonMethod']='Actual CFS six-hourly temperature snapshots selected at AIFS valid instants; no temporal interpolation. Different grids and initialization times remain explicit.'

 else:
  assert [x['metadata']['endStep'] for x in t]==[x['metadata']['endStep'] for x in r]
  out.update(kind='deterministic instantaneous temperature and cumulative precipitation snapshots',attribution='ECMWF open data, CC BY 4.0',source=f'https://data.ecmwf.int/forecasts/{a.run[:8]}/{a.run[8:]}z/aifs-single/0p25/oper/',frames=[{'metadata':f['metadata'],'values':f['values'].round(2).tolist()} for f in sorted(t+r,key=lambda f:f['metadata']['endStep'])])
 target=pathlib.Path(a.output);tmp=target.with_suffix(target.suffix+'.tmp');tmp.write_text(json.dumps(out,separators=(',',':'),allow_nan=False));tmp.replace(target)
 print(a.output,len(c),flush=True)
if __name__=='__main__':main()
