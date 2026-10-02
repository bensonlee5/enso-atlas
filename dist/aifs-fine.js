'use strict';
(function(root){
 const decoded=new WeakMap();
 async function inflateFrame(frame,fine){
  const packed=Uint8Array.from(atob(frame.valuesPacked),c=>c.charCodeAt(0));
  if(packed.length>180000)throw Error('Oversized packed weather frame');
  const reader=new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip')).getReader(),chunks=[];let size=0;
  try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>130320){await reader.cancel();throw Error('Oversized decoded weather frame')}chunks.push(value)}}finally{reader.releaseLock()}
  if(size!==130320)throw Error('Wrong weather grid size');
  const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length}const view=new DataView(bytes.buffer),values=new Array(65160);let missing=0;
  for(let i=0;i<values.length;i++){const raw=view.getInt16(i*2,true);values[i]=raw===fine.missingValue?null:raw*fine.scale;if(values[i]===null)missing++;}
  if(missing!==frame.missingCells)throw Error('Weather missingness mismatch');return values;
 }
 async function prepare(product){if(!product?.fineFirstWeek)return product;if(decoded.has(product))return decoded.get(product);
  const pending=(async()=>{if(root.AtlasForecastSchema)root.AtlasForecastSchema.validateAifsFineMetadata(product);const f=product.fineFirstWeek,coords=[];if(f.schemaVersion!==1||f.grid?.rows!==181||f.grid.columns!==360||f.encoding!=='gzip-base64-int16-le'||f.scale!==.1||f.missingValue!==-32768||f.temperature?.length!==29||f.precipitation?.length!==28)throw Error('Invalid first-week fields');
   for(let y=90;y>=-90;y--)for(let x=-180;x<180;x++)coords.push([y,x]);
   const temperature=[],precipitation=[];for(const frame of f.temperature){const values=await inflateFrame(frame,f);if(values.some(v=>v!==null&&(v< -120||v>70)))throw Error('Invalid temperature range');temperature.push({...frame,values})}for(const frame of f.precipitation){const values=await inflateFrame(frame,f);if(values.some(v=>v!==null&&v<0))throw Error('Negative interval rainfall');precipitation.push({...frame,values})}
   Object.defineProperty(product,'fineDecoded',{value:{coords,temperature,precipitation},enumerable:false});return product;
  })();decoded.set(product,pending);return pending;
 }
 root.AtlasAifsFine={prepare,inflateFrame};if(typeof module!=='undefined')module.exports=root.AtlasAifsFine;
})(typeof globalThis!=='undefined'?globalThis:this);
