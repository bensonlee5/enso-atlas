'use strict';
const assert=require('node:assert/strict'),{boot,sleep}=require('./location-search-test.cjs');
(async()=>{const t=await boot({},false,{reducedMotion:false});await sleep(25);t.eval('R=350;W=900;H=700;CX=450;CY=350');
t.eval('window.detailField={...globalField,playback:true};drawContours(detailField);window.playingSegments=contourCache.segments;window.levelCount=contourLevels(detailField).length');
assert.equal(t.eval('contourCache.segments.quality.levels'),t.eval('levelCount'));assert.equal(t.eval('contourCache.segments.quality.withheld'),0);
t.eval('detailField.playback=false;drawContours(detailField)');assert.equal(t.eval('playingSegments===contourCache.segments'),true,'Paused/playing reuse identical full-precision geometry');assert.equal(t.eval('contourCache.segments.quality.radius'),400);
t.eval('R=450;drawContours(detailField)');assert.equal(t.eval('playingSegments===contourCache.segments'),false);assert.equal(t.eval('contourCache.segments.quality.radius'),500);assert.equal(t.eval('contourCache.segments.quality.levels'),t.eval('levelCount'));assert.deepEqual(t.errors,[]);t.dom.window.close();console.log('PASS contour rendering: all levels retained, identical paused/playing geometry/cache, conservative zoom invalidation, no hidden contour coarsening');
})().catch(e=>{console.error(e.stack);process.exit(1)});
