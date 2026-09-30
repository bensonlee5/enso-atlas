import json,pathlib,datetime,math
R=pathlib.Path(__file__).parent
T=json.loads((R/'cfs-tmp2m-60days.json').read_text());P=json.loads((R/'cfs-prate-60days.json').read_text())
coords=T['gridCoordinates'];init=datetime.datetime(2026,9,29,tzinfo=datetime.timezone.utc)
out={'model':'NOAA CFSv2','run':T['run'],'member':'01','kind':'single-member raw forecast; not calibrated anomaly or probability','method':'Arithmetic means of 28 six-hourly instantaneous forecast samples per week at native model grid points. Coordinates selected by nearest native latitude/longitude to roughly 2-degree spacing; no spatial interpolation. Precipitation is mean instantaneous rate expressed in mm/day, not a verified weekly accumulation.','units':{'temperature':'°C','precipitationRate':'mm/day equivalent'},'sources':[T['source'],P['source']],'gridCoordinates':coords,'weeks':[],'sampledLocations':[]}
for w in range(1,9):
 a=(w-1)*28;b=w*28
 def means(d):return [round(sum(f['values'][j] for f in d['frames'][a:b])/28,2) for j in range(len(coords))]
 out['weeks'].append({'week':w,'intervalStart':(init+datetime.timedelta(days=(w-1)*7)).isoformat(),'intervalEndExclusive':(init+datetime.timedelta(days=w*7)).isoformat(),'firstSampleHour':(w-1)*168+6,'lastSampleHour':w*168,'temperature':means(T),'precipitationRate':means(P),'sampleCount':28})
for name,la,lo in [('Los Angeles',34.05,-118.24),('San Francisco',37.77,-122.42),('Sacramento',38.58,-121.49),('San Diego',32.72,-117.16),('Fresno',36.74,-119.79),('New York',40.71,-74.01),('Chicago',41.88,-87.63),('Dallas',32.78,-96.80),('Miami',25.76,-80.19),('Seattle',47.61,-122.33)]:
 j=min(range(len(coords)),key=lambda i:(coords[i][0]-la)**2+(math.cos(math.radians(la))*(coords[i][1]-lo))**2)
 out['sampledLocations'].append({'name':name,'requestedCoordinate':[la,lo],'nativeGridCoordinate':coords[j],'gridIndex':j,'weeks':[{'week':w['week'],'temperature':w['temperature'][j],'precipitationRate':w['precipitationRate'][j]} for w in out['weeks']]})
(R/'cfs-weekly-raw-60days.json').write_text(json.dumps(out,separators=(',',':')))
print('bytes',(R/'cfs-weekly-raw-60days.json').stat().st_size);print(json.dumps(out['sampledLocations'][0],indent=2))
