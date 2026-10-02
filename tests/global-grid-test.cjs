'use strict';
const assert=require('assert/strict'),fs=require('fs'),{performance}=require('perf_hooks');
const {sampledGrid,smoothContourSegments}=require('../dist/contours.js');
const q=JSON.parse(fs.readFileSync('dist/data/ensemble-percentiles.json'));
const start=performance.now();
for(const period of [...q.weeks,q.remainingDays57to60])for(const key of q.availableQuantiles){
 const grid=sampledGrid(q.gridCoordinates,period.temperature[key]);assert(grid.wrap);
 for(const [lat,lon] of [[51,0],[36,140],[-34,151],[-24,-47],[0,20],[0,180],[0,-180],[85,0],[-85,0]])assert(Number.isFinite(grid.sample(lon,lat)),`${key} ${lat},${lon}`);
 assert(Math.abs(grid.sample(179.99,0)-grid.sample(-180.01,0))<1e-9);
 assert.equal(grid.sample(0,90),null);assert.equal(grid.sample(0,-90),null);
}
const daily=JSON.parse(fs.readFileSync('dist/data/cfs-global-60days.json'));const dailyGrid=sampledGrid(daily.gridCoordinates,daily.days[0].temperatureC);assert(dailyGrid.wrap,'Irregular native nearest samples must still close the actual periodic seam');assert(Number.isFinite(dailyGrid.sample(180,0)));assert.equal(dailyGrid.sample(0,90),null);
const segments=smoothContourSegments(q.gridCoordinates,q.weeks[0].temperature.p50,[-30,-10,0,10,20,30]);assert(segments.some(s=>s.a[0]>179||s.b[0]>179),'Contours cross the date-line neighborhood');assert(segments.length>1000);assert(segments.every(s=>[...s.a,...s.b].every(Number.isFinite)));assert(performance.now()-start<5000,'Global grid CPU budget');
console.log('PASS worldwide grids: every period/percentile, Europe/Asia/Africa/Americas/Oceania/ocean, both date-line directions, polar caps, daily periodic seam, contours, bounded CPU');
