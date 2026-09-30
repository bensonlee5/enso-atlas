"""Build a frozen no-ENSO pilot input, raw physical units, from genuine archived fields."""
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib
R=Path(__file__).resolve().parent
KEY=['start_date','lat','lon']
# Fixed before scoring: 14-day-spaced initializations, one 14-day target lead.
DATES=pd.date_range('1999-01-01','2021-12-31',freq='14D')
f={}
for var in ['tmp2m','precip']:
 d=pd.read_hdf(R/'raw'/f'iri-cfsv2-{var}-all-us1_5-ensembled.h5')
 col=f'iri_cfsv2_{var}-15.5d'
 d=d.loc[d.start_date.isin(DATES),KEY+[col]].rename(columns={col:f'forecast_{var}'})
 assert not d.duplicated(KEY).any()
 f[var]=d
x=f['tmp2m'].merge(f['precip'],on=KEY,validate='one_to_one')
grid=x[['lat','lon']].drop_duplicates().sort_values(['lat','lon'])
grid['region']=np.where(grid.lon<255,'west',np.where(grid.lon<275,'central','east'))+'_'+np.where(grid.lat<37.5,'south','north')
grid['weight']=np.cos(np.deg2rad(grid.lat)); grid.to_csv(R/'region_grid.csv',index=False)
x=x.merge(grid,on=['lat','lon'],validate='many_to_one')
x=x.rename(columns={'start_date':'init_date'});x['target_start']=x.init_date+pd.Timedelta(days=15);x['target_end']=x.init_date+pd.Timedelta(days=28)
x['persistence_start']=x.init_date-pd.Timedelta(days=43);x['persistence_end']=x.init_date-pd.Timedelta(days=30)
for var in ['tmp2m','precip']:
 d=pd.read_hdf(R/'raw'/f'gt-us_{var}_1.5x1.5-14d.h5')[[var]].reset_index()
 for datecol,prefix in [('target_start','observed'),('persistence_start','persistence')]:
  s=d.loc[d.start_date.isin(x[datecol]),KEY+[var]].rename(columns={'start_date':datecol,var:prefix+'_'+var})
  x=x.merge(s,on=[datecol,'lat','lon'],how='left',validate='many_to_one')
 del d
values=[p+'_'+v for p in ['forecast','observed','persistence'] for v in ['tmp2m','precip']]
counts=grid.groupby('region').size().to_dict();rows=[];dropped=[]
for (init,region),g in x.groupby(['init_date','region'],sort=True):
 if len(g)!=counts[region] or not np.isfinite(g[values]).all().all():
  dropped.append({'init_date':str(init.date()),'region':region,'cells':len(g),'missing_values':int(g[values].isna().sum().sum())});continue
 row={k:g.iloc[0][k] for k in ['init_date','target_start','target_end','region','persistence_start','persistence_end']}
 for c in values:row[c]=float(np.average(g[c],weights=g.weight))
 row['grid_cells']=len(g);rows.append(row)
out=pd.DataFrame(rows).rename(columns={p+'_'+v:p+'_'+name for p in ['forecast','observed','persistence'] for v,name in [('tmp2m','temp_c'),('precip','precip_mm')]})
# Retrospectively revised MEI is intentionally not in the model input CSV.
mei=pd.read_hdf(R/'raw/gt-mei.h5')[['start_date','mei']].sort_values('start_date')
sens=out[['init_date','region']].copy();sens['index_lookup_date']=sens.init_date-pd.Timedelta(days=60)
sens=pd.merge_asof(sens.sort_values('index_lookup_date'),mei,left_on='index_lookup_date',right_on='start_date',direction='backward').rename(columns={'mei':'lagged_mei_revised','start_date':'mei_archive_date'})
sens.to_csv(R/'retrospective_mei_sensitivity_only.csv',index=False)
out=out.sort_values(['init_date','region']);out.to_csv(R/'pairs.csv',index=False,float_format='%.8f')
audit={'rows':len(out),'unique_init_dates':int(out.init_date.nunique()),'regions':counts,'first_init':str(out.init_date.min().date()),'last_init':str(out.init_date.max().date()),'last_target_end':str(out.target_end.max().date()),'target_days':14,'target_start_lead_days':15,'target_end_lead_days':28,'raw_candidate_rows':int(x.groupby(['init_date','region']).ngroups),'dropped_incomplete_regions':len(dropped),'per_year_rows':{str(k):int(v) for k,v in out.groupby(out.init_date.dt.year).size().items()},'expected_init_dates':len(DATES),'missing_initializations':[str(t.date()) for t in DATES.difference(out.init_date.unique())],'csv_sha256':hashlib.sha256((R/'pairs.csv').read_bytes()).hexdigest()}
(R/'audit.json').write_text(json.dumps(audit,indent=2));(R/'dropped_rows.json').write_text(json.dumps(dropped,indent=2));print(json.dumps(audit,indent=2))
