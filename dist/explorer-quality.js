'use strict';
// One presentation layer, shared by direct controls, asynchronous data and WebMCP.
function syncExplorerState(){
 $('cityBar').hidden=globalMode||longMode;$('cityHeading').textContent=cities[city][0];
 document.querySelector('.colorbar').style.visibility=globalMode&&!globalField?'hidden':'visible';
 const banner=$('modeBanner');let label,detail,kind='forecast';
 if(globalMode){const d=globalField;kind=d?.kind==='CLIMATE AVERAGE'?'climate':d?.kind==='HISTORICAL REANALYSIS'?'history':d?'forecast':'unavailable';label=d?.heading||'No weather field';detail=d?d.valid:$('globalStatus').textContent;$('mapReading').textContent=d?$('globalPrimary').textContent+' '+d.unit+' · selected grid point':'No values substituted';}
 else if(longMode){const d=longData();label=!d?'Loading CFSv2 guidance':d?.ensemble?'CFSv2 · four-member outlook':d?.raw?'CFSv2 · one model member':'CFSv2 · ensemble-mean anomaly';detail=$('longDate').textContent;$('mapReading').textContent=cfs?.sampledLocations[longCity]?.name+' · '+$('longPrimary').textContent+' '+$('longUnit').textContent;}
 else{label='GFS · local daily forecast';detail=$('selectedDate').textContent;$('mapReading').textContent=cities[city][0]+' · '+$('primary').textContent+' '+$('primaryUnit').textContent;document.querySelector('.hourcontrol').hidden=variable!=='cloud_cover';}
 banner.dataset.kind=kind;banner.replaceChildren();const strong=document.createElement('strong'),span=document.createElement('span');strong.textContent=label;span.textContent=detail;banner.append(strong,span);
 for(const attr of ['data-horizon','data-var','data-focus','data-view'])document.querySelectorAll('['+attr+']').forEach(b=>b.setAttribute('aria-pressed',String(b.classList.contains('active'))));
 const run=globalMode?globalField?.data?.run:longMode?longData()?.data?.run:null;const old=run&&Date.now()-Date.parse(run)>4*86400000;banner.classList.toggle('dated',!!old);if(old){const warning=document.createElement('span');warning.className='freshnesswarning';warning.textContent='Dated run · '+run.slice(0,10)+' · check source before use';banner.appendChild(warning)}
 $('refresh').textContent=globalMode||longMode?'↻ Update sources':'↻ Refresh GFS';$('refresh').title=globalMode||longMode?'Recheck the daily public data feed':'Refresh GFS point forecasts';
 if((globalMode||longMode)&&$('feedStatus').textContent.includes('unavailable')){const warning=document.createElement('span');warning.className='freshnesswarning';warning.textContent='Source update unavailable · retaining the displayed, dated data';banner.appendChild(warning)}
 if(!globalMode&&!longMode&&$('fetchStatus').textContent.includes('unavailable')){const warning=document.createElement('span');warning.className='freshnesswarning';warning.textContent='Live update unavailable · saved forecast shown';banner.appendChild(warning)}
 if(typeof navigator!=='undefined'&&navigator.onLine===false){const warning=document.createElement('span');warning.className='freshnesswarning';warning.textContent='Offline · already-loaded data only';banner.appendChild(warning)}
 if(typeof renderComparison==='function')renderComparison();
}
for(const name of ['render','renderLong','renderGlobal']){const original=window[name];window[name]=function(...args){const result=original(...args);syncExplorerState();return result}}
$('refresh').onclick=()=>{if(globalMode||longMode){$('refresh').disabled=true;refreshPublicData(true).finally(()=>{$('refresh').disabled=false;syncExplorerState()})}else refresh().finally(syncExplorerState)};
$('touchGlobe').onclick=()=>{touchExplore=!touchExplore;canvas.style.touchAction=touchExplore?'none':'pan-y';$('touchGlobe').setAttribute('aria-pressed',String(touchExplore));$('touchGlobe').textContent=touchExplore?'Done exploring':'Explore globe';canvas.classList.toggle('touch-active',touchExplore)};
canvas.addEventListener('keydown',e=>{const keys=['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-','0'];if(!keys.includes(e.key))return;e.preventDefault();if(e.key==='0'){$('zoomReset').click();return}if(['+','=','-'].includes(e.key)){setZoom(zoomScale*(e.key==='-'?1/1.2:1.2));return}lon+=e.key==='ArrowLeft'?-5:e.key==='ArrowRight'?5:0;lat=Math.max(-75,Math.min(75,lat+(e.key==='ArrowUp'?5:e.key==='ArrowDown'?-5:0)));draw()});
$('globalToday').onclick=()=>{$('globalDate').value=new Date().toISOString().slice(0,10);$('globalView').value='auto';globalRequest++;globalLoading=false;renderGlobal()};
addEventListener('offline',()=>{const b=$('modeBanner');const p=document.createElement('span');p.className='freshnesswarning';p.textContent='Offline · showing already-loaded data and its source dates';b.appendChild(p)});
syncExplorerState();
function renderComparison(){
 const area=$('comparisonValues'),note=$('comparisonNote');area.replaceChildren();if(!globalMode||!globalField){note.textContent='No matching forecast comparison is available in this view.';return}
 if(globalField.kind==='CLIMATE AVERAGE'||globalField.kind==='HISTORICAL REANALYSIS'){note.textContent='This view is not a current forecast comparison. Select an in-range forecast date to compare two model snapshots.';return}
 if($('globalVariable').value!=='temperatureC'){note.textContent='Rainfall comparison is withheld. CFS exposes sampled instantaneous rates; AIFS exposes accumulation since initialization. Their numbers are not interchangeable.';return}
 const cf=globalAssets.cfs,ai=globalAssets.aifs;if(!cf||!ai)return;const target=Date.parse($('globalDate').value+'T12:00:00Z'),frames=ai.frames.filter(f=>f.metadata.shortName==='2t');const a=frames.reduce((best,f)=>Math.abs(Date.parse(ai.run)+aifsLead(f)*3600000-target)<Math.abs(Date.parse(ai.run)+aifsLead(best)*3600000-target)?f:best),valid=Date.parse(ai.run)+aifsLead(a)*3600000;
 const c=cf.comparisonSnapshots?.find(f=>Date.parse(f.validTime)===valid);if(!c){note.textContent='No matching CFS instantaneous sample is available in this data bundle. The daily CFS mean is not substituted for an instantaneous value.';return}
 const ci=globalNearest(cf.gridCoordinates,globalSelectedPoint),aii=globalNearest(ai.gridCoordinates,globalSelectedPoint),cv=c.temperatureC[ci],av=a.values[aii];if(!Number.isFinite(cv)||!Number.isFinite(av)){note.textContent='Matching model values are unavailable at this sampled point.';return}
 note.textContent='Nearest shared snapshot · same valid instant: '+new Date(valid).toISOString().slice(0,16).replace('T',' ')+' UTC. Both are instantaneous 2 m temperatures; the map keeps its selected statistic.';
 const dl=document.createElement('dl');for(const [name,value] of [['CFSv2 · member 01',fmt(convertTemp(cv))+' '+tempUnit()],['ECMWF AIFS',fmt(convertTemp(av))+' '+tempUnit()],['AIFS minus CFS',(av-cv>=0?'+':'')+fmt(convertTemp(av-cv,true))+' '+tempUnit()]]){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=name;dd.textContent=value;dl.append(dt,dd)}area.appendChild(dl);
 const small=document.createElement('small');small.textContent='CFS initialized '+cf.run.slice(0,16)+' at grid '+cf.gridCoordinates[ci].map(x=>x.toFixed(2)).join(', ')+'; AIFS initialized '+ai.run.slice(0,16)+' at grid '+ai.gridCoordinates[aii].map(x=>x.toFixed(2)).join(', ')+'. Different grids and initialization times remain. This difference is model disagreement, not a confidence interval or an accuracy score.';area.appendChild(small);
}

const selectForecastHorizon=setHorizon;setHorizon=function(value){selectForecastHorizon(value);if(typeof matchMedia==='function'&&matchMedia('(max-width:760px)').matches)$('forecastSettings').open=true};
if(typeof matchMedia==='function'&&matchMedia('(max-width:760px)').matches)$('forecastSettings').open=false;

for(const button of document.querySelectorAll('[data-view],[data-focus]'))button.addEventListener('click',syncExplorerState);
