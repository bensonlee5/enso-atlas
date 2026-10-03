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
 $('forecastFineWeek').click();$('forecastRestart').click();assert.equal(t.eval('globalField.fine'),true);
 t.eval('drawContinuousField(globalField)');const beforeRaster=Buffer.from(raster),beforeValues=t.eval('globalField.values.slice()');
 $('forecastPlay').click();step(1);step(1600);const s=w.AtlasPlayback.state;
 assert.equal(w.AtlasPlayback.playing,true);assert.equal(s.descriptor.frames.length,29);assert(Math.abs((s.time-s.descriptor.frames[0].time)/(s.descriptor.frames.at(-1).time-s.descriptor.frames[0].time)-1600/48000)<1e-9);
 assert(t.eval('globalField.values').some((v,i)=>v!==beforeValues[i]));t.eval('drawContinuousField(globalField)');assert(!beforeRaster.equals(raster),'Actual dense AIFS colors must change during Play');
 $('forecastPlay').click();const paused=w.AtlasPlayback.state.time;step(8000);assert.equal(w.AtlasPlayback.state.time,paused);
 $('forecastPlay').click();step(1);Object.defineProperty(w.document,'hidden',{configurable:true,value:true});w.document.dispatchEvent(new w.Event('visibilitychange'));step(60000);assert.equal(w.AtlasPlayback.playing,false);assert.equal(w.AtlasPlayback.state.time,paused);
 Object.defineProperty(w.document,'hidden',{configurable:true,value:false});$('forecastPlay').click();step(1);step(48000);assert.equal(w.AtlasPlayback.playing,false);assert.equal(w.AtlasPlayback.state.i,28);assert.equal(queue.size,0);assert.deepEqual(t.errors,[]);t.dom.window.close();
 console.log('PASS regressions: late source preserves explicit selection; dense AIFS Play changes scalar/raster; delayed frames retain wall time; pause/hidden/resume/end remain bounded');
})().catch(e=>{console.error(e.stack);process.exit(1)});
