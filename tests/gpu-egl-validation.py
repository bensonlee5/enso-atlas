import ctypes as C,re,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['EGL_PLATFORM']='surfaceless'
e=C.CDLL('libEGL.so.1'); P=C.c_void_p; I=C.c_int; U=C.c_uint
for name,restype,args in [('eglGetDisplay',P,[P]),('eglInitialize',U,[P,C.POINTER(I),C.POINTER(I)]),('eglBindAPI',U,[U]),('eglChooseConfig',U,[P,C.POINTER(I),C.POINTER(P),I,C.POINTER(I)]),('eglCreatePbufferSurface',P,[P,P,C.POINTER(I)]),('eglCreateContext',P,[P,P,P,C.POINTER(I)]),('eglMakeCurrent',U,[P,P,P,P]),('eglGetProcAddress',P,[C.c_char_p])]:
 f=getattr(e,name);f.restype=restype;f.argtypes=args
D=e.eglGetDisplay(None);major=I();minor=I();assert e.eglInitialize(D,C.byref(major),C.byref(minor)), 'EGL initialization unavailable'
a=(I*15)(0x3033,1,0x3040,4,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038,0,0);cfg=P();n=I();assert e.eglChooseConfig(D,a,C.byref(cfg),1,C.byref(n)) and n.value
assert e.eglBindAPI(0x30A0)
s=e.eglCreatePbufferSurface(D,cfg,(I*5)(0x3057,512,0x3056,512,0x3038));c=e.eglCreateContext(D,cfg,None,(I*3)(0x3098,2,0x3038));assert c and s and e.eglMakeCurrent(D,s,s,c)
def gl(name,r,args):return C.CFUNCTYPE(r,*args)(e.eglGetProcAddress(name.encode()))
create=gl('glCreateShader',U,[U]);source=gl('glShaderSource',None,[U,I,C.POINTER(C.c_char_p),C.POINTER(I)]);compile=gl('glCompileShader',None,[U]);get=gl('glGetShaderiv',None,[U,U,C.POINTER(I)]);log=gl('glGetShaderInfoLog',None,[U,I,C.POINTER(I),C.c_char_p]);string=gl('glGetString',C.c_char_p,[U]);print('Renderer:',string(0x1F01).decode(),'Version:',string(0x1F02).decode())
code=open(ROOT/'dist/globe-renderer.js').read(); shaders=[]
for name,typ,src in [('vertex',0x8B31,re.search("const vertex='(.*?)';",code,re.S)[1]),('fragment',0x8B30,re.search('const fragment=`(.*?)`;',code,re.S)[1])]:
 sh=create(typ);data=C.c_char_p(src.encode());source(sh,1,C.byref(data),None);compile(sh);ok=I();get(sh,0x8B81,C.byref(ok));b=C.create_string_buffer(4096);log(sh,4096,None,b);print(name, bool(ok.value),b.value.decode());assert ok.value;shaders.append(sh)
program=gl('glCreateProgram',U,[])();attach=gl('glAttachShader',None,[U,U]);link=gl('glLinkProgram',None,[U]);gp=gl('glGetProgramiv',None,[U,U,C.POINTER(I)])
for sh in shaders:attach(program,sh)
link(program);ok=I();gp(program,0x8B82,C.byref(ok));assert ok.value,'link failed';print('PASS exact production GLSL ES shaders compiled and linked in independent Mesa EGL context')
from PIL import Image,ImageDraw
import json, math,time
use=gl('glUseProgram',None,[U]);use(program)
gen=gl('glGenBuffers',None,[I,C.POINTER(U)]);bind=gl('glBindBuffer',None,[U,U]);buf=U();gen(1,C.byref(buf));bind(0x8892,buf);vertices=(C.c_float*12)(-1,-1,1,-1,-1,1,-1,1,1,-1,1,1);gl('glBufferData',None,[U,C.c_ssize_t,P,U])(0x8892,C.sizeof(vertices),vertices,0x88E4)
a=gl('glGetAttribLocation',I,[U,C.c_char_p])(program,b'a');gl('glEnableVertexAttribArray',None,[U])(a);gl('glVertexAttribPointer',None,[U,I,U,U,I,P])(a,2,0x1406,0,0,None)
ul=gl('glGetUniformLocation',I,[U,C.c_char_p]);f=gl('glUniform1f',None,[I,C.c_float]);f2=gl('glUniform2f',None,[I,C.c_float,C.c_float]);f3=gl('glUniform3f',None,[I,C.c_float,C.c_float,C.c_float]);ui=gl('glUniform1i',None,[I,I]);loc=lambda s:ul(program,s.encode())
f2(loc('size'),512,512);f2(loc('center'),256,256);f(loc('radius'),230);l=math.radians(-108);t=math.radians(29)
f3(loc('east'),math.cos(l),0,-math.sin(l));f3(loc('north'),-math.sin(t)*math.sin(l),math.cos(t),-math.sin(t)*math.cos(l));f3(loc('front'),math.cos(t)*math.sin(l),math.sin(t),math.cos(t)*math.cos(l));sl=math.radians(-60);sb=math.radians(-3);f3(loc('sun'),math.cos(sb)*math.sin(sl),math.sin(sb),math.cos(sb)*math.cos(sl));f(loc('lighting'),1);f(loc('hasSurface'),1)
mask=Image.new('RGBA',(2048,1024),(0,0,0,255));dr=ImageDraw.Draw(mask)
for feature in json.load(open(ROOT/'dist/data/world.json'))['features']:
 geo=feature['geometry'];polys=[geo['coordinates']] if geo['type']=='Polygon' else geo['coordinates']
 for poly in polys:
  for index,ring in enumerate(poly):dr.polygon([((lo+180)/360*2048,(90-la)/180*1024) for lo,la in ring],fill='white' if index==0 else 'black')
for unit,im,name in [(0,mask,'land'),(1,Image.open(ROOT/'dist/earth-surface.jpg').convert('RGBA'),'surface')]:
 tex=U();gl('glGenTextures',None,[I,C.POINTER(U)])(1,C.byref(tex));gl('glActiveTexture',None,[U])(0x84C0+unit);gl('glBindTexture',None,[U,U])(0x0DE1,tex);raw=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes();rawbuf=C.create_string_buffer(raw)
 gl('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0x0DE1,0,0x1908,im.width,im.height,0,0x1908,0x1401,rawbuf)
 par=gl('glTexParameteri',None,[U,U,I])
 for key,val in [(0x2801,0x2601),(0x2800,0x2601),(0x2802,0x812F),(0x2803,0x812F)]:par(0x0DE1,key,val)
 ui(loc(name),unit)
gl('glViewport',None,[I,I,I,I])(0,0,512,512);draw=gl('glDrawArrays',None,[U,I,I]);finish=gl('glFinish',None,[]);draw(4,0,6);finish();start=time.perf_counter()
for k in range(30):draw(4,0,6);finish()
print('Software-render benchmark, 512x512, 30frames:',round((time.perf_counter()-start)*1000/30,2),'ms/frame; not browser/device performance')
pixels=C.create_string_buffer(512*512*4);gl('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,512,512,0x1908,0x1401,pixels)
Image.frombytes('RGBA',(512,512),pixels.raw).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(os.environ.get('ENSO_RENDER_OUTPUT','/tmp/enso-gpu-shader-validation.png'));print('Saved exact shader offscreen validation render')
