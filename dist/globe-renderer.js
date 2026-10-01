'use strict';
/* GPU ray/sphere globe. Canvas2D is used only for map labels and scientific
   annotations; the planet, solar terminator and atmosphere are fragment shaded. */
class AtlasGlobe {
 constructor(canvas,onFailure){
  this.canvas=canvas;this.onFailure=onFailure;this.lost=false;
  const gl=this.gl=canvas.getContext('webgl',{alpha:true,antialias:false,premultipliedAlpha:false,preserveDrawingBuffer:false,powerPreference:'low-power'});
  if(!gl)throw Error('WebGL unavailable');
  const vertex='attribute vec2 a; void main(){gl_Position=vec4(a,0.,1.);}';
  const fragment=`precision highp float;
  uniform vec2 size,center;uniform float radius;uniform vec3 east,north,front,sun;
  uniform float lighting,hasSurface;uniform sampler2D land,surface;
  const float PI=3.141592653589793;
  void main(){
   vec2 q=(vec2(gl_FragCoord.x,size.y-gl_FragCoord.y)-center)/radius;
   float r2=dot(q,q);float edge=sqrt(r2);
   if(r2>1.){float rim=exp(-(edge-1.)*135.)*.38;if(edge>1.055)discard;
    gl_FragColor=vec4(vec3(.22,.53,.79),rim);return;}
   vec3 n=vec3(q.x,-q.y,sqrt(1.-r2));vec3 p=n.x*east+n.y*north+n.z*front;
   vec2 uv=vec2(atan(p.x,p.z)/(2.*PI)+.5,asin(clamp(p.y,-1.,1.))/PI+.5);
   float mask=texture2D(land,uv).r;vec3 tex=texture2D(surface,uv).rgb;
   if(hasSurface>.5)mask=max(mask,smoothstep(.035,.09,max(tex.r,tex.g)));
   vec3 ocean=vec3(.018,.076,.13);vec3 ground=mix(vec3(.16,.24,.20),vec3(.34,.34,.27),pow(abs(p.y),1.8));
   vec3 base=mix(ocean,ground,mask);if(hasSurface>.5)base=mix(ocean,tex*.8+.025,mask);
   float diffuse=dot(p,sun);float daylight=smoothstep(-.13,.20,diffuse);
   float lambert=.22+.78*max(0.,diffuse);float energy=mix(.82, mix(.095,lambert,daylight),lighting);
   vec3 lightSun=vec3(dot(sun,east),dot(sun,north),dot(sun,front));
   float spec=pow(max(0.,dot(n,normalize(lightSun+vec3(0.,0.,1.)))),85.)*.46*(1.-mask)*daylight*lighting;
   vec3 col=base*energy+vec3(.67,.82,.9)*spec;
   float fresnel=pow(1.-n.z,3.5);col+=vec3(.12,.37,.60)*fresnel*(.25+.75*daylight);
   float gridLon=abs(fract((uv.x-.5)*12.+.5)-.5);float gridLat=abs(fract((uv.y-.5)*6.+.5)-.5);
   float grid=1.-smoothstep(.001,.003,min(gridLon,gridLat));col+=vec3(.055,.10,.12)*grid*.3;
   col=pow(col,vec3(.82));gl_FragColor=vec4(col,1.-smoothstep(.998,1.,edge));
  }`;
  const compile=(type,src)=>{const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s};
  this.program=gl.createProgram();gl.attachShader(this.program,compile(gl.VERTEX_SHADER,vertex));gl.attachShader(this.program,compile(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(this.program);if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw Error('Globe shader link failed');gl.useProgram(this.program);
  const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);const a=gl.getAttribLocation(this.program,'a');gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,2,gl.FLOAT,false,0,0);
  this.u={};for(const key of ['size','center','radius','east','north','front','sun','lighting','land','surface','hasSurface'])this.u[key]=gl.getUniformLocation(this.program,key);
  this.textures=[this.texture(0),this.texture(1)];gl.uniform1i(this.u.land,0);gl.uniform1i(this.u.surface,1);
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();this.lost=true;this.onFailure()});
  canvas.addEventListener('webglcontextrestored',()=>{this.onFailure()});
 }
 texture(unit){const g=this.gl,t=g.createTexture();g.activeTexture(g.TEXTURE0+unit);g.bindTexture(g.TEXTURE_2D,t);g.texImage2D(g.TEXTURE_2D,0,g.RGBA,1,1,0,g.RGBA,g.UNSIGNED_BYTE,new Uint8Array([0,0,0,255]));g.texParameteri(g.TEXTURE_2D,g.TEXTURE_MIN_FILTER,g.LINEAR);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_MAG_FILTER,g.LINEAR);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_WRAP_S,g.CLAMP_TO_EDGE);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_WRAP_T,g.CLAMP_TO_EDGE);return t}
 upload(unit,image){const g=this.gl;g.activeTexture(g.TEXTURE0+unit);g.bindTexture(g.TEXTURE_2D,this.textures[unit]);g.pixelStorei(g.UNPACK_FLIP_Y_WEBGL,true);g.texImage2D(g.TEXTURE_2D,0,g.RGBA,g.RGBA,g.UNSIGNED_BYTE,image)}
 setWorld(world){if(!world||this.world===world||this.lost)return;this.world=world;const c=document.createElement('canvas');c.width=2048;c.height=1024;const x=c.getContext('2d');x.fillStyle='#000';x.fillRect(0,0,c.width,c.height);x.fillStyle='#fff';for(const f of world.features){const polys=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates;for(const poly of polys){x.beginPath();for(const ring of poly){ring.forEach(([lon,lat],i)=>{const a=(lon+180)/360*c.width,b=(90-lat)/180*c.height;i?x.lineTo(a,b):x.moveTo(a,b)});x.closePath()}x.fill('evenodd')}}this.upload(0,c)}
 setSurface(url){const image=new Image();image.onload=()=>{if(this.lost)return;this.upload(1,image);this.surface=true;if(typeof draw==='function')draw()};image.src=url;}
 render({width,height,dpr,cx,cy,r,lon,lat,sunLon,sunLat,shade}){if(this.lost)return false;const g=this.gl,c=this.canvas;const w=Math.round(width*dpr),h=Math.round(height*dpr);if(c.width!==w||c.height!==h){c.width=w;c.height=h}g.viewport(0,0,w,h);g.clearColor(0,0,0,0);g.clear(g.COLOR_BUFFER_BIT);g.useProgram(this.program);const rad=Math.PI/180,l=lon*rad,t=lat*rad,s=sunLon*rad,b=sunLat*rad;g.uniform2f(this.u.size,w,h);g.uniform2f(this.u.center,cx*dpr,cy*dpr);g.uniform1f(this.u.radius,r*dpr);g.uniform3f(this.u.east,Math.cos(l),0,-Math.sin(l));g.uniform3f(this.u.north,-Math.sin(t)*Math.sin(l),Math.cos(t),-Math.sin(t)*Math.cos(l));g.uniform3f(this.u.front,Math.cos(t)*Math.sin(l),Math.sin(t),Math.cos(t)*Math.cos(l));g.uniform3f(this.u.sun,Math.cos(b)*Math.sin(s),Math.sin(b),Math.cos(b)*Math.cos(s));g.uniform1f(this.u.lighting,shade?1:0);g.uniform1f(this.u.hasSurface,this.surface?1:0);g.drawArrays(g.TRIANGLES,0,6);return true;}
}
