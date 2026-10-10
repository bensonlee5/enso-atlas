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
            native=p.get('nativePointForecasts',{});native_index=next((j for j,n in enumerate(native.get('locations',[])) if n['name']==loc['name'] and n['requestedCoordinate']==loc['requestedCoordinate']),None) if native.get('run')==p['run'] else None
            archive_loc=dict(loc)
            if native_index is not None:
                archive_loc={**native['locations'][native_index],'nativeCatalogIndex':native_index,'sampling':'Full native Gaussian node; no downscaling'}
            for w in frames:
                period={k:w[k] for k in ['intervalStart','intervalEndExclusive','firstSampleHour','lastSampleHour','sampleCountPerMember']}
                period['leadWeek']=w['week']
                for field in ('temperature','precipitationRate'):
                    source=native['periods'][w['week']-1][field] if native_index is not None else w[field];index=native_index if native_index is not None else i
                    period[field]={q:source[q][index] for q in ('p1','p5','p10','p50','p90','p95','p99') if q in source}
                periods.append(period)
            locations.append({**archive_loc,'periods':periods})
        record={'schemaVersion':1,'archivedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'run':p['run'],'sourceProductSha256':hashlib.sha256(data).hexdigest(),'memberCount':p['memberCount'],'model':p['model'],'sources':p['sources'],'units':p['units'],'method':p['method'],'locations':locations}
        # Preserve membership and source evidence for lagged products. Earlier
        # immutable four-member archives intentionally retain their original schema.
        for field in ('memberIDs', 'members', 'laggedEnsemble', 'lagDays', 'initializationRange', 'quantileMethod', 'provenance', 'coverage', 'sampling'):
            if field in p:
                record[field] = p[field]
        # Exclusive creation means a later retrieval cannot rewrite an issued forecast.
        with dest.open('x') as f: json.dump(record,f,separators=(',',':'));f.write('\n')
    record=json.loads(dest.read_text())
    index_path=archive_dir/'index.json'
    index=json.loads(index_path.read_text()) if index_path.exists() else {'schemaVersion':1,'issuances':[]}
    entries={x['run']:x for x in index['issuances']}
    entries[record['run']]={'run':record['run'],'path':key,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'archivedAt':record['archivedAt']}
    # Bound the active verification window. This never deletes historical data.
    index['issuances']=sorted(entries.values(),key=lambda x:x['run'])[-400:]
    index['retention']='Latest 400 issuances indexed for verification; older immutable objects are not automatically deleted. New forecast data is stored outside Git history.'
    index_path.write_text(json.dumps(index,indent=2)+'\n')
    return dest
