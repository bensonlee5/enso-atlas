import assert from 'node:assert/strict';import {createWorker,handleHistory} from '../server/worker.mjs';
const worker=createWorker({'/index.html':{body:'test',type:'text/html',etag:'"test"'}});
assert.equal((await worker.fetch(new Request('https://test/'))).status,200);assert.equal((await worker.fetch(new Request('https://test/missing'))).status,404);assert.equal((await worker.fetch(new Request('https://test/',{method:'POST'}))).status,405);
for(const suffix of ['date=2030-01-01','date=2025-02-31','date=2025-99-99','url=https://untrusted.invalid','date=2025-01-01&date=2025-01-02','date=2025-01-01&url=bad'])assert.equal((await handleHistory(new Request('https://test/api/history?'+suffix))).status,400);
console.log('PASS worker public-asset routing, method restrictions and bounded historical inputs');
