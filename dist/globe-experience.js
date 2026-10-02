'use strict';
// A globe-first shell; existing controls and data handlers retain their identities.
(function(){
 const panel=document.querySelector('.map-panel'),workspace=document.querySelector('.workspace');
 const gpuCanvas=document.createElement('canvas');gpuCanvas.id='planet';gpuCanvas.setAttribute('aria-hidden','true');panel.insertBefore(gpuCanvas,canvas);
 const rendererStatus=document.createElement('span');rendererStatus.id='rendererStatus';rendererStatus.textContent='GPU globe';panel.appendChild(rendererStatus);
 const fallback=()=>{gpuGlobe=null;gpuCanvas.hidden=true;rendererStatus.textContent='Compatibility globe';const note=document.getElementById('basemapAttributionText');if(note)note.textContent='Background coastline: Natural Earth. Forecast colors and contours are separate model data; their run and valid dates are shown above.';draw()};
 try{gpuGlobe=new AtlasGlobe(gpuCanvas,fallback);gpuGlobe.setSurface('earth-surface.jpg')}catch(error){console.warn("ENSO WebGL fallback:",error.message);rendererStatus.title=error.message;fallback()}
 const timeline=document.querySelector('.timeline');workspace.before(timeline);
 const daylight=document.querySelector('.sunpanel');const details=document.createElement('details');details.className='daylight-details';const summary=document.createElement('summary');summary.textContent='Sunlight · independent date & time';details.appendChild(summary);details.appendChild(daylight);timeline.after(details);
 const citybar=$('cityBar');timeline.before(citybar);
 const top=document.querySelector('.topline');top.querySelector('h1').textContent='Forecast operations';
 const baseNote=document.createElement('details');baseNote.className='basemap-note';baseNote.id='basemapAttribution';const baseSummary=document.createElement('summary');baseSummary.textContent='Background imagery · attribution';const baseText=document.createElement('p');baseText.id='basemapAttributionText';baseText.textContent=gpuGlobe?'Background imagery: NASA Blue Marble, October 2004 archival surface composite. It is not live satellite imagery. Forecast colors and contours are separate model data; their run and valid dates are shown above.':'Background coastline: Natural Earth. Forecast colors and contours are separate model data; their run and valid dates are shown above.';baseNote.append(baseSummary,baseText);panel.appendChild(baseNote);
 let travel=0;const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
 function flyTo(targetLon,targetLat,targetZoom=zoomScale){const token=++travel,startLon=lon,startLat=lat,startZoom=zoomScale,delta=((targetLon-startLon+540)%360)-180,start=performance.now();if(reduced()){lon=targetLon;lat=targetLat;setZoom(targetZoom);return}function frame(now){if(token!==travel)return;const t=Math.min(1,(now-start)/850),ease=t*t*(3-2*t);lon=startLon+delta*ease;lat=startLat+(targetLat-startLat)*ease;zoomScale=startZoom+(targetZoom-startZoom)*ease;resize();$('zoomLevel').textContent=Math.round(zoomScale*100)+'%';if(t<1)requestAnimationFrame(frame)}requestAnimationFrame(frame)}
 window.atlasFlyTo=flyTo;
 canvas.addEventListener('pointerdown',()=>{travel++});canvas.addEventListener('wheel',()=>{travel++},{passive:true});canvas.addEventListener('keydown',()=>{travel++});
 $('city').onchange=e=>{city=Number(e.target.value);render();flyTo(cities[city][2],Math.max(-75,Math.min(75,cities[city][1]-8)))};
 document.querySelectorAll('[data-focus]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-focus]').forEach(x=>x.classList.toggle('active',x===b));const f=b.dataset.focus;flyTo(f==='global'?-160:f==='ca'?-120:-108,f==='global'?10:f==='ca'?32:29,f==='ca'?1.5:1)});
 $('zoomReset').onclick=()=>{rotating=false;$('rotate').setAttribute('aria-pressed','false');$('rotate').textContent='◎ Rotate globe';flyTo(-108,29,1)};
 $('globalPointForm').onsubmit=e=>{e.preventDefault();const a=Number($('globalLat').value),b=Number($('globalLon').value);if(!Number.isFinite(a)||!Number.isFinite(b)||Math.abs(a)>90||Math.abs(b)>180)return;globalSelectedPoint=[a,b];renderGlobal();flyTo(b,Math.max(-75,Math.min(75,a-8)))};
 document.addEventListener('visibilitychange',()=>{if(document.hidden){travel++;rotating=false;sunPlaying=false;$('rotate').textContent='◎ Rotate globe';$('rotate').setAttribute('aria-pressed','false');$('playSun').textContent='Play';$('playSun').setAttribute('aria-pressed','false')}});
 // Coarse source grids retain sampled points; contours never imply new resolution.
 const originalDrawGlobal=drawGlobal;drawGlobal=function(){ctx.save();ctx.globalAlpha=mapStyle==='both'?.72:1;originalDrawGlobal();ctx.restore()};
 resize=function(){const b=canvas.getBoundingClientRect(),d=Math.min(1.5,devicePixelRatio||1);W=b.width;H=b.height;canvas.width=W*d;canvas.height=H*d;ctx.setTransform(d,0,0,d,0,0);R=Math.min(W*.43,H*.41)*zoomScale;CX=W*.5;CY=H*.51;draw()};
 resize();
})();
