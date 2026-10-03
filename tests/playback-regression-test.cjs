'use strict';
// Application integration and actual field/raster changes, not hardware/browser coverage.
const assert=require('node:assert/strict'),{boot,sleep}=require('./location-search-test.cjs');
(async()=>{
 for(const product of ['anomaly','raw']){
  let release;const gate=new Promise(r=>release=r),t=await boot({},false,{deferFile:'data/ensemble-percentiles.json',deferUntil:gate});
  t.w.document.querySelector('[data-horizon="long"]').click();t.$('longProduct').value=product;t.$('longProduct').dispatchEvent(new t.w.Event('change',{bubbles:true}));
  release();await t.eval('ensembleLoad');await sleep(5);
  assert.equal(t.eval('longProduct'),product,'Late ensemble arrival must not replace explicit selection');assert.equal(t.$('longProduct').value,product);assert(t.$('longProduct').querySelector('[value="ensemble"]'));assert.deepEqual(t.errors,[]);t.dom.window.close();
 }
 const t=await boot({},false,{reducedMotion:false}),{$,w}=t;let queue=new Map(),serial=0,now=0,raster=null;
 w.requestAnimationFrame=fn=>{queue.set(++serial,fn);return serial};w.cancelAnimationFrame=id=>queue.delete(id);
 t.eval('draw=function(){};window.atlasFlyTo=function(){};lon=-108;lat=29;R=200;ctx.drawImage=function(){}');
 w.HTMLCanvasElement.prototype.getContext=function(){return {createImageData:(a,b)=>({data:new Uint8ClampedArray(a*b*4)}),putImageData:image=>{raster=Buffer.from(image.data)},drawImage(){}}};
 const step=ms=>{now+=ms;const callbacks=[...queue.values()];queue.clear();for(const fn of callbacks)fn(now)};
 assert.equal($('forecastPlaybackSpeed').value,'1');assert.equal($('forecastPlaybackSpeed').closest('details'),null,'Pass duration remains visible beside Play');assert.deepEqual([...$('forecastPlaybackSpeed').options].map(o=>o.textContent),['6 seconds','12 seconds','24 seconds','48 seconds']);
 $('forecastFineWeek').click();$('forecastRestart').click();assert.equal(t.eval('globalField.fine'),true);
 t.eval('drawContinuousField(globalField)');const beforeRaster=Buffer.from(raster),beforeValues=t.eval('globalField.values.slice()');
 $('forecastPlay').click();step(1);step(1600);const s=w.AtlasPlayback.state;
 assert.equal(w.AtlasPlayback.playing,true);assert.equal(s.descriptor.frames.length,29);assert(Math.abs((s.time-s.descriptor.frames[0].time)/(s.descriptor.frames.at(-1).time-s.descriptor.frames[0].time)-1600/12000)<1e-9);
 assert(t.eval('globalField.values').some((v,i)=>v!==beforeValues[i]));t.eval('drawContinuousField(globalField)');assert(!beforeRaster.equals(raster),'Actual dense AIFS colors must change during Play');
 $('forecastPlay').click();const paused=w.AtlasPlayback.state.time;step(8000);assert.equal(w.AtlasPlayback.state.time,paused);
 $('forecastPlay').click();step(1);Object.defineProperty(w.document,'hidden',{configurable:true,value:true});w.document.dispatchEvent(new w.Event('visibilitychange'));step(60000);assert.equal(w.AtlasPlayback.playing,false);assert.equal(w.AtlasPlayback.state.time,paused);
 Object.defineProperty(w.document,'hidden',{configurable:true,value:false});$('forecastPlay').click();step(1);step(12000);assert.equal(w.AtlasPlayback.playing,false);assert.equal(w.AtlasPlayback.state.i,28);assert.equal(queue.size,0);
 // Every duration reaches the same final exact field, including rainfall intervals.
 const change=(id,v)=>{$(id).value=String(v);$(id).dispatchEvent(new w.Event('change',{bubbles:true}));};
 for(const [speed,milliseconds] of [[2,6000],[1,12000],[.5,24000],[.25,48000]]){
  change('forecastPlaybackSpeed',speed);$('forecastRestart').click();$('forecastPlay').click();step(1);step(milliseconds/2);assert.equal(w.AtlasPlayback.playing,true);assert(Math.abs((w.AtlasPlayback.state.time-w.AtlasPlayback.state.descriptor.frames[0].time)/(w.AtlasPlayback.state.descriptor.frames.at(-1).time-w.AtlasPlayback.state.descriptor.frames[0].time)-.5)<1e-9);step(milliseconds/2);assert.equal(w.AtlasPlayback.state.i,28);assert.equal(w.AtlasPlayback.playing,false);
 }
 $('fieldPrecipitation').click();change('forecastPlaybackSpeed',2);$('forecastRestart').click();$('forecastPlay').click();step(1);step(3000);assert.equal(w.AtlasPlayback.state.alpha,0);assert.equal(t.eval('globalField.intervalTotal'),true);step(3000);assert.equal(w.AtlasPlayback.state.i,27);assert.equal(w.AtlasPlayback.playing,false);
 $('forecastOpenEnsemble').click();change('forecastPlaybackAxis','percentile');$('forecastRestart').click();const seen=new Set([t.eval('percentile')]);$('forecastPlay').click();step(1);for(let i=0;i<24;i++){step(250);seen.add(t.eval('percentile'))}assert.deepEqual([...seen],['p1','p5','p10','p50','p90','p95','p99']);assert.equal(w.AtlasPlayback.playing,false);assert.equal(queue.size,0);assert.deepEqual(t.errors,[]);t.dom.window.close();
 console.log('PASS regressions: late source preserves explicit selection; dense AIFS Play changes scalar/raster; delayed frames retain wall time; pause/hidden/resume/end remain bounded');
})().catch(e=>{console.error(e.stack);process.exit(1)});
