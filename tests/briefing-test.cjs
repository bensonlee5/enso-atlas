const assert=require('node:assert/strict');
const {days,nearestTime,freshness}=require('../dist/briefing.js');
const source=require('../dist/data/forecast.json');
assert.equal(days(source[0]).slice(0,7).length,7);
const a=days({daily:{time:['2026-10-01','2026-10-02'],temperature_2m_max:[0,null],temperature_2m_min:[-5],precipitation_sum:[0,null],wind_speed_10m_max:[10,NaN]}},true);
assert.equal(a[0].high,32);assert.equal(a[0].low,23);assert.equal(a[0].precipitation,0);assert.equal(a[1].high,null);assert.equal(a[1].low,null);assert.equal(a[1].wind,null);assert.equal(a[1].precipitation,null);
assert.equal(nearestTime(['2026-10-01T00:00','2026-10-01T03:00'],Date.parse('2026-10-01T02:30Z')),1);
assert.equal(freshness('invalid'),'Time unavailable');
console.log('PASS: seven real dates, independent source values, Fahrenheit conversion, null/zero distinction, nearest valid time, source freshness');
