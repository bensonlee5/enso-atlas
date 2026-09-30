/* Approximate NOAA solar position for visual day/night shading.
   https://gml.noaa.gov/grad/solcalc/solareqns.PDF */
'use strict';
const Solar={
 parts(instant,zone){const p=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(instant).map(p=>[p.type,p.value]));return {date:`${p.year}-${p.month}-${p.day}`,time:`${p.hour}:${p.minute}`}},
 fromWall(date,time,zone){if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!/^\d{2}:\d{2}$/.test(time))return [];const base=Date.parse(date+'T'+time+':00Z');if(!Number.isFinite(base))return [];const offsets=new Set();for(const d of [-2,0,2]){const instant=base+d*86400000,p=this.parts(instant,zone);offsets.add(Date.parse(p.date+'T'+p.time+':00Z')-instant)}return [...offsets].map(o=>base-o).filter(t=>{const p=this.parts(t,zone);return p.date===date&&p.time===time}).sort((a,b)=>a-b)},
 position(date){const year=date.getUTCFullYear(),days=(Date.UTC(year+1,0,1)-Date.UTC(year,0,1))/86400000,doy=Math.floor((date-Date.UTC(year,0,1))/86400000)+1,hour=date.getUTCHours()+date.getUTCMinutes()/60+date.getUTCSeconds()/3600,g=2*Math.PI/days*(doy-1+(hour-12)/24),eq=229.18*(.000075+.001868*Math.cos(g)-.032077*Math.sin(g)-.014615*Math.cos(2*g)-.040849*Math.sin(2*g)),dec=.006918-.399912*Math.cos(g)+.070257*Math.sin(g)-.006758*Math.cos(2*g)+.000907*Math.sin(2*g)-.002697*Math.cos(3*g)+.00148*Math.sin(3*g);return {declination:dec*180/Math.PI,longitude:((180-15*hour-eq/4+540)%360)-180}}
};
if(typeof module!=='undefined')module.exports=Solar;
