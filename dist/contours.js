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
 const dx=gap(xs),dy=gap(ys),seam=360-(xs.at(-1)-xs[0]),wrap=xs.length>3&&seam>0&&seam<=dx*1.8&&xs.at(-1)-xs[0]>=270;
 const xi=new Map(xs.map((x,i)=>[x,i])),yi=new Map(ys.map((y,i)=>[y,i]));
 const g=Array.from({length:ys.length},()=>Array(xs.length).fill(null));coords.forEach((c,i)=>{g[yi.get(c[0])][xi.get(c[1])]=values[i]});
 if(wrap){xs.push(xs[0]+360);g.forEach(r=>r.push(r[0]))}
 function bracket(a,x){let l=0,h=a.length-1;if(x<a[0]||x>a[h])return -1;while(h-l>1){const m=(l+h)>>1;if(a[m]<=x)l=m;else h=m}return l}
 function sample(lon,lat){if(wrap)lon=((lon-xs[0])%360+360)%360+xs[0];const i=bracket(xs,lon),j=bracket(ys,lat);if(i<0||j<0||xs[i+1]-xs[i]>dx*1.8||ys[j+1]-ys[j]>dy*1.8)return null;const v=[g[j][i],g[j][i+1],g[j+1][i],g[j+1][i+1]];if(!v.every(Number.isFinite))return null;const x=(lon-xs[i])/(xs[i+1]-xs[i]),y=(lat-ys[j])/(ys[j+1]-ys[j]);return (1-y)*(v[0]*(1-x)+v[1]*x)+y*(v[2]*(1-x)+v[3]*x)}
 return {xs,ys,g,dx,dy,wrap,sample};
}
function smoothContourSegments(coords,values,levels,steps=3){
 const grid=sampledGrid(coords,values),cc=[],vv=[];
 // Subdivide the same bilinear field rather than smoothing across missing cells.
 for(let j=0;j<grid.ys.length-1;j++)for(let sy=0;sy<steps;sy++){
  const y=grid.ys[j]+(grid.ys[j+1]-grid.ys[j])*sy/steps;
  for(let i=0;i<grid.xs.length-1;i++)for(let sx=0;sx<steps;sx++){const x=grid.xs[i]+(grid.xs[i+1]-grid.xs[i])*sx/steps;cc.push([y,x]);vv.push(grid.sample(x,y))}
  cc.push([y,grid.xs.at(-1)]);vv.push(grid.sample(grid.xs.at(-1),y));
 }
 const y=grid.ys.at(-1);for(let i=0;i<grid.xs.length-1;i++)for(let sx=0;sx<steps;sx++){const x=grid.xs[i]+(grid.xs[i+1]-grid.xs[i])*sx/steps;cc.push([y,x]);vv.push(grid.sample(x,y))}cc.push([y,grid.xs.at(-1)]);vv.push(grid.sample(grid.xs.at(-1),y));
 return contourSegments(cc,vv,levels);
}
// Reuse only coordinate topology; scalar values and every requested level remain current.
const contourTopologyCache=new WeakMap();
function contourTopology(coords){
 let result=contourTopologyCache.get(coords);if(result)return result;
 const grid=sampledGrid(coords,coords.map((_,i)=>i)),cells=[];
 for(let y=0;y<grid.ys.length-1;y++)for(let x=0;x<grid.xs.length-1;x++){
  const dx=grid.xs[x+1]-grid.xs[x],dy=grid.ys[y+1]-grid.ys[y];
  if(dx>grid.dx*1.8||dy>grid.dy*1.8)continue;
  const indices=[grid.g[y][x],grid.g[y][x+1],grid.g[y+1][x+1],grid.g[y+1][x]];
  if(indices.every(Number.isInteger))cells.push({indices,x:grid.xs[x],y:grid.ys[y],dx,dy});
 }
 result={cells,wrap:grid.wrap};contourTopologyCache.set(coords,result);return result;
}
// Trace the bilinear isoline itself. Chords are accepted only within explicit scalar
// and conservative orthographic-projection error bounds. No post-hoc curve fitting.
function adaptiveContourSegments(coords,values,levels,options={}){
 const sorted=[...new Set(levels.filter(Number.isFinite))].sort((a,b)=>a-b),buckets=sorted.map(()=>[]),topology=contourTopology(coords);
 const radius=Math.max(1,options.radius||320),pixelTolerance=Math.max(.05,options.pixelTolerance||.3),gaps=sorted.slice(1).map((v,i)=>v-sorted[i]),scalarTolerance=Math.max(1e-8,options.scalarTolerance||Math.min(.02,(gaps.length?Math.min(...gaps):1)*.02));
 const packed=options.packed===true,maxDepth=Math.min(32,Math.max(1,options.maxDepth||24)),maxSegments=Math.min(1000000,options.maxSegments||500000),maxWork=2000000,rad=Math.PI/180;const view=options.view&&Number.isFinite(options.view.longitude)&&Number.isFinite(options.view.latitude)?options.view:null;
 const quality={scalarTolerance,pixelTolerance,radius,visited:0,segments:0,withheld:0,depthLimit:0,segmentLimit:0,workLimit:0,numericalFailure:0,maxDepth:0,levels:sorted.length};
 const lower=(v)=>{let a=0,b=sorted.length;while(a<b){const m=(a+b)>>1;if(sorted[m]<v)a=m+1;else b=m}return a};
 const cases={1:[[3,0]],2:[[0,1]],3:[[3,1]],4:[[1,2]],6:[[0,2]],7:[[3,2]],8:[[2,3]],9:[[2,0]],11:[[1,2]],12:[[1,3]],13:[[0,1]],14:[[3,0]]},edges=[[0,1],[1,2],[2,3],[3,0]],corners=[[0,0],[1,0],[1,1],[0,1]];
 for(const cell of topology.cells){
  if(view){const phi=(cell.y+cell.dy/2)*rad,center=view.latitude*rad,delta=(cell.x+cell.dx/2-view.longitude)*rad,dot=Math.sin(phi)*Math.sin(center)+Math.cos(phi)*Math.cos(center)*Math.cos(delta),margin=(Math.abs(cell.dx)+Math.abs(cell.dy))/2+(view.marginDegrees||0);if(margin<90&&dot< -Math.sin(margin*rad))continue;}
  const ids=cell.indices,v=[values[ids[0]],values[ids[1]],values[ids[2]],values[ids[3]]];if(!Number.isFinite(v[0])||!Number.isFinite(v[1])||!Number.isFinite(v[2])||!Number.isFinite(v[3]))continue;
  const min=Math.min(v[0],v[1],v[2],v[3]),max=Math.max(v[0],v[1],v[2],v[3]);if(min===max)continue;const b=v[1]-v[0],c=v[3]-v[0],d=v[2]-v[1]-v[3]+v[0];
  for(let k=lower(min);k<sorted.length&&sorted[k]<=max;k++){
   const level=sorted[k],a=v[0]-level,q=a*d-b*c,scale=Math.max(1,Math.abs(v[0]-level),Math.abs(v[1]-level),Math.abs(v[2]-level),Math.abs(v[3]-level));
   const code=(v[0]>=level?1:0)+(v[1]>=level?2:0)+(v[2]>=level?4:0)+(v[3]>=level?8:0);
   const crossing=edge=>{const [i,j]=edges[edge],t=(level-v[i])/(v[j]-v[i]);return [corners[i][0]+t*(corners[j][0]-corners[i][0]),corners[i][1]+t*(corners[j][1]-corners[i][1])]};
   const emit=(p,z)=>{if(quality.segments>=maxSegments){quality.withheld++;quality.segmentLimit++;return}const aa=[cell.x+p[0]*cell.dx,cell.y+p[1]*cell.dy],bb=[cell.x+z[0]*cell.dx,cell.y+z[1]*cell.dy];if(Math.hypot(aa[0]-bb[0],aa[1]-bb[1])<1e-10)return;if(packed)buckets[k].push(level,aa[0],aa[1],bb[0],bb[1]);else buckets[k].push({level,a:aa,b:bb});quality.segments++;};
   function refine(p,z,depth){
    quality.visited++;quality.maxDepth=Math.max(quality.maxDepth,depth);if(quality.visited>maxWork||quality.segments>=maxSegments){quality.withheld++;if(quality.visited>maxWork)quality.workLimit++;else quality.segmentLimit++;return}
    const du=z[0]-p[0],dv=z[1]-p[1],scalarError=Math.abs(d*du*dv)/4,angle=(Math.abs(du*cell.dx)+Math.abs(dv*cell.dy))*rad,projectionChord=radius*angle*angle/8;
    let mid=[(p[0]+z[0])/2,(p[1]+z[1])/2],deviation=0;
    // Exact straight branches need only projection refinement, including saddle arms.
    if(scalarError>1e-13*scale){
     const horizontal=Math.abs(du*cell.dx)>=Math.abs(dv*cell.dy),axis=horizontal?0:1,other=1-axis,coefficient=horizontal?b:c,denominator=horizontal?c:b,u0=p[axis],u1=z[axis],slope=(z[other]-p[other])/(u1-u0),solve=u=>-(a+coefficient*u)/(denominator+d*u),um=(u0+u1)/2;
     mid=horizontal?[um,solve(um)]:[solve(um),um];
     if(!Number.isFinite(mid[0])||!Number.isFinite(mid[1])||mid[0]< -1e-8||mid[0]>1+1e-8||mid[1]< -1e-8||mid[1]>1+1e-8){quality.withheld++;quality.numericalFailure++;return}
     const deviationAt=u=>Math.abs(solve(u)-(p[other]+slope*(u-u0)));let maximumDeviation=deviationAt(um);
     if(d!==0&&q/slope>0){const root=Math.sqrt(q/slope),lo=Math.min(u0,u1),hi=Math.max(u0,u1),up=(root-denominator)/d,un=(-root-denominator)/d;if(up>lo&&up<hi)maximumDeviation=Math.max(maximumDeviation,deviationAt(up));if(un>lo&&un<hi)maximumDeviation=Math.max(maximumDeviation,deviationAt(un));}
     deviation=maximumDeviation*(horizontal?cell.dy:cell.dx);
    }
    const projectionError=radius*rad*deviation+projectionChord;
    if(scalarError<=scalarTolerance&&projectionError<=pixelTolerance){emit(p,z);return}
    if(depth>=maxDepth){quality.withheld++;quality.depthLimit++;return}
    refine(p,mid,depth+1);refine(mid,z,depth+1);
   }
   // Factored level sets can have boundary saddles or complete zero edges,
   // not just the four-crossing marching-square cases. Trace their exact arms.
   if(d!==0&&Math.abs(q/d)<=Number.EPSILON*scale*128){const x=-c/d,y=-b/d,insideX=x>=0&&x<=1,insideY=y>=0&&y<=1;if(insideX||insideY){if(insideX){if(insideY){refine([x,0],[x,y],0);refine([x,y],[x,1],0)}else refine([x,0],[x,1],0)}if(insideY){if(insideX){refine([0,y],[x,y],0);refine([x,y],[1,y],0)}else refine([0,y],[1,y],0)}continue}}
   if(d===0&&b===0&&c!==0){const y=-a/c;if(y>=0&&y<=1)refine([0,y],[1,y],0);continue}
   if(d===0&&c===0&&b!==0){const x=-a/b;if(x>=0&&x<=1)refine([x,0],[x,1],0);continue}
   if(code===0||code===15)continue;
   const pairs=code===5||code===10?(q>0?[[0,1],[2,3]]:[[3,0],[1,2]]):cases[code];
   for(const pair of pairs)refine(crossing(pair[0]),crossing(pair[1]),0);
  }
 }
 if(packed){const data=new Float64Array(quality.segments*5);let offset=0;for(const bucket of buckets){data.set(bucket,offset);offset+=bucket.length;}return {data,length:quality.segments,quality};}
 const out=buckets.flat();Object.defineProperty(out,'quality',{value:quality});return out;
}
root.adaptiveContourSegments=adaptiveContourSegments;root.contourTopology=contourTopology;root.sampledGrid=sampledGrid;root.smoothContourSegments=smoothContourSegments;root.contourSegments=contourSegments;if(typeof module!=='undefined')module.exports={contourSegments,sampledGrid,smoothContourSegments,adaptiveContourSegments,contourTopology};
})(typeof globalThis!=='undefined'?globalThis:this);
