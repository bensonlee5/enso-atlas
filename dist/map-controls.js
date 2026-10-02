'use strict';
/* Each control changes one named dimension: product, field, period, camera. */
(function(){
 const select=$('mapRegion');
 const regions={americas:[-80,5],europe:[15,45],africa:[20,0],asia:[100,30],oceania:[140,-25],pacific:[180,0],north:[0,75],south:[0,-75]};
 function focus(){const p=regions[select.value]||[globalSelectedPoint[1],Math.max(-75,Math.min(75,globalSelectedPoint[0]-8))];rotating=false;$('rotate').setAttribute('aria-pressed','false');$('rotate').textContent='◎ Rotate globe';if(window.atlasFlyTo)window.atlasFlyTo(p[0],p[1],1);else{lon=p[0];lat=p[1];setZoom(1)}}
 select.onchange=focus;
 const previousHorizon=setHorizon;setHorizon=function(value){const camera=[lon,lat,zoomScale];previousHorizon(value);window.atlasFlyTo?.(...camera)};
 for(const button of document.querySelectorAll('[data-horizon]'))button.onclick=()=>setHorizon(button.dataset.horizon);
 const previousSelect=window.AtlasWorkspace.select;window.AtlasWorkspace.select=function(record){select.value='selected';return previousSelect(record)};
 $('zoomReset').onclick=focus;
 canvas.addEventListener('pointerdown',()=>{select.value='selected'});
 const sync=syncExplorerState;syncExplorerState=function(){sync();const isGrid=globalMode||longMode;document.querySelector('.primary-fields').hidden=!isGrid;const title=globalMode?'Worldwide daily maps':longMode?(longData()?.data?.coverage==='global'?'Worldwide weekly maps':'Regional weekly maps'):'Local daily forecast';document.querySelector('.topline h1').textContent=title;document.querySelector('.variables').setAttribute('aria-label','Daily forecast variable');$('modelComparison').hidden=!globalMode||$('globalView').value==='climate'||$('globalView').value==='history';};
 const globalLatest=$('globalToday');globalLatest.onclick=()=>{const p=globalAssets[$('globalModel').value];if(!p)return;const start=p.days?.[0]?.date||p.run.slice(0,10),end=p.days?.at(-1)?.date||new Date(Date.parse(p.run)+360*3600000).toISOString().slice(0,10),today=new Date().toISOString().slice(0,10);$('globalDate').value=today<start?start:today>end?end:today;$('globalView').value='forecast';globalRequest++;globalLoading=false;renderGlobal()};
 $('forecastSettings').open=true;
 syncExplorerState();
})();
