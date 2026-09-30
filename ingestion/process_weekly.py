import sys,pathlib,json,datetime
R=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'python-packages'))
import h5py,numpy as np
out={'model':'NOAA CPC CFSv2 weekly ensemble anomalies','initialDate':'2026-09-28','ensembleMembers':16,'baseline':'1999–2010 model climatology','kind':'Published ensemble-mean anomaly, not probability','fields':{}}
for v in ['prec','tmpsfc']:
 with h5py.File(R/f'{v}-weekly.nc') as f:
  lon=(f['lon'][:]+180)%360-180;lat=f['lat'][:];xx,yy=np.meshgrid(lon,lat);mask=(xx>=-126)&(xx<=-66)&(yy>=24)&(yy<=50)
  out['gridCoordinates']=np.column_stack((yy[mask],xx[mask])).tolist()
  arr=f['anom'][0,:,0,:,:]
  frames=[]
  for i,t in enumerate(f['time'][:]):
   start=datetime.date(2021,1,1)+datetime.timedelta(days=int(t));vals=arr[i][mask]
   frames.append({'week':i+1,'startDate':str(start),'endDate':str(start+datetime.timedelta(days=6)),'values':[round(float(x),3) if x!=-9999 else None for x in vals]})
  out['fields'][v]={'unit':'mm/day' if v=='prec' else '°C anomaly','source':f'https://www.cpc.ncep.noaa.gov/products/CFSv2/weekly/data/CFSv2.{v}.20260928.wkly.anom.nc','frames':frames}
(R/'cfs-weekly-anomalies.json').write_text(json.dumps(out,separators=(',',':')))
print('points',len(out['gridCoordinates']),'size',(R/'cfs-weekly-anomalies.json').stat().st_size)
