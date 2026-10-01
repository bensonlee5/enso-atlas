"""Archive small immutable issued forecasts before replacement, without deleting history."""
import datetime as dt, hashlib, json, pathlib

def archive_product(product_path, archive_dir):
    archive_dir=pathlib.Path(archive_dir);archive_dir.mkdir(parents=True,exist_ok=True)
    data=pathlib.Path(product_path).read_bytes();p=json.loads(data)
    run=dt.datetime.fromisoformat(p['run']); key=run.strftime('%Y%m%d%H')+'.json'
    dest=archive_dir/key
    if not dest.exists():
        frames=p['weeks']+[p['remainingDays57to60']]
        locations=[]
        for loc in p['sampledLocations']:
            i=loc['gridIndex']; periods=[]
            for w in frames:
                period={k:w[k] for k in ['intervalStart','intervalEndExclusive','firstSampleHour','lastSampleHour','sampleCountPerMember']}
                period['leadWeek']=w['week']
                for field in ('temperature','precipitationRate'):
                    period[field]={q:w[field][q][i] for q in ('p1','p5','p10','p50','p90','p95','p99') if q in w[field]}
                periods.append(period)
            locations.append({**loc,'periods':periods})
        record={'schemaVersion':1,'archivedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'run':p['run'],'sourceProductSha256':hashlib.sha256(data).hexdigest(),'memberCount':p['memberCount'],'model':p['model'],'sources':p['sources'],'units':p['units'],'method':p['method'],'locations':locations}
        # Exclusive creation means a later retrieval cannot rewrite an issued forecast.
        with dest.open('x') as f: json.dump(record,f,separators=(',',':'));f.write('\n')
    record=json.loads(dest.read_text())
    index_path=archive_dir/'index.json'
    index=json.loads(index_path.read_text()) if index_path.exists() else {'schemaVersion':1,'issuances':[]}
    entries={x['run']:x for x in index['issuances']}
    entries[record['run']]={'run':record['run'],'path':key,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'archivedAt':record['archivedAt']}
    # The rolling verification window bounds traffic. Older immutable files remain in Git.
    index['issuances']=sorted(entries.values(),key=lambda x:x['run'])[-400:]
    index['retention']='Latest 400 issuances indexed; older immutable files remain available in repository history and archive directory.'
    index_path.write_text(json.dumps(index,indent=2)+'\n')
    return dest
