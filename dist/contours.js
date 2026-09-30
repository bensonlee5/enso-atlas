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
root.contourSegments=contourSegments;if(typeof module!=='undefined')module.exports={contourSegments};
})(typeof globalThis!=='undefined'?globalThis:this);
