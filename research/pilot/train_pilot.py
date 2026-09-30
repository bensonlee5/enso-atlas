"""Real-data CPU-only deterministic residual MLP calibration; no ENSO or probabilistic claim."""
from pathlib import Path
import argparse, copy, hashlib, json, os, platform, time
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from threadpoolctl import threadpool_limits

RAW = ['forecast_temp_c', 'forecast_precip_mm']
OBS = ['observed_temp_c', 'observed_precip_mm']
DATES = ['init_date', 'target_start', 'target_end']
CONFIG = dict(seed=42, hidden_layers=[24,12], max_epochs=400, patience=40,
              learning_rate=0.001, alpha=0.01, ridge_alpha=10.0,
              validation_start='2015-01-01', test_start='2018-01-01', purge_days=14,
              climatology_harmonics=2, enso_features=False)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_split(path):
    d = pd.read_csv(path)
    for c in DATES: d[c] = pd.to_datetime(d[c], errors='raise')
    if d.duplicated(['init_date','region']).any(): raise ValueError('Duplicate initialization/region')
    if d.duplicated(['target_start','target_end','region']).any(): raise ValueError('Duplicate target/region')
    if not np.isfinite(d[RAW+OBS].to_numpy()).all(): raise ValueError('Nonfinite data')
    if not ((d.target_end-d.target_start).dt.days == 13).all(): raise ValueError('Targets must be inclusive 14-day intervals')
    if not ((d.target_start-d.init_date).dt.days == 15).all(): raise ValueError('Only weeks 3–4 lead +15 to +28 supported')
    if (d[RAW[1]]<0).any() or (d[OBS[1]]<0).any(): raise ValueError('Negative precipitation')
    for _, part in d.groupby('region'):
        q=part.sort_values('target_start')
        if (q.target_start.iloc[1:].to_numpy() <= q.target_end.iloc[:-1].to_numpy()).any():
            raise ValueError('Overlapping verification windows within region')
    v,t = pd.Timestamp(CONFIG['validation_start']),pd.Timestamp(CONFIG['test_start'])
    lag=pd.Timedelta(days=CONFIG['purge_days'])
    masks={'train':(d.init_date<v)&(d.target_end+lag<v),
           'validation':(d.init_date>=v)&(d.init_date<t)&(d.target_end+lag<t),
           'test':d.init_date>=t}
    splits={k:d.loc[m].sort_values(['init_date','region']).reset_index(drop=True) for k,m in masks.items()}
    if any(x.empty for x in splits.values()): raise ValueError('Empty split')
    regions=sorted(splits['train'].region.unique())
    if any(set(x.region)-set(regions) for x in splits.values()): raise ValueError('Unseen region')
    for left,right in [('train','validation'),('validation','test')]:
        if splits[left].target_end.max()+lag >= splits[right].init_date.min(): raise ValueError('Insufficient purge')
    return splits, len(d)-sum(map(len,splits.values())), regions

def seasonal(d):
    # Target interval midpoint is known at forecast initialization.
    midpoint=d.target_start+pd.Timedelta(days=6.5)
    angle=2*np.pi*(midpoint.dt.dayofyear.to_numpy()-1)/365.2425
    return np.column_stack([np.ones(len(d)), np.sin(angle),np.cos(angle),np.sin(2*angle),np.cos(2*angle)])

def climate_design(d, regions):
    return np.hstack([seasonal(d)*(d.region.to_numpy()==r)[:,None] for r in regions])

def feature_matrix(d, regions, clim_coef):
    season=seasonal(d)[:,1:]
    region=np.column_stack([d.region.to_numpy()==r for r in regions]).astype(float)
    clim=climate_design(d,regions)@clim_coef
    raw=d[RAW].to_numpy()
    return np.column_stack([raw,raw-clim,season,region])

def physical(pred):
    pred=pred.copy(); pred[:,1]=np.maximum(0,pred[:,1]); return pred

def metrics(y,p):
    return {name:{'rmse':float(np.sqrt(np.mean((y[:,i]-p[:,i])**2))),
                  'mae':float(np.mean(np.abs(y[:,i]-p[:,i]))),
                  'bias':float(np.mean(p[:,i]-y[:,i]))}
            for i,name in enumerate(['temperature_c','precipitation_14day_mm'])}

def neural_json_predict(d, artifact):
    regions=artifact['regions']; pre=artifact['preprocessing']
    x=feature_matrix(d,regions,np.array(pre['climatology_coefficients']))
    h=(x-np.array(pre['feature_mean']))/np.array(pre['feature_scale'])
    for i,(w,b) in enumerate(zip(artifact['weights'],artifact['biases'])):
        h=h@np.array(w)+np.array(b)
        if i<len(artifact['weights'])-1: h=np.tanh(h)
    return physical(d[RAW].to_numpy()+h*np.array(pre['residual_scale'])+np.array(pre['residual_mean']))

def run(csv, manifest, output):
    start=time.monotonic(); out=Path(output)
    if out.exists() and any(out.iterdir()): raise ValueError('Output must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    splits,purged,regions=load_split(csv)
    frozen={'config':CONFIG,'dataset_sha256':digest(csv),'manifest_sha256':digest(manifest)}
    (out/'frozen_experiment.json').write_text(json.dumps(frozen,indent=2)+'\n')
    tr,va=splits['train'],splits['validation']
    clim_coef=np.linalg.lstsq(climate_design(tr,regions),tr[OBS].to_numpy(),rcond=None)[0]
    xtr=feature_matrix(tr,regions,clim_coef); xv=feature_matrix(va,regions,clim_coef)
    xm=xtr.mean(0); xs=xtr.std(0); xs[xs<1e-8]=1
    xtr=(xtr-xm)/xs; xv=(xv-xm)/xs
    residual=tr[OBS].to_numpy()-tr[RAW].to_numpy()
    rm=residual.mean(0); rs=residual.std(0); rs[rs<1e-8]=1
    ytr=(residual-rm)/rs; yv=(va[OBS].to_numpy()-va[RAW].to_numpy()-rm)/rs
    bias={r:residual[tr.region.to_numpy()==r].mean(0).tolist() for r in regions}
    ridge=Ridge(alpha=CONFIG['ridge_alpha']).fit(xtr,ytr)
    mlp=MLPRegressor(hidden_layer_sizes=tuple(CONFIG['hidden_layers']),activation='tanh',
        solver='adam',alpha=CONFIG['alpha'],batch_size=min(128,len(tr)),learning_rate_init=CONFIG['learning_rate'],
        random_state=CONFIG['seed'],shuffle=True,max_iter=1,early_stopping=False)
    best_loss=float('inf'); best=None; history=[]; stale=0
    with threadpool_limits(limits=1):
        for epoch in range(1,CONFIG['max_epochs']+1):
            mlp.partial_fit(xtr,ytr)
            loss=float(np.mean((mlp.predict(xv)-yv)**2))
            if not np.isfinite(loss): raise ValueError('Nonfinite training')
            history.append({'epoch':epoch,'training_normalized_residual_mse':float(np.mean((mlp.predict(xtr)-ytr)**2)),
                            'validation_normalized_residual_mse':loss})
            if loss<best_loss-1e-8: best_loss=loss; best=copy.deepcopy(mlp); best_epoch=epoch; stale=0
            else: stale+=1
            if stale>=CONFIG['patience']: break
    artifact={'schema_version':1,'model':'No-ENSO residual MLP pilot','horizon':'weeks 3–4 inclusive 14-day target',
        'units':['degC','mm/14days'],'regions':regions,'activation':'tanh','config':CONFIG,
        'preprocessing':{'climatology_coefficients':clim_coef.tolist(),'feature_mean':xm.tolist(),'feature_scale':xs.tolist(),
                         'residual_mean':rm.tolist(),'residual_scale':rs.tolist()},
        'feature_order':['raw_temp','raw_precip','raw_temp_minus_train_climate','raw_precip_minus_train_climate',
                         'sin1','cos1','sin2','cos2',*['region_'+r for r in regions]],
        'weights':[a.tolist() for a in best.coefs_],'biases':[a.tolist() for a in best.intercepts_],
        'training_region_bias':bias,'ridge_coefficients':ridge.coef_.tolist(),'ridge_intercept':ridge.intercept_.tolist()}
    (out/'model.json').write_text(json.dumps(artifact,indent=2,allow_nan=False)+'\n')
    report={**frozen,'scope':'Six-region CONUS retrospective weeks 3–4 deterministic calibration pilot; not backbone fine-tuning',
        'probabilistic_validation':None,'enso_input':False,'purged_rows':purged,'provenance':json.loads(Path(manifest).read_text()),
        'runtime':{'device':'cpu','seconds':0,'best_epoch':best_epoch,'epochs_run':epoch,
                   'parameter_count':sum(w.size for w in best.coefs_)+sum(b.size for b in best.intercepts_),
                   'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__},
        'split_audit':{},'metrics':{},'caveats':['One seed and one fixed temporal split; no test-set tuning',
        'Coarse regional means hide local extremes and spatial error; not local forecast validation',
        'No ENSO features: revised MEI is not certified issuance-time vintage',
        'Point forecasts only: no calibrated probabilities, empirical interval coverage, CRPS or reliability claim',
        'Rows share times and spatial dependence; sample count is not independent event count',
        'Historical final verification observations; this is retrospective, not simulated operational retraining',
        'Validation/test years held out from fit; boundaries purged at least 14 days past final training/validation target',
        'Uncertainty/significance of skill differences not established; no robust superiority claim']}
    records=[]
    for name,d in splits.items():
        report['split_audit'][name]={'rows':len(d),'initializations':int(d.init_date.nunique()),'regions':regions,
            'initialization_min':str(d.init_date.min().date()),'initialization_max':str(d.init_date.max().date()),
            'target_start_min':str(d.target_start.min().date()),'target_end_max':str(d.target_end.max().date()),
            'initialization_years':sorted(map(int,d.init_date.dt.year.unique()))}
        # Test features are constructed only after checkpoint selection has finished.
        x=(feature_matrix(d,regions,clim_coef)-xm)/xs; y=d[OBS].to_numpy(); raw=d[RAW].to_numpy()
        predictions={'raw_cfsv2':raw,'train_seasonal_climatology':physical(climate_design(d,regions)@clim_coef),
            'train_region_bias_correction':physical(raw+np.array([bias[r] for r in d.region])),
            'ridge_residual':physical(raw+ridge.predict(x)*rs+rm),'neural_residual_no_enso':physical(raw+best.predict(x)*rs+rm)}
        if {'persistence_temp_c','persistence_precip_mm'}.issubset(d.columns):
            predictions['lagged_observation_persistence']=d[['persistence_temp_c','persistence_precip_mm']].to_numpy()
        assert np.allclose(predictions['neural_residual_no_enso'],neural_json_predict(d,artifact),atol=1e-10)
        report['metrics'][name]={'overall':{k:metrics(y,p) for k,p in predictions.items()},
            'by_region':{r:{k:metrics(y[d.region==r],p[d.region==r]) for k,p in predictions.items()} for r in regions}}
        record=d[DATES+['region']+OBS].copy(); record['split']=name
        for k,p in predictions.items(): record[k+'_temperature_c']=p[:,0]; record[k+'_precipitation_mm']=p[:,1]
        records.append(record)
    pd.concat(records).to_csv(out/'predictions.csv',index=False)
    report['runtime']['seconds']=time.monotonic()-start
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (out/'training_history.json').write_text(json.dumps(history,indent=2)+'\n')
    print(json.dumps({'runtime':report['runtime'],'test':report['metrics']['test']['overall']},indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--csv',required=True); p.add_argument('--manifest',required=True); p.add_argument('--output',required=True)
    a=p.parse_args(); run(a.csv,a.manifest,a.output)
