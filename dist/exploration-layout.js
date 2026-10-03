'use strict';
/* Compact working surface. Scientific state remains owned by the forecast modules. */
(function(){
 const picker=document.querySelector('.location-picker'),selected=picker.querySelector('.selected-location');
 const editor=document.createElement('details');editor.id='locationEditor';editor.className='location-editor';
 const summary=document.createElement('summary');summary.textContent='Search or manage location';editor.append(summary);
 for(const node of [...picker.children])if(node!==selected)editor.append(node);
 picker.replaceChildren(selected,editor);
 selected.querySelector('.location-kicker').textContent='LOCATION';
 $('locationChange').setAttribute('aria-controls','locationEditor');
 $('locationChange').onclick=()=>{editor.open=!editor.open;$('locationChange').setAttribute('aria-expanded',String(editor.open));if(editor.open){$('locationQuery').value='';$('locationQuery').focus()}};
 editor.addEventListener('toggle',()=>{if(typeof document==='undefined'||!document)return;$('locationChange').setAttribute('aria-expanded',String(editor.open))});
 $('locationChange').setAttribute('aria-expanded','false');
 editor.addEventListener('keydown',e=>{if(e.key==='Escape'){editor.open=false;$('locationChange').focus()}});
 $('locationResults').addEventListener('click',e=>{if(e.target.closest('.location-result'))editor.open=false});
 const clear=$('locationClear');editor.append(clear);clear.addEventListener('click',()=>{editor.open=true;$('locationQuery').focus()});
 const privacy=$('locationPrivacy'),privacyDetails=document.createElement('details');privacyDetails.className='location-privacy-details';privacyDetails.innerHTML='<summary>Location privacy</summary>';privacy.before(privacyDetails);privacyDetails.append(privacy);
 const settings=$('forecastSettings');settings.open=false;
 settings.querySelector('summary').textContent='Model, period & options';
 const workspace=document.querySelector('.workspace'),map=document.querySelector('.map-panel'),playback=$('forecastPlayback');
 map.after(playback);
 const fineShortcut=document.createElement('button');fineShortcut.id='forecastFineWeek';fineShortcut.type='button';fineShortcut.textContent='First week · 6-hour maps';playback.querySelector('.playback-scenarios').prepend(fineShortcut);
 fineShortcut.onclick=()=>{AtlasPlayback.stop();$('globalModel').value='aifs';$('globalView').value='forecast';setHorizon('global');$('globalToday').click();};
 const playbackOptions=document.createElement('details');playbackOptions.className='playback-options';playbackOptions.innerHTML='<summary>Playback options</summary><div class="playback-options-content"></div>';
 const top=playback.querySelector('.playback-top'),optionsBody=playbackOptions.lastElementChild;
 for(const label of [...top.querySelectorAll('label')])if(!label.querySelector('#forecastPlaybackAxis,#forecastPlaybackSpeed'))optionsBody.append(label);
 top.append(playbackOptions);
 const method=playback.querySelector('details:not(.playback-options)');method.prepend($('forecastPlaybackNote'));
 for(const [id,label] of [['globalPointForm','Coordinates & map point'],['modelComparison','Compare model snapshots']]){const element=$(id),details=document.createElement('details');details.className='secondary-forecast-detail';const summary=document.createElement('summary');summary.textContent=label;details.append(summary);element.before(details);details.append(element);}
 const sourceDetails=document.createElement('details');sourceDetails.className='source-context-details';sourceDetails.innerHTML='<summary>Source, freshness & interpretation</summary>';workspace.after(sourceDetails);sourceDetails.append($('operatingStrip'));
 // Essential failures remain visible even when source detail is collapsed.
 const attention=document.createElement('p');attention.id='forecastAttention';attention.setAttribute('role','status');attention.hidden=true;document.querySelector('.timeline').after(attention);
 const updateAttention=()=>{if(typeof document==='undefined'||!document)return;fineShortcut.disabled=!globalAssets.aifs?.fineDecoded;fineShortcut.hidden=!!(globalMode&&globalField?.fine);const notes=[...$('operatingStrip').querySelectorAll('.attention')].map(n=>[...n.children].map(x=>x.textContent).join(': '));attention.hidden=!notes.length;attention.textContent=notes.join(' · ')};
 new MutationObserver(updateAttention).observe($('operatingStrip'),{childList:true,subtree:true,characterData:true});updateAttention();
 // Never place a previous location's numeric column beside a new city's inputs.
 const airContext=$('airSharedContext'),airGrid=document.querySelector('.airgrid'),airLoad=document.createElement('button');airLoad.type='button';airLoad.id='loadSelectedAir';airLoad.textContent='Load this city';airContext.after(airLoad);
 airLoad.onclick=()=>{const loc=AtlasWorkspace.location();$('airLat').value=loc[1];$('airLon').value=loc[2];$('airForm').requestSubmit();};
 $('airForm').addEventListener('submit',()=>{const a=Number($('airLat').value),b=Number($('airLon').value),loc=AtlasWorkspace.location();if($('airLat').value.trim()&&$('airLon').value.trim()&&Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a)<=90&&Math.abs(b)<=180&&(Math.abs(a-loc[1])>.0001||Math.abs(b-loc[2])>.0001))AtlasLocationSearch.coordinates([a,b]);},true);
 function updateAirState(){if(typeof document==='undefined'||!document)return;const loc=AtlasWorkspace.location(),same=!!airData&&Math.abs(loc[1]-airRequestedCoordinate[0])<.01&&Math.abs(loc[2]-airRequestedCoordinate[1])<.01;airGrid.hidden=!same;airLoad.hidden=same;$('airTime').disabled=!same;$('airAltitude').disabled=!same;$('airStatus').hidden=!same&&/Dated source snapshot|Source refreshed/.test($('airStatus').textContent);airLoad.disabled=$('loadAir').disabled;if(!same){const message='Atmospheric column not loaded for '+loc[0]+'. Load this city to view its temperature, humidity and wind profile.';if(airContext.textContent!==message)airContext.textContent=message;$('airOperatingStrip').hidden=true}else $('airOperatingStrip').hidden=false;}
 const originalSync=syncExplorerState;syncExplorerState=function(){originalSync();updateAirState()};
 const originalAir=renderAir;renderAir=function(){originalAir();updateAirState()};
 new MutationObserver(updateAirState).observe($('loadAir'),{attributes:true,attributeFilter:['disabled']});
 for(const name of ['update','select','reset']){const original=AtlasWorkspace[name];AtlasWorkspace[name]=function(...args){const result=original(...args);updateAirState();return result}}
 new MutationObserver(updateAirState).observe(airContext,{childList:true});
 updateAirState();
})();
