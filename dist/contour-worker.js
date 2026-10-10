'use strict';
importScripts('contours.js');
let coordinates=null;
self.onmessage=({data})=>{try{if(data.coords)coordinates=data.coords;if(!coordinates)throw Error('Missing grid');const start=performance.now(),segments=adaptiveContourSegments(coordinates,data.values,data.levels,data.options);self.postMessage({id:data.id,key:data.key,segments,milliseconds:performance.now()-start},[segments.data.buffer]);}catch(error){self.postMessage({id:data.id,key:data.key,error:String(error.message)});}};
