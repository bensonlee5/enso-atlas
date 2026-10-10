"""Bounded native-node city extraction; never infer extra model resolution."""
import numpy as np
CITIES=[('Houston',29.76,-95.37),('Denver',39.74,-104.99),('Palo Alto',37.44188,-122.14302),('San Francisco',37.77,-122.42),('Los Angeles',34.05,-118.24),('Sacramento',38.58,-121.49),('San Diego',32.72,-117.16),('Fresno',36.74,-119.79),('New York',40.71,-74.01),('Chicago',41.88,-87.63),('Dallas',32.78,-96.8),('Miami',25.76,-80.19),('Seattle',47.61,-122.33),('London',51.51,-.13),('Paris',48.86,2.35),('Tokyo',35.68,139.69),('Sydney',-33.87,151.21),('Singapore',1.35,103.82),('São Paulo',-23.55,-46.63),('Cape Town',-33.92,18.42)]
def nearest_points(lats,lons,locations):
 lat=np.radians(lats);indices=[];points=[];latitude_rows=np.unique(lats);longitude_columns=np.unique(lons)
 for name,la,lo in locations:
  a=np.sin((lat-np.radians(la))/2)**2+np.cos(lat)*np.cos(np.radians(la))*np.sin(np.radians(lons-lo)/2)**2
  i=int(np.argmin(a));indices.append(i)
  row=int(np.searchsorted(latitude_rows,lats[i]));south=float((latitude_rows[max(0,row-1)]+lats[i])/2);north=float((latitude_rows[min(len(latitude_rows)-1,row+1)]+lats[i])/2)
  points.append({'nativeCellLatitudeBounds':[south,north],'nativeCellLongitudeHalfWidth':float(np.median(np.diff(longitude_columns))/2),'name':name,'requestedCoordinate':[la,lo],'nativeGridCoordinate':[float(lats[i]),float(lons[i])],'distanceKm':round(float(12742*np.arcsin(np.sqrt(np.clip(a[i],0,1)))),3)})
 return np.asarray(indices),points
