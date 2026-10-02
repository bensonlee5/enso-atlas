// Dated NOAA snapshots are deterministic test fixtures, not live source freshness.
// Tests of arbitrary freshly downloaded bundles keep the real clock instead.
const fs=require('node:fs'),path=require('node:path');
const source=JSON.parse(fs.readFileSync(path.join(__dirname,'../dist/data/cfs-global-60days.json'),'utf8'));
const anchor=Date.parse(source.run)+86400000;
module.exports=class FixtureDate extends Date{constructor(...args){super(...(args.length?args:[anchor]))}static now(){return anchor}};
