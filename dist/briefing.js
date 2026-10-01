'use strict';
/* Pure presentation data. Missing source values are never coerced to zero. */
(function(root){
 const finite=value=>Number.isFinite(value)?value:null;
 function days(forecast,units=false){
  const d=forecast?.daily;if(!Array.isArray(d?.time))return [];
  const temperature=v=>Number.isFinite(v)?(units?v*1.8+32:v):null;
  return d.time.map((validDate,index)=>({index,validDate,high:temperature(d.temperature_2m_max?.[index]),low:temperature(d.temperature_2m_min?.[index]),precipitation:finite(d.precipitation_sum?.[index]),wind:finite(d.wind_speed_10m_max?.[index])}));
 }
 function nearestTime(times,instant){let index=-1,distance=Infinity;times.forEach((time,i)=>{const difference=Math.abs(Date.parse(time.endsWith('Z')?time:time+'Z')-instant);if(difference<distance){distance=difference;index=i}});return index;}
 function freshness(time,now=Date.now()){const elapsed=now-Date.parse(time);if(!Number.isFinite(elapsed))return 'Time unavailable';if(elapsed<0)return 'Future source timestamp';const hours=Math.floor(elapsed/3600000);return hours<1?'less than 1 hour old':hours<48?hours+' hours old':Math.floor(hours/24)+' days old';}
 function utc(time){const value=new Date(time);return Number.isFinite(value.getTime())?value.toISOString().slice(0,16).replace('T',' ')+' UTC':'Not provided';}
 root.AtlasBriefing={days,nearestTime,freshness,utc};
 if(typeof module!=='undefined')module.exports=root.AtlasBriefing;
})(typeof globalThis==='undefined'?this:globalThis);
