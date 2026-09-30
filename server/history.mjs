/** Server-side only: NOAA PSL does not expose CORS headers. No auth or payment.
 * Bind only date argument in an existing server route; never accept arbitrary URLs.
 * Suggested route cache: immutable by date, timeout 30s, request deduplication.
 */
export function parseAscii(text, variable, date) {
 const parts=text.split(/^-{10,}\s*$/m);if(parts.length!==2)throw Error('Invalid NOAA ASCII response');
 const body=parts[1];
 const vector=name=>{const m=body.match(new RegExp('^'+name.replaceAll('.','\\.')+'\\[\\d+\\]\\s*\\n([^\\n]+)','m'));if(!m)throw Error('Missing '+name);return m[1].split(',').map(Number)};
 const lat=vector('lat'),lon=vector('lon');
 const rows=[...body.matchAll(/^\[0\]\[(\d+)\],\s*(.*)$/gm)].map(m=>({index:Number(m[1]),values:m[2].split(',').map(Number)}));
 if(rows.length!==lat.length||rows.some((r,i)=>r.index!==i||r.values.length!==lon.length))throw Error('Invalid field shape');
 const time=vector(variable+'.time')[0];const actual=new Date(Date.UTC(1800,0,1)+time*3600000).toISOString().slice(0,10);if(actual!==date)throw Error('NOAA returned another date');
 const raw=rows.flatMap(r=>r.values);return {gridCoordinates:lat.flatMap(a=>lon.map(b=>[a,((b+180)%360)-180])),values:raw.map(v=>v < -1e20?null:Math.round((variable==='air'?v-273.15:v*86400)*100)/100)};
}
export async function getHistory(date,fetcher=fetch) {
 if(!/^\d{4}-\d{2}-\d{2}$/.test(date))throw Error('Use YYYY-MM-DD');
 const d=new Date(date+'T00:00:00Z');if(!Number.isFinite(+d)||d.toISOString().slice(0,10)!==date||date<'1948-01-01'||date>'2026-03-17')throw Error('Supported dates: 1948-01-01 through 2026-03-17');
 const year=d.getUTCFullYear(),day=Math.round((+d-Date.UTC(year,0,1))/86400000);
 const sources=[];
 const fields=await Promise.all([['air','air.2m.gauss'],['prate','prate.sfc.gauss']].map(async([v,p])=>{
  const url=`https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis/Dailies/surface_gauss/${p}.${year}.nc.ascii?${v}[${day}:1:${day}][0:2:93][0:2:191],lat[0:2:93],lon[0:2:191]`;
  sources.push(url);const r=await fetcher(url,{signal:AbortSignal.timeout(30000)});if(!r.ok)throw Error('NOAA upstream '+r.status);return parseAscii(await r.text(),v,date);
 }));
 if(JSON.stringify(fields[0].gridCoordinates)!==JSON.stringify(fields[1].gridCoordinates))throw Error('Grid mismatch');
 return {dataset:'NOAA NCEP/NCAR Reanalysis 1',kind:'historical daily weather reconstruction, not an archived issued forecast',date,coverageStart:'1948-01-01',coverageEnd:'2026-03-17',gridCoordinates:fields[0].gridCoordinates,temperatureC:fields[0].values,precipitationMmDay:fields[1].values,sources,attribution:'NCEP-NCAR Reanalysis 1 data provided by NOAA PSL, Boulder, Colorado, USA'};
}
