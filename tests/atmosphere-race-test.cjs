'use strict';
// Small VM harness: no browser allocation and no external requests.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,{value:'0',innerHTML:'',textContent:'',disabled:false,setAttribute(){}});return nodes.get(id)},requests=[];
const context={console,$:node,Date,Math,Number,AbortSignal,AbortController,setTimeout,clearTimeout,tempUnit:()=> '°C',fmt:x=>x,convertTemp:x=>x,fetch:(url,options)=>new Promise((resolve,reject)=>requests.push({url,options,resolve,reject}))};
vm.createContext(context);const evaluate=code=>vm.runInContext(code,context);
evaluate(fs.readFileSync(path.join(__dirname,'../dist/atmosphere.js'),'utf8'));
const snapshot=JSON.parse(fs.readFileSync(path.join(__dirname,'../dist/data/atmosphere-sf.json')));
const response=(latitude,longitude)=>{const data=structuredClone(snapshot);Object.assign(data,{latitude,longitude});return {ok:true,json:async()=>data}};
const submit=(latitude,longitude)=>{node('airLat').value=String(latitude);node('airLon').value=String(longitude);return node('airForm').onsubmit({preventDefault(){}})};
const read=()=>JSON.parse(evaluate('JSON.stringify({latitude:airData.latitude,longitude:airData.longitude,requested:airRequestedCoordinate,snapshot:airIsSnapshot,retrieved:airRetrieved})'));
(async()=>{
 const live=submit(40,-80);requests[1].resolve(response(40,-80));await live;const accepted=read();
 requests[0].resolve({ok:true,json:async()=>snapshot});await new Promise(r=>setImmediate(r));
 assert.deepEqual(read(),accepted,'a late bundled snapshot must not replace a live column or its provenance');
 const old=submit(41,-81),newer=submit(42,-82);assert(requests[2].options.signal.aborted);
 requests[3].resolve(response(42,-82));await newer;requests[2].resolve(response(41,-81));await old;
 assert.equal(read().latitude,42);assert.deepEqual(read().requested,[42,-82]);
 const latest=read(),invalid=submit(43,-83);requests[4].resolve({ok:true,json:async()=>({latitude:43,longitude:-83,elevation:0,hourly:{time:['2026-10-02T00:00']}})});await invalid;
 assert.deepEqual(read(),latest,'invalid columns must not partially commit location/freshness');assert.match(node('airStatus').textContent,/Could not load/);assert.equal(node('loadAir').disabled,false);
 const wrongLocation=submit(44,-84);requests[5].resolve(response(10,10));await wrongLocation;assert.deepEqual(read(),latest);
 console.log('PASS atmosphere: late snapshot, repeated request race, abort, invalid/mismatched response and provenance retention');
})().catch(error=>{console.error(error);process.exitCode=1});
