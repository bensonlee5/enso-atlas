'use strict';
// Pure shared schema used before browser adoption and server publication.
(function(root){const publicDataFiles=['cfs-weekly-raw-60days.json','cfs-weekly-anomalies.json','enso-observations.json','ensemble-percentiles.json','verification.json','cfs-global-60days.json','aifs-global-snapshots.json'];
function requireData(ok,message){if(!ok)throw Error(message)}
function goodDate(s){return typeof s==='string'&&/^\d{4}-\d{2}-\d{2}/.test(s)&&Number.isFinite(Date.parse(s))}
function numericArray(a,n,nullable=false){return Array.isArray(a)&&a.length===n&&a.every(x=>Number.isFinite(x)||(nullable&&x===null))}
// Shared optional extension validation. Call metadata validator from the existing
// synchronous product validator and await payload validator before promotion.
function validateAifsFineMetadata(product) {
 const f=product.fineFirstWeek;if(f===undefined)return null;
 const assert=(v,m)=>{if(!v)throw Error('AIFS fine: '+m)};
 assert(f.schemaVersion===1&&f.encoding==='gzip-base64-int16-le'&&f.scale===.1&&f.missingValue===-32768,'encoding');
 const g=f.grid;assert(g?.rows===181&&g.columns===360&&g.latitudeStart===90&&g.longitudeStart===-180&&g.latitudeStep===-1&&g.longitudeStep===1,'grid');
 assert(f.sourceGridDegrees===.25&&f.sampleSpacingDegrees===1,'resolution');
 assert(f.temperature?.length===29&&f.precipitation?.length===28,'horizon');
 const run=Date.parse(product.run);assert(Number.isFinite(run),'initialization');
 const count=n=>Number.isInteger(n)&&n>=0&&n<=65160;
 for(const [kind,frames] of [['temperature',f.temperature],['precipitation',f.precipitation]])for(const [i,frame] of frames.entries()){
  const h=(kind==='temperature'?i:i+1)*6;assert(frame.leadHours===h,'lead order');
  assert(count(frame.missingCells),'missing count');
  assert(typeof frame.valuesPacked==='string'&&frame.valuesPacked.length<=200000&&frame.valuesPacked.length%4===0&&/^[A-Za-z0-9+/]+={0,2}$/.test(frame.valuesPacked),'packed field');
  if(kind==='temperature')assert(Date.parse(frame.validTime)===run+h*3600000,'valid time');
  else{assert(Date.parse(frame.intervalStart)===run+(h-6)*3600000&&Date.parse(frame.intervalEnd)===run+h*3600000,'interval');assert(count(frame.packingNoiseClampedCells)&&frame.missingCells+frame.packingNoiseClampedCells<=65160&&Number.isFinite(frame.packingToleranceMm)&&frame.packingToleranceMm>=0,'quality');}
 }
 return f;
}
async function decodeAifsFineFrame(frame){
 const b=Uint8Array.from(atob(frame.valuesPacked),c=>c.charCodeAt(0));
 const stream=new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip')),reader=stream.getReader();
 const result=new Uint8Array(130320);let size=0;
 try{for(;;){const {done,value}=await reader.read();if(done)break;if(size+value.length>result.length)throw Error('AIFS fine: expanded size');result.set(value,size);size+=value.length;}}catch(e){await reader.cancel().catch(()=>{});throw e;}
 if(size!==result.length)throw Error('AIFS fine: truncated field');
 const data=new DataView(result.buffer),values=new Int16Array(65160);let missing=0;
 for(let i=0;i<values.length;i++){values[i]=data.getInt16(i*2,true);if(values[i]===-32768)missing++;}
 if(missing!==frame.missingCells)throw Error('AIFS fine: missing count mismatch');return values;
}
async function validateAifsFinePayload(product){
 const f=validateAifsFineMetadata(product);if(!f)return;
 for(const frame of f.temperature){const a=await decodeAifsFineFrame(frame);if(a.some(v=>v!==-32768&&(v< -1200||v>700)))throw Error('AIFS fine: temperature range');}
 for(const frame of f.precipitation){const a=await decodeAifsFineFrame(frame);if(a.some(v=>v!==-32768&&v<0))throw Error('AIFS fine: negative interval');}
}

function validatePublicProducts(p){const raw=p[publicDataFiles[0]],a=p[publicDataFiles[1]],e=p[publicDataFiles[2]],q=p[publicDataFiles[3]];
 for(const product of [raw,a,q]){requireData(Array.isArray(product.gridCoordinates)&&product.gridCoordinates.length>0&&product.gridCoordinates.length<10000,'Invalid grid');requireData(product.gridCoordinates.every(c=>Array.isArray(c)&&c.length===2&&c.every(Number.isFinite)&&Math.abs(c[0])<=90&&Math.abs(c[1])<=180),'Invalid coordinates')}
 requireData(goodDate(raw.run)&&goodDate(q.run)&&goodDate(a.initialDate),'Invalid initialization');
 requireData(Array.isArray(raw.weeks)&&raw.weeks.length===8,'Raw weeks');for(const w of raw.weeks){requireData(goodDate(w.intervalStart)&&goodDate(w.intervalEndExclusive),'Raw dates');for(const field of ['temperature','precipitationRate'])requireData(numericArray(w[field],raw.gridCoordinates.length),'Raw values')}
 for(const field of ['tmpsfc','prec']){const x=a.fields[field];requireData(x?.frames?.length===4,'Anomaly weeks');for(const f of x.frames)requireData(goodDate(f.startDate)&&goodDate(f.endDate)&&numericArray(f.values,a.gridCoordinates.length,true),'Anomaly data')}
 requireData(q.schemaVersion===3&&q.coverage==='global'&&q.sampling?.longitudePeriodic===true&&q.gridCoordinates.length>=4000&&q.gridCoordinates.some(c=>c[0]<-80)&&q.gridCoordinates.some(c=>c[0]>80)&&q.gridCoordinates.some(c=>c[1]<-170)&&q.gridCoordinates.some(c=>c[1]>170),'Worldwide ensemble coverage required');
 requireData([4,8,12,16].includes(q.memberCount)&&q.memberIDs?.length===q.memberCount&&new Set(q.memberIDs).size===q.memberCount&&q.weeks?.length===8&&q.remainingDays57to60,'Ensemble structure');
 if(q.laggedEnsemble){requireData([2,3,4].includes(q.lagDays)&&q.memberCount===4*q.lagDays&&q.members?.length===q.memberCount,'Lagged ensemble membership');requireData(q.initializationRange?.length===2&&q.initializationRange.every(goodDate)&&Date.parse(q.initializationRange[1])===Date.parse(q.run)&&Date.parse(q.initializationRange[1])-Date.parse(q.initializationRange[0])===(q.lagDays-1)*86400000,'Lagged initialization window');const ids=q.members.map(m=>m.id);requireData(new Set(ids).size===q.memberCount&&ids.every((id,i)=>id===q.memberIDs[i])&&q.members.every(m=>goodDate(m.initialization)&&['01','02','03','04'].includes(m.member)&&Date.parse(m.initialization)>=Date.parse(q.initializationRange[0])&&Date.parse(m.initialization)<=Date.parse(q.run)),'Lagged member identities')}
 for(const w of [...q.weeks,q.remainingDays57to60]){requireData(goodDate(w.intervalStart)&&goodDate(w.intervalEndExclusive)&&w.memberCount===q.memberCount,'Ensemble dates/count');for(const f of ['temperature','precipitationRate']){const keys=['p1','p5','p10','p50','p90','p95','p99'];for(const key of keys)requireData(numericArray(w[f][key],q.gridCoordinates.length),'Complete seven-quantile values required');requireData(keys.slice(1).every((key,j)=>w[f][key].every((v,i)=>w[f][keys[j]][i]<=v)),'Unordered quantiles');}}
 const artifact=q.memberMeansArtifact;requireData(artifact?.file==='ensemble-member-means.json.gz'&&artifact.format==='gzip-json'&&artifact.decimalPlaces===6&&artifact.bytes>0&&artifact.bytes<8000000&&/^[a-f0-9]{64}$/.test(artifact.sha256),'Auditable member artifact required');
 requireData(Array.isArray(e.observations)&&e.observations.length>0&&e.observations.length<=200,'ENSO rows');for(const o of e.observations)requireData(goodDate(o.date)&&Number.isFinite(o.nino34?.anomaly),'ENSO values');
 const sources=[...(raw.sources||[]),...(q.sources||[]),a.fields.prec.source,a.fields.tmpsfc.source,e.source];for(const source of sources){const u=new URL(source);requireData(u.protocol==='https:'&&['nomads.ncep.noaa.gov','www.cpc.ncep.noaa.gov'].includes(u.hostname),'Unapproved source URL')}
 requireData(Date.now()-Date.parse(raw.run)<14*86400000&&Date.now()-Date.parse(q.run)<14*86400000,'Repository model data too old');const v=p['verification.json'];requireData(v?.schemaVersion===1&&goodDate(v.generatedAt)&&v.counts&&v.temperature,'Invalid verification report');for(const k of ['verified','pending'])requireData(Number.isInteger(v.counts[k])&&v.counts[k]>=0,'Invalid verification counts');for(const group of ['byLead','byLocation']){requireData(Array.isArray(v.temperature[group]),'Invalid verification group');for(const row of v.temperature[group])for(const key of ['bias','mae','rmse'])requireData(row[key]===null||Number.isFinite(row[key]),'Invalid verification score')}const gc=p['cfs-global-60days.json'],ga=p['aifs-global-snapshots.json'];for(const g of [gc,ga]){requireData(goodDate(g.run)&&g.gridCoordinates?.length>1000&&g.gridCoordinates.length<10000,'Invalid global grid/run');requireData(g.gridCoordinates.every(c=>c.length===2&&c.every(Number.isFinite)&&Math.abs(c[0])<=90&&Math.abs(c[1])<=180),'Global coordinates')}requireData(gc.days?.length===60&&ga.frames?.length===8,'Global horizon');for(const [i,f] of gc.days.entries()){requireData(goodDate(f.date)&&f.firstSampleHour===i*24+6&&f.lastSampleHour===(i+1)*24&&f.date===new Date(Date.parse(gc.run)+i*86400000).toISOString().slice(0,10),'Global date/sample window');if(f.intervalStart!==undefined||f.intervalEndExclusive!==undefined)requireData(Date.parse(f.intervalStart)===Date.parse(gc.run)+i*86400000&&Date.parse(f.intervalEndExclusive)===Date.parse(gc.run)+(i+1)*86400000,'Global rolling window');for(const key of ['temperatureC','precipitationMmDay'])requireData(numericArray(f[key],gc.gridCoordinates.length),'Global field')}if(gc.comparisonSnapshots)for(const f of gc.comparisonSnapshots)requireData(goodDate(f.validTime)&&numericArray(f.temperatureC,gc.gridCoordinates.length)&&f.statistic==='instantaneous 2m air temperature','Invalid matched snapshot');for(const f of ga.frames)requireData(['2t','tp'].includes(f.metadata?.shortName)&&numericArray(f.values,ga.gridCoordinates.length),'AIFS field');for(const source of [...(gc.sources||[]),ga.source]){const u=new URL(source);requireData(u.protocol==='https:'&&['nomads.ncep.noaa.gov','data.ecmwf.int'].includes(u.hostname),'Unapproved global source')}validateAifsFineMetadata(ga);requireData(Date.now()-Date.parse(ga.run)<14*86400000&&Date.now()-Date.parse(gc.run)<14*86400000,'Global forecast stale');return p;
}

const api={publicDataFiles,requireData,goodDate,numericArray,validatePublicProducts,validateAifsFineMetadata,validateAifsFinePayload,decodeAifsFineFrame};root.AtlasForecastSchema=api;if(typeof module!=='undefined')module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
