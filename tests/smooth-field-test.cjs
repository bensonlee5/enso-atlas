const assert=require('assert');const {sampledGrid,smoothContourSegments}=require('../dist/contours.js');
let g=sampledGrid([[0,0],[0,2],[2,0],[2,2]],[0,2,2,4]);assert.equal(g.sample(1,1),2);assert.equal(g.sample(3,1),null);assert.equal(g.sample(1,3),null);
g=sampledGrid([[0,0],[0,2],[2,0],[2,2]],[0,null,2,4]);assert.equal(g.sample(1,1),null);
const coords=[],v=[];for(const y of [-80,0,80])for(const x of [-180,-90,0,90]){coords.push([y,x]);v.push(Math.cos(x*Math.PI/180))}g=sampledGrid(coords,v);assert(g.wrap);assert(Math.abs(g.sample(179,0)-g.sample(-181,0))<1e-9);assert.equal(g.sample(0,85),null);
const segments=smoothContourSegments([[0,0],[0,2],[2,0],[2,2]],[0,2,2,4],[1,2,3]);assert(segments.length>3);for(const s of segments)for(const [x,y] of [s.a,s.b]){assert(x>=0&&x<=2&&y>=0&&y<=2);assert(Math.abs(x+y-s.level)<1e-9)}
console.log('PASS smooth field: bilinear values, no extrapolation, missing-cell mask, cyclic seam, polar cap, level-preserving subdivision');
