'use strict';
// A globe-first shell; existing controls and data handlers retain their identities.
(function(){
 const panel=document.querySelector('.map-panel'),workspace=document.querySelector('.workspace');
 const gpuCanvas=document.createElement('canvas');gpuCanvas.id='planet';gpuCanvas.setAttribute('aria-hidden','true');panel.insertBefore(gpuCanvas,canvas);
 const rendererStatus=document.createElement('span');rendererStatus.id='rendererStatus';rendererStatus.textContent='GPU globe';panel.appendChild(rendererStatus);
 const fallback=()=>{gpuGlobe=null;gpuCanvas.hidden=true;rendererStatus.textContent='Compatibility globe';draw()};
 try{gpuGlobe=new AtlasGlobe(gpuCanvas,fallback);gpuGlobe.setSurface('earth-surface.jpg')}catch(error){console.warn("ENSO WebGL fallback:",error.message);rendererStatus.title=error.message;fallback()}
 const timeline=document.querySelector('.timeline');workspace.after(timeline);
 const daylight=document.querySelector('.sunpanel');const details=document.createElement('details');details.className='daylight-details';const summary=document.createElement('summary');summary.textContent='Sunlight · independent date & time';details.appendChild(summary);details.appendChild(daylight);timeline.after(details);
 const citybar=$('cityBar');panel.appendChild(citybar);
 const top=document.querySelector('.topline');top.querySelector('h1').textContent='Explore Earth';
 const readingButton=document.createElement('button');readingButton.id='toggleReading';readingButton.textContent='Location details';readingButton.setAttribute('aria-expanded','false');panel.appendChild(readingButton);
 readingButton.onclick=()=>{const open=workspace.classList.toggle('reading-open');readingButton.setAttribute('aria-expanded',String(open));readingButton.textContent=open?'Close details':'Location details'};
 const baseNote=document.createElement('span');baseNote.className='basemap-note';baseNote.textContent=gpuGlobe?'NASA surface · Oct 2004 · not live imagery':'Natural Earth coastline · compatibility view';panel.appendChild(baseNote);
 let travel=0;const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
 function flyTo(targetLon,targetLat,targetZoom=zoomScale){const token=++travel,startLon=lon,startLat=lat,startZoom=zoomScale,delta=((targetLon-startLon+540)%360)-180,start=performance.now();if(reduced()){lon=targetLon;lat=targetLat;setZoom(targetZoom);return}function frame(now){if(token!==travel)return;const t=Math.min(1,(now-start)/850),ease=t*t*(3-2*t);lon=startLon+delta*ease;lat=startLat+(targetLat-startLat)*ease;zoomScale=startZoom+(targetZoom-startZoom)*ease;resize();$('zoomLevel').textContent=Math.round(zoomScale*100)+'%';if(t<1)requestAnimationFrame(frame)}requestAnimationFrame(frame)}
 canvas.addEventListener('pointerdown',()=>{travel++});canvas.addEventListener('wheel',()=>{travel++},{passive:true});canvas.addEventListener('keydown',()=>{travel++});
 $('city').onchange=e=>{city=Number(e.target.value);render();flyTo(cities[city][2],Math.max(-75,Math.min(75,cities[city][1]-8)))};
 document.querySelectorAll('[data-focus]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-focus]').forEach(x=>x.classList.toggle('active',x===b));const f=b.dataset.focus;flyTo(f==='global'?-160:f==='ca'?-120:-108,f==='global'?10:f==='ca'?32:29,f==='ca'?1.5:1)});
 $('zoomReset').onclick=()=>{rotating=false;$('rotate').setAttribute('aria-pressed','false');$('rotate').textContent='◎ Rotate globe';flyTo(-108,29,1)};
 $('globalPointForm').onsubmit=e=>{e.preventDefault();const a=Number($('globalLat').value),b=Number($('globalLon').value);if(!Number.isFinite(a)||!Number.isFinite(b)||Math.abs(a)>90||Math.abs(b)>180)return;globalSelectedPoint=[a,b];renderGlobal();flyTo(b,Math.max(-75,Math.min(75,a-8)))};
 document.addEventListener('visibilitychange',()=>{if(document.hidden){travel++;rotating=false;sunPlaying=false;$('rotate').textContent='◎ Rotate globe';$('rotate').setAttribute('aria-pressed','false');$('playSun').textContent='Play';$('playSun').setAttribute('aria-pressed','false')}});
 // Coarse source grids retain sampled points; contours never imply new resolution.
 const originalDrawGlobal=drawGlobal;drawGlobal=function(){ctx.save();ctx.globalAlpha=mapStyle==='both'?.72:1;originalDrawGlobal();ctx.restore()};
 resize();
})();
