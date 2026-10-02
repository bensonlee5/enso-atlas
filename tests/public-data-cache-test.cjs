const fs=require('fs'),vm=require('vm'),assert=require('assert');
const sandbox={console,TextEncoder,URL,Date,Number,Promise,Math,Array,JSON,AbortSignal,initialLoad:new Promise(()=>{}),ensembleLoad:Promise.resolve(),setInterval(){},document:{visibilityState:'hidden'},fetch(){throw Error('No network')},cfs:{run:'2026-10-02T00:00:00Z'},ensemble:{run:'2026-10-02T00:00:00Z'},anomalies:{initialDate:'2026-09-28'},ensoLatest:{date:'2026-09-30'},globalAssets:{cfs:{run:'2026-10-02T00:00:00Z'},aifs:{run:'2026-10-02T00:00:00Z'}}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(require('path').join(__dirname,'../dist/forecast-schema.js'),'utf8'),sandbox);vm.runInContext(fs.readFileSync('dist/public-data.js','utf8'),sandbox);
sandbox.products={'cfs-weekly-raw-60days.json':{run:'2026-10-02T00:00:00Z'},'ensemble-percentiles.json':{run:'2026-10-02T00:00:00Z'},'cfs-weekly-anomalies.json':{initialDate:'2026-09-28'},'enso-observations.json':{observations:[{date:'2026-09-30'}]},'cfs-global-60days.json':{run:'2026-10-02T00:00:00Z'},'aifs-global-snapshots.json':{run:'2026-10-02T00:00:00Z'}};
assert(vm.runInContext('bundleNotOlderThanLoaded(products)',sandbox));sandbox.products['ensemble-percentiles.json'].run='2026-10-01T00:00:00Z';assert.equal(vm.runInContext('bundleNotOlderThanLoaded(products)',sandbox),false);sandbox.products['ensemble-percentiles.json'].run='2026-10-03T00:00:00Z';assert(vm.runInContext('bundleNotOlderThanLoaded(products)',sandbox));sandbox.products['aifs-global-snapshots.json'].run='2026-10-01T00:00:00Z';assert.equal(vm.runInContext('bundleNotOlderThanLoaded(products)',sandbox),false);console.log('PASS cache/network source run monotonicity: newer fallback cannot be replaced by an older cached product');
(async()=>{
 sandbox.localStorage={getItem:()=>JSON.stringify({manifest:{generatedAt:'2026-10-02'},texts:{a:'saved'}}),setItem(){throw Error('Quota exceeded')}};
 assert.equal((await vm.runInContext("forecastCache('get')",sandbox)).texts.a,'saved');
 await vm.runInContext("forecastCache('put', {texts:{a:'large'}})",sandbox);
 sandbox.indexedDB={open(){throw Error('Blocked device storage')}};sandbox.setTimeout=setTimeout;sandbox.clearTimeout=clearTimeout;
 assert.equal(await vm.runInContext("forecastCache('get')",sandbox),null);
 console.log('PASS model-cache fallback and blocked/quota-limited storage fail safely');
})().catch(e=>{console.error(e);process.exitCode=1});
