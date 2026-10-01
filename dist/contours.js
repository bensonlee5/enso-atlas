/* Marching squares on genuine rectilinear model samples. No city-point fitting. */
(function(root){
function contourSegments(coords,values,levels){
 const ys=[...new Set(coords.map(c=>c[0]))].sort((a,b)=>a-b),xs=[...new Set(coords.map(c=>c[1]))].sort((a,b)=>a-b);
 if(xs.length<2||ys.length<2)return [];
 const xi=new Map(xs.map((x,i)=>[x,i])),yi=new Map(ys.map((y,i)=>[y,i])),grid=Array.from({length:ys.length},()=>Array(xs.length).fill(null));
 coords.forEach((c,i)=>{if(Number.isFinite(values[i]))grid[yi.get(c[0])][xi.get(c[1])]=values[i]});
 const medianGap=a=>{const g=a.slice(1).map((v,i)=>v-a[i]).sort((x,y)=>x-y);return g[Math.floor(g.length/2)]},maxX=medianGap(xs)*1.8,maxY=medianGap(ys)*1.8,out=[];
 const edges=[[0,1],[1,2],[2,3],[3,0]],cases={1:[[3,0]],2:[[0,1]],3:[[3,1]],4:[[1,2]],6:[[0,2]],7:[[3,2]],8:[[2,3]],9:[[2,0]],11:[[1,2]],12:[[1,3]],13:[[0,1]],14:[[3,0]]};
 for(const level of levels){if(!Number.isFinite(level))continue;for(let j=0;j<ys.length-1;j++)for(let i=0;i<xs.length-1;i++){
  if(xs[i+1]-xs[i]>maxX||ys[j+1]-ys[j]>maxY)continue;
  const v=[grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]];
  if(v.some(x=>!Number.isFinite(x)))continue;
  const code=v.reduce((s,x,k)=>s+(x>=level?1<<k:0),0);if(code===0||code===15)continue;
  let pairs=cases[code];const above=(v[0]+v[1]+v[2]+v[3])/4>=level;
  if(code===5)pairs=above?[[0,1],[2,3]]:[[3,0],[1,2]];
  if(code===10)pairs=above?[[3,0],[1,2]]:[[0,1],[2,3]];
  const c=[[xs[i],ys[j]],[xs[i+1],ys[j]],[xs[i+1],ys[j+1]],[xs[i],ys[j+1]]];
  const cross=edge=>{const [a,b]=edges[edge],t=(level-v[a])/(v[b]-v[a]);return [c[a][0]+t*(c[b][0]-c[a][0]),c[a][1]+t*(c[b][1]-c[a][1])]};
  for(const pair of pairs){const a=cross(pair[0]),b=cross(pair[1]);if([...a,...b].every(Number.isFinite)&&Math.hypot(a[0]-b[0],a[1]-b[1])>1e-9)out.push({level,a,b})}
 }}return out;
}
// Bilinear interpolation is presentation-only; gaps, regional edges and polar caps stay empty.
function sampledGrid(coords,values){
 const ys=[...new Set(coords.map(c=>c[0]))].sort((a,b)=>a-b),xs=[...new Set(coords.map(c=>c[1]))].sort((a,b)=>a-b);
 const gap=a=>{const g=a.slice(1).map((v,i)=>v-a[i]).sort((a,b)=>a-b);return g[Math.floor(g.length/2)]||0};
 const dx=gap(xs),dy=gap(ys),wrap=xs.length>3&&Math.abs(xs.at(-1)-xs[0]+dx-360)<dx*.2;
 const xi=new Map(xs.map((x,i)=>[x,i])),yi=new Map(ys.map((y,i)=>[y,i]));
 const g=Array.from({length:ys.length},()=>Array(xs.length).fill(null));coords.forEach((c,i)=>{g[yi.get(c[0])][xi.get(c[1])]=values[i]});
 if(wrap){xs.push(xs[0]+360);g.forEach(r=>r.push(r[0]))}
 function bracket(a,x){let l=0,h=a.length-1;if(x<a[0]||x>a[h])return -1;while(h-l>1){const m=(l+h)>>1;if(a[m]<=x)l=m;else h=m}return l}
 function sample(lon,lat){if(wrap)lon=((lon-xs[0])%360+360)%360+xs[0];const i=bracket(xs,lon),j=bracket(ys,lat);if(i<0||j<0||xs[i+1]-xs[i]>dx*1.8||ys[j+1]-ys[j]>dy*1.8)return null;const v=[g[j][i],g[j][i+1],g[j+1][i],g[j+1][i+1]];if(!v.every(Number.isFinite))return null;const x=(lon-xs[i])/(xs[i+1]-xs[i]),y=(lat-ys[j])/(ys[j+1]-ys[j]);return (1-y)*(v[0]*(1-x)+v[1]*x)+y*(v[2]*(1-x)+v[3]*x)}
 return {xs,ys,g,dx,dy,wrap,sample};
}
function smoothContourSegments(coords,values,levels){
 const grid=sampledGrid(coords,values),cc=[],vv=[],steps=3;
 // Subdivide the same bilinear field rather than smoothing across missing cells.
 for(let j=0;j<grid.ys.length-1;j++)for(let sy=0;sy<steps;sy++){
  const y=grid.ys[j]+(grid.ys[j+1]-grid.ys[j])*sy/steps;
  for(let i=0;i<grid.xs.length-1;i++)for(let sx=0;sx<steps;sx++){const x=grid.xs[i]+(grid.xs[i+1]-grid.xs[i])*sx/steps;cc.push([y,x]);vv.push(grid.sample(x,y))}
  cc.push([y,grid.xs.at(-1)]);vv.push(grid.sample(grid.xs.at(-1),y));
 }
 const y=grid.ys.at(-1);for(let i=0;i<grid.xs.length-1;i++)for(let sx=0;sx<steps;sx++){const x=grid.xs[i]+(grid.xs[i+1]-grid.xs[i])*sx/steps;cc.push([y,x]);vv.push(grid.sample(x,y))}cc.push([y,grid.xs.at(-1)]);vv.push(grid.sample(grid.xs.at(-1),y));
 return contourSegments(cc,vv,levels);
}
root.sampledGrid=sampledGrid;root.smoothContourSegments=smoothContourSegments;root.contourSegments=contourSegments;if(typeof module!=='undefined')module.exports={contourSegments,sampledGrid,smoothContourSegments};
})(typeof globalThis!=='undefined'?globalThis:this);
