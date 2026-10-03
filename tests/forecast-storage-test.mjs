import assert from 'node:assert/strict';
import {generateKeyPairSync,sign,createHash,webcrypto} from 'node:crypto';
import fs from 'node:fs';
import {createForecastService,FORECAST_FILES,FORECAST_POLICY,FORECAST_WRITER_ENABLED} from '../server/forecasts.mjs';
globalThis.crypto??=webcrypto;
const base=FORECAST_POLICY.audience,now=Date.now(),seconds=Math.floor(now/1000),pair=generateKeyPairSync('rsa',{modulusLength:2048}),jwk={...pair.publicKey.export({format:'jwk'}),alg:'RS256',use:'sig',kid:'test-key'};
const claims={iss:FORECAST_POLICY.issuer,aud:base,sub:'repo:bensonlee5@4791094/enso-atlas@1396914466:ref:refs/heads/main',repository:'bensonlee5/enso-atlas',repository_id:'1396914466',repository_owner:'bensonlee5',repository_visibility:'public',runner_environment:'github-hosted',repository_owner_id:'4791094',ref:'refs/heads/main',ref_type:'branch',workflow_ref:FORECAST_POLICY.workflow,event_name:'workflow_dispatch',run_id:'123',run_attempt:'1',sha:'a'.repeat(40),workflow_sha:'a'.repeat(40),iat:seconds,nbf:seconds,exp:seconds+300};
function token(overrides={},header={}){const h=Buffer.from(JSON.stringify({alg:'RS256',typ:'JWT',kid:'test-key',...header})).toString('base64url'),p=Buffer.from(JSON.stringify({...claims,...overrides})).toString('base64url'),input=h+'.'+p;return input+'.'+sign('RSA-SHA256',Buffer.from(input),pair.privateKey).toString('base64url')}
const hash=b=>createHash('sha256').update(b).digest('hex');
const canonical=v=>v&&typeof v==='object'?(Array.isArray(v)?'['+v.map(canonical).join(',')+']':'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}'):JSON.stringify(v);
class Bucket{
 constructor(){this.map=new Map();this.writes=0;this.reads=0;this.failCAS=false}
 snapshot(key){const d=this.map.get(key);if(!d)return null;return {...d,arrayBuffer:async()=>d.bytes.buffer.slice(d.bytes.byteOffset,d.bytes.byteOffset+d.bytes.byteLength),body:new Blob([d.bytes]).stream()}}
 async get(k){this.reads++;return this.snapshot(k)}async head(k){this.reads++;return this.snapshot(k)}
 async put(k,b,o={}){const current=this.map.get(k);if(o.onlyIf?.etagDoesNotMatch==='*'&&current)return null;if(o.onlyIf?.etagMatches&&current?.etag!==o.onlyIf.etagMatches)return null;if(this.failCAS&&k==='forecasts/latest.json')return null;const bytes=Buffer.from(typeof b==='string'?b:new Uint8Array(b)),etag=hash(Buffer.concat([bytes,Buffer.from(String(++this.writes))]));this.map.set(k,{bytes,size:bytes.length,etag,httpEtag:'"'+etag+'"',customMetadata:o.customMetadata||{},httpMetadata:o.httpMetadata||{}});return this.snapshot(k)}
}
let jwksCalls=0;const fetcher=async (u,options)=>{assert.equal(options.redirect,'manual','Workers-safe no-follow JWKS fetch');assert.equal(u,FORECAST_POLICY.jwks);jwksCalls++;return Response.json({keys:[jwk]})},bucket=new Bucket(),env={FORECASTS:bucket},svc=createForecastService({enabled:true,fetcher,clock:()=>now});
function request(path,{method='GET',body,auth=token(),headers={}}={}){return new Request(base+path,{method,headers:{...(auth?{authorization:'Bearer '+auth}:{}),...headers},...(body===undefined?{}:{body,duplex:'half'})})}
async function status(path,options,expected){const r=await svc.handle(request(path,options),env);assert.equal(r.status,expected,await r.text());return r}
assert.equal(FORECAST_WRITER_ENABLED,true,'The explicitly approved scoped writer is enabled');
const disabled=createForecastService({fetcher,enabled:false});assert.equal((await disabled.handle(request('/api/forecasts/promote',{method:'POST',body:'{}'}),env)).status,503);
assert.equal((await svc.handle(request('/api/forecasts/manifest'),{})).status,503);await status('/api/forecasts/manifest',{},404);
for(const changes of [{repository_id:'1'},{repository_owner_id:'1'},{workflow_ref:'other'},{ref:'refs/heads/other'},{aud:'https://wrong.example'},{aud:[base]},{iss:'https://evil.example'},{event_name:'pull_request_target'},{event_name:'pull_request'},{environment:'Production'},{job_workflow_ref:'reusable'},{head_ref:'feature'},{iat:seconds+300},{iat:seconds-1000},{nbf:seconds+300},{exp:seconds-1},{exp:seconds+5000}]){const r=await svc.handle(request('/api/forecasts/promote',{method:'POST',body:'{}',auth:token(changes)}),env);assert(r.status===401||r.status===403,JSON.stringify(changes));}
for(const changes of [{job_workflow_ref:FORECAST_POLICY.workflow},{job_workflow_sha:claims.workflow_sha},{job_workflow_ref:FORECAST_POLICY.workflow,job_workflow_sha:'b'.repeat(40)},{job_workflow_ref:'other/workflow@refs/heads/main',job_workflow_sha:claims.workflow_sha}])await status('/api/forecasts/promote',{method:'POST',body:'{}',auth:token(changes)},403);
await status('/api/forecasts/promote',{method:'POST',body:'{}',auth:token({job_workflow_ref:FORECAST_POLICY.workflow,job_workflow_sha:claims.workflow_sha})},400);
for(const h of [{alg:'none'},{alg:'HS256'},{kid:'missing'},{jku:'https://evil.example'}]){const r=await svc.handle(request('/api/forecasts/promote',{method:'POST',body:'{}',auth:token({},h)}),env);assert.equal(r.status,401)}
let forged=token();forged=forged.slice(0,-8)+'AAAAAAAA';await status('/api/forecasts/promote',{method:'POST',body:'{}',auth:forged},401);
const redirected=createForecastService({enabled:true,clock:()=>now,fetcher:async()=>new Response('',{status:302,headers:{location:'https://untrusted.invalid/keys'}})});assert.equal((await redirected.handle(request('/api/forecasts/promote',{method:'POST',body:'{}'}),env)).status,503,'JWKS redirects fail closed');
assert.equal(bucket.writes,0);assert.equal(jwksCalls,1,'Bounded cached JWKS lookup, including unknown kid');
const filename='verification.json',small=Buffer.from('{}'),digest=hash(small),objectURL='/api/forecasts/objects/'+digest+'/'+filename;
await status(objectURL,{method:'PUT',body:small,auth:null},401);await status(objectURL,{method:'PUT',body:'wrong'},400);await status(objectURL,{method:'PUT',body:small,headers:{'content-length':'9000000'}},413);
await status('/api/forecasts/objects/'+digest+'/secret.env',{method:'PUT',body:small},404);await status('/api/forecasts/objects/'+digest+'/archive%2F2026100100.json',{method:'PUT',body:small},404);
await status('/api/forecasts/objects/'+digest+'/archive/index.json',{method:'PUT',body:Buffer.alloc(200001)},413);
await status(objectURL,{method:'PUT',body:small},201);await status(objectURL,{method:'PUT',body:small},204);await status(objectURL,{method:'HEAD',auth:null},200);await status(objectURL,{auth:null},200);await status('/api/forecasts/objects/'+digest+'/aifs-global-snapshots.json',{},404);
const dir=process.env.ENSO_DATA_DIR?new URL('file://'+process.env.ENSO_DATA_DIR.replace(/\/$/,'')+'/'):new URL('../dist/data/',import.meta.url),files={},objects={},blobs={};
const archiveIndex=JSON.parse(fs.readFileSync(new URL('archive/index.json',dir)));for(const name of [...FORECAST_FILES,'ensemble-member-means.json.gz','archive/index.json',...archiveIndex.issuances.map(r=>'archive/'+r.path)]){const bytes=fs.readFileSync(new URL(name,dir));blobs[name]=bytes;objects[name]={sha256:hash(bytes),bytes:bytes.length};if(FORECAST_FILES.includes(name))files[name]=objects[name]}
const p=n=>JSON.parse(blobs[n]),initializations={raw:p('cfs-weekly-raw-60days.json').run,anomaly:p('cfs-weekly-anomalies.json').initialDate,ensemble:p('ensemble-percentiles.json').run,ensoObservation:p('enso-observations.json').observations.at(-1).date,globalCfs:p('cfs-global-60days.json').run,aifs:p('aifs-global-snapshots.json').run};
function manifest(init=initializations,objs=objects,fs=files){const core={files:fs,objects:objs,initializations:init};return {schemaVersion:1,storageVersion:1,generatedAt:new Date().toISOString(),...core,releaseID:hash(canonical(core))}}
let m=manifest();await status('/api/forecasts/promote',{method:'POST',body:JSON.stringify(m),headers:{'if-none-match':'*'}},400);assert(!bucket.map.has('forecasts/latest.json'));
for(const [name,bytes]of Object.entries(blobs))await status('/api/forecasts/objects/'+objects[name].sha256+'/'+name,{method:'PUT',body:bytes},201);
await status('/api/forecasts/promote',{method:'POST',body:JSON.stringify(m)},412);await status('/api/forecasts/promote',{method:'POST',body:JSON.stringify(m),headers:{'if-none-match':'*'}},200);
let current=await svc.handle(request('/api/forecasts/manifest',{auth:null}),env),etag=current.headers.get('etag');assert.equal((await current.json()).releaseID,m.releaseID);
await status('/api/forecasts/promote',{method:'POST',body:JSON.stringify(m),headers:{'if-none-match':'*'}},412);await status('/api/forecasts/promote',{method:'POST',body:JSON.stringify(m),headers:{'if-match':etag}},200);
// Use a new attempt so rollback/relabel checks reach data validation rather than
// the already-published-attempt conflict guard. Derive dates from the fixture.
claims.run_id='124';
const rollback=manifest({...initializations,ensemble:new Date(Date.parse(initializations.ensemble)-86400000).toISOString()});await status('/api/forecasts/promote',{method:'POST',body:JSON.stringify(rollback),headers:{'if-match':etag}},409);
const relabel=manifest({...initializations,ensemble:new Date(Date.parse(initializations.ensemble)+86400000).toISOString()});await status('/api/forecasts/promote',{method:'POST',body:JSON.stringify(relabel),headers:{'if-match':etag}},400);
claims.run_id='124';
const newVerification=Buffer.from(JSON.stringify({...p('verification.json'),storageTest:true})),newObjects={...objects,'verification.json':{sha256:hash(newVerification),bytes:newVerification.length}},newFiles={...files,'verification.json':newObjects['verification.json']};await status('/api/forecasts/objects/'+hash(newVerification)+'/verification.json',{method:'PUT',body:newVerification},201);
const changed=manifest(initializations,newObjects,newFiles);bucket.failCAS=true;await status('/api/forecasts/promote',{method:'POST',body:JSON.stringify(changed),headers:{'if-match':etag}},412);bucket.failCAS=false;
assert.equal(JSON.parse(bucket.map.get('forecasts/latest.json').bytes).releaseID,m.releaseID,'Failed CAS leaves last-good manifest unchanged');
await status('/api/forecasts/promote',{method:'POST',body:JSON.stringify(changed),headers:{'if-match':etag}},200);await status('/api/forecasts/promote',{method:'POST',body:JSON.stringify(m),headers:{'if-match':etag}},412);
await status('/api/forecasts/promote',{method:'POST',body:JSON.stringify(m),auth:token({run_id:'122'}),headers:{'if-match':(await svc.handle(request('/api/forecasts/manifest'),env)).headers.get('etag')}},409);
await status('/api/forecasts/releases/'+changed.releaseID+'/manifest.json',{},200);await status('/api/forecasts/admin',{},404);
assert.equal((await svc.active(request('/data/ensemble-percentiles.json'),env,'ensemble-percentiles.json')).status,200);
const archiveName='archive/'+archiveIndex.issuances.at(-1).path;const archiveResponse=await svc.active(request('/data/'+archiveName),env,archiveName);assert.equal(archiveResponse.status,200);assert.equal(archiveResponse.headers.get('cache-control'),'no-store');assert.equal((await archiveResponse.json()).run,archiveIndex.issuances.at(-1).run);assert.equal((await svc.active(request('/data/private.json'),env,'private.json')).status,404);
console.log('PASS forecast storage: explicit disable control, signed exact OIDC trust, malicious claims/alg/signature, bounded JWKS/body/paths, immutable object hashes, complete real bundle, per-source rollback/relabel prevention, CAS races and last-good preservation');
