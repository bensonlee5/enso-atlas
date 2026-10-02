"""Keep auditable member means out of the browser's render bundle.
The gzip artifact retains six-decimal member temporal averages and is published
to object storage beside the hash-verified forecast, never Git history.
No quantile is reconstructed from other quantiles.
"""
import gzip, hashlib, json, pathlib, math, io
KEYS=('p1','p5','p10','p50','p90','p95','p99')
LEVELS=(.01,.05,.1,.5,.9,.95,.99)
ARTIFACT='ensemble-member-means.json.gz'
def separate_member_means(product, folder):
    periods=product['weeks']+[product['remainingDays57to60']]
    artifact={k:product[k] for k in ('run','memberIDs','gridCoordinates')}
    artifact['periods']=[{'intervalStart':w['intervalStart'],'intervalEndExclusive':w['intervalEndExclusive'],'memberMeans':w.pop('memberMeans')} for w in periods]
    body=gzip.compress(json.dumps(artifact,separators=(',',':'),allow_nan=False).encode(),mtime=0)
    folder=pathlib.Path(folder);folder.mkdir(parents=True,exist_ok=True)
    dest=folder/ARTIFACT;pending=dest.with_suffix('.gz.tmp');pending.write_bytes(body);pending.replace(dest)
    product['memberMeansArtifact']={'file':ARTIFACT,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'format':'gzip-json','decimalPlaces':6}
    return product

def validate_member_artifact(product,folder):
    meta=product['memberMeansArtifact'];assert meta['file']==ARTIFACT and meta['format']=='gzip-json' and meta['decimalPlaces']==6
    body=(pathlib.Path(folder)/ARTIFACT).read_bytes();assert len(body)==meta['bytes'] and len(body)<8000000
    assert hashlib.sha256(body).hexdigest()==meta['sha256'],'Member artifact hash mismatch'
    with gzip.GzipFile(fileobj=io.BytesIO(body)) as compressed:
        raw=compressed.read(20000001)
    assert len(raw)<20000000,'Member artifact exceeds bounded size'
    artifact=json.loads(raw);assert all(artifact[k]==product[k] for k in ('run','memberIDs','gridCoordinates'))
    periods=product['weeks']+[product['remainingDays57to60']];assert len(artifact['periods'])==len(periods)
    for period,w in zip(artifact['periods'],periods):
        assert all(period[k]==w[k] for k in ('intervalStart','intervalEndExclusive'))
        for field in ('temperature','precipitationRate'):
            means=period['memberMeans'][field];assert len(means)==product['memberCount']
            assert all(len(row)==len(product['gridCoordinates']) and all(math.isfinite(v) for v in row) for row in means)
            for i,column in enumerate(zip(*means)):
                ordered=sorted(column)
                for key,level in zip(KEYS,LEVELS):
                    pos=(len(ordered)-1)*level;lo=math.floor(pos);fraction=pos-lo
                    expected=ordered[lo]*(1-fraction)+ordered[min(lo+1,len(ordered)-1)]*fraction
                    assert abs(w[field][key][i]-expected)<=.000501,'Quantile differs from authentic member temporal means'
    return artifact
