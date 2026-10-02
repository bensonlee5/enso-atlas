#!/usr/bin/env python3
"""Restore/publish immutable forecast objects with a last-written CAS manifest.

Standard library only. The upload job installs no decoding packages and never
executes files from its intermediate artifact. Authorization stays in memory.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

SITE='https://enso-weather-atlas.bensonlee5.chatgpt.site'
API='/api/forecasts'
BROWSER_FILES=frozenset(('cfs-weekly-raw-60days.json','cfs-weekly-anomalies.json','enso-observations.json','ensemble-percentiles.json','verification.json','cfs-global-60days.json','aifs-global-snapshots.json'))
AUDIT='ensemble-member-means.json.gz'
MAX_OBJECTS=410
MAX_TOTAL_BYTES=64_000_000
MAX_MANIFEST_BYTES=200_000
MAX_FILE_BYTES=8_000_000
LEGACY_COMMIT='f8e4c04a0db70228fe954e439bda0d41e67021bd'
LEGACY_ARCHIVES={
 '2026092900.json':'71e41a9e90167ff598b1e5f919e7e2c61f58c228e3bd2de17b5981376d45dea9',
 '2026093000.json':'fa6da4b895b2f6df119bc97de92b7400a450ecc8351c4efcfd57257f1ab1826d',
 '2026100100.json':'86178340e129c96711ee6d30ddfd636cdd5448c44b5ebdfc790dbb7469cfbb8a',
}

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def sha(body):return hashlib.sha256(body).hexdigest()
def allowed_name(name):return isinstance(name,str) and (name in BROWSER_FILES or name in (AUDIT,'archive/index.json') or re.fullmatch(r'archive/20[0-9]{6}00\.json',name) is not None)
def file_limit(name):
 if name==AUDIT:return 8_000_000
 if name in BROWSER_FILES:return 5_000_000
 if allowed_name(name):return 200_000
 return 0
def release_id(manifest):return sha(canonical({k:manifest[k] for k in ('files','objects','initializations')}))
def metadata(body):return {'sha256':sha(body),'bytes':len(body)}
def validate_manifest(manifest):
 if manifest.get('schemaVersion')!=1 or manifest.get('storageVersion')!=1:raise ValueError('Unsupported storage manifest')
 objects=manifest.get('objects',{})
 if set(manifest.get('files',{}))!=BROWSER_FILES or not set(BROWSER_FILES|{AUDIT,'archive/index.json'}).issubset(objects):raise ValueError('Missing required forecast objects')
 if not 9<=len(objects)<=MAX_OBJECTS:raise ValueError('Object count exceeds bounded archive window')
 total=0
 for name,meta in objects.items():
  if not allowed_name(name) or not isinstance(meta,dict) or set(meta)!={'sha256','bytes'}:raise ValueError('Unexpected object name/metadata')
  if not isinstance(meta['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',meta['sha256']):raise ValueError('Invalid object digest')
  if type(meta['bytes']) is not int or not 0<meta['bytes']<=file_limit(name):raise ValueError('Invalid object size')
  total+=meta['bytes']
 if total>MAX_TOTAL_BYTES:raise ValueError('Active bundle exceeds 64 MB budget')
 if any(objects[n]!=meta for n,meta in manifest['files'].items()):raise ValueError('Browser and object manifests differ')
 if set(manifest.get('initializations',{}))!={'raw','anomaly','ensemble','ensoObservation','globalCfs','aifs'}:raise ValueError('Incomplete source initialization guards')
 if manifest.get('releaseID')!=release_id(manifest):raise ValueError('Manifest release digest mismatch')
 return manifest

def build_manifest(folder):
 folder=Path(folder);manifest=json.loads((folder/'refresh-manifest.json').read_text())
 index=json.loads((folder/'archive/index.json').read_text())
 if index.get('schemaVersion')!=1 or not isinstance(index.get('issuances'),list) or len(index['issuances'])>400:raise ValueError('Invalid bounded archive index')
 names=set(BROWSER_FILES)|{AUDIT,'archive/index.json'}
 for entry in index['issuances']:
  name='archive/'+entry['path']
  if not allowed_name(name) or name=='archive/index.json':raise ValueError('Unexpected archived path')
  if metadata((folder/name).read_bytes())['sha256']!=entry['sha256']:raise ValueError('Archive index digest mismatch')
  names.add(name)
 manifest['objects']={name:metadata((folder/name).read_bytes()) for name in sorted(names)}
 manifest['storageVersion']=1
 manifest['releaseID']=release_id(manifest)
 validate_manifest(manifest)
 for name,meta in manifest['files'].items():
  if manifest['objects'][name]!=meta:raise ValueError('Source manifest digest mismatch')
 if len(canonical(manifest))>MAX_MANIFEST_BYTES:raise ValueError('Manifest exceeds budget')
 return manifest

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  raise urllib.error.HTTPError(req.full_url,code,'HTTP redirects are not allowed',headers,fp)

def bootstrap_archives(folder,fetcher=None):
 """Migrate original issued bytes from one verified historical Git commit.

 This is a read-only compatibility bridge, not a continuing GitHub data feed.
 Every future issuance is obtained from NOAA and stored externally.
 """
 opener=urllib.request.build_opener(NoRedirect())
 def read(name):
  url=f'https://raw.githubusercontent.com/bensonlee5/enso-atlas/{LEGACY_COMMIT}/dist/data/archive/{name}'
  with opener.open(urllib.request.Request(url,headers={'User-Agent':'ENSOAtlas-archive-migration/1.0'}),timeout=45) as response:
   raw=response.read(200_001)
   if len(raw)>200_000:raise ValueError('Legacy archive exceeds size budget')
   return raw
 fetcher=fetcher or read;entries=[];verified={}
 for name,digest in LEGACY_ARCHIVES.items():
  raw=fetcher(name)
  if len(raw)>200_000 or sha(raw)!=digest:raise ValueError('Legacy archive hash mismatch: '+name)
  record=json.loads(raw);verified[name]=raw
  entries.append({'run':record['run'],'path':name,'sha256':digest,'archivedAt':record['archivedAt']})
 target=Path(folder)/'archive';target.mkdir(parents=True,exist_ok=True)
 for name,raw in verified.items():
  path=target/name
  if path.exists() and path.read_bytes()!=raw:raise ValueError('Refusing to replace conflicting legacy archive')
  path.write_bytes(raw)
 index={'schemaVersion':1,'issuances':entries,'retention':'Latest 400 issuances indexed; immutable historical objects are not automatically deleted. New forecast data is stored outside Git history.'}
 (target/'index.json').write_bytes(canonical(index))
 print('Migrated three hash-verified original issuances from fixed historical commit')

class Client:
 def __init__(self,origin=SITE):
  if origin!=SITE:raise ValueError('Only the verified production Site origin is permitted')
  self.origin=origin;self.opener=urllib.request.build_opener(NoRedirect());self.token=None;self.token_at=0
 def request(self,path,method='GET',body=None,headers=None,limit=MAX_MANIFEST_BYTES,authenticated=False,attempts=3):
  if not path.startswith(API+'/') or '..' in path or '?' in path or '#' in path:raise ValueError('Invalid forecast API path')
  headers={'User-Agent':'ENSOAtlas-forecast-publisher/1.0',**(headers or {})}
  if path==API+'/manifest':headers.update({'Cache-Control':'no-cache','Pragma':'no-cache'})
  for attempt in range(attempts):
   h=dict(headers)
   if authenticated:h['Authorization']='Bearer '+self.oidc()
   req=urllib.request.Request(self.origin+path,data=body,headers=h,method=method)
   try:
    with self.opener.open(req,timeout=90) as r:
     data=r.read(limit+1)
     if len(data)>limit:raise ValueError('Service response exceeds bounded size')
     return r.status,dict(r.headers),data
   except urllib.error.HTTPError as ex:
    # CAS conflicts never acquire a new predecessor or silently republish.
    if ex.code in (404,409,412):return ex.code,dict(ex.headers),ex.read(min(limit,2048))
    if ex.code not in (429,500,502,503,504) or attempt==attempts-1:raise RuntimeError(f'{method} forecast service failed with HTTP {ex.code}') from None
   except (TimeoutError,urllib.error.URLError):
    if attempt==attempts-1:raise
   time.sleep(2**attempt)
 def oidc(self):
  if self.token and time.monotonic()-self.token_at<60:return self.token
  url=os.environ.get('ACTIONS_ID_TOKEN_REQUEST_URL','');credential=os.environ.get('ACTIONS_ID_TOKEN_REQUEST_TOKEN','')
  parsed=urllib.parse.urlsplit(url)
  if parsed.scheme!='https' or not parsed.hostname or not parsed.hostname.endswith('.actions.githubusercontent.com') or parsed.username or not credential:raise RuntimeError('GitHub Actions OIDC is unavailable in this job')
  query=urllib.parse.parse_qsl(parsed.query,keep_blank_values=True)
  query=[(k,v) for k,v in query if k!='audience']+[('audience',self.origin)]
  url=urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query)))
  req=urllib.request.Request(url,headers={'Authorization':'Bearer '+credential})
  with self.opener.open(req,timeout=30) as r:
   body=r.read(32_001)
   if len(body)>32_000:raise ValueError('Oversized OIDC response')
   token=json.loads(body).get('value')
  if not isinstance(token,str) or len(token)>16_000 or token.count('.')!=2:raise ValueError('Invalid OIDC response')
  self.token=token;self.token_at=time.monotonic();return token

def object_path(name,meta):
 if not allowed_name(name):raise ValueError('Unexpected object path')
 return API+'/objects/'+meta['sha256']+'/'+name

def restore(client,folder,state_path,allow_bootstrap=False):
 status,headers,body=client.request(API+'/manifest')
 if status==404:
  if not allow_bootstrap:raise RuntimeError('No forecast feed exists; explicitly allow a daily bootstrap')
  Path(folder).mkdir(parents=True,exist_ok=True)
  bootstrap_archives(folder)
  Path(state_path).write_bytes(canonical({'etag':None,'releaseID':None,'objects':{}}))
  print('No stored manifest: explicit daily bootstrap required');return None
 if status!=200:raise RuntimeError(f'Cannot restore established feed (HTTP {status}); refusing fallback')
 manifest=validate_manifest(json.loads(body));etag=next((v for k,v in headers.items() if k.lower()=='etag'),None)
 if not etag:raise ValueError('Stored manifest must provide an ETag for compare-and-swap')
 with tempfile.TemporaryDirectory(prefix='enso-restore-') as temp:
  stage=Path(temp)
  for name,meta in manifest['objects'].items():
   status,_,data=client.request(object_path(name,meta),limit=meta['bytes'])
   if status!=200 or metadata(data)!=meta:raise ValueError('Stored object missing or digest mismatch: '+name)
   target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  (stage/'refresh-manifest.json').write_bytes(canonical(manifest))
  folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
  for source in stage.rglob('*'):
   if source.is_file():
    target=folder/source.relative_to(stage);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 Path(state_path).write_bytes(canonical({'etag':etag,'releaseID':manifest['releaseID'],'objects':manifest['objects']}))
 print(json.dumps({'status':'restored','releaseID':manifest['releaseID'],'objects':len(manifest['objects']),'bytes':sum(x['bytes'] for x in manifest['objects'].values())}));return manifest

def publish(client,folder,state_path):
 folder=Path(folder);manifest=build_manifest(folder);state=json.loads(Path(state_path).read_text())
 if state.get('releaseID')==manifest['releaseID']:
  status,_,body=client.request(API+'/manifest')
  if status!=200 or validate_manifest(json.loads(body))['releaseID']!=manifest['releaseID']:raise RuntimeError('Feed changed after restore; unchanged local data is not confirmed current')
  print(json.dumps({'status':'unchanged-and-read-back','releaseID':manifest['releaseID']}));return manifest
 changed=[n for n,m in manifest['objects'].items() if state.get('objects',{}).get(n)!=m]
 if len(changed)>18:raise ValueError('More than18 changed objects; split the controlled bootstrap before publication')
 uploaded=0
 for name,meta in manifest['objects'].items():
  if state.get('objects',{}).get(name)==meta:continue
  path=object_path(name,meta);status,_,_=client.request(path,method='HEAD')
  if status==404:
   data=(folder/name).read_bytes()
   if metadata(data)!=meta:raise ValueError('File changed after bundle validation')
   status,_,_=client.request(path,method='PUT',body=data,headers={'Content-Type':'application/gzip' if name==AUDIT else 'application/json','If-None-Match':'*'},authenticated=True)
   if status not in (200,201,204,412):raise RuntimeError(f'Object upload failed: HTTP {status}')
   uploaded+=len(data)
  elif status!=200:raise RuntimeError(f'Object existence check failed: HTTP {status}')
 headers={'Content-Type':'application/json'}
 headers.update({'If-Match':state['etag']} if state.get('etag') else {'If-None-Match':'*'})
 status,_,_=client.request(API+'/promote',method='POST',body=canonical(manifest),headers=headers,authenticated=True)
 if status in (409,412):
  # A timed-out successful promotion may have been retried with the old ETag.
  # Accept only exact readback; otherwise leave newer data intact and fail.
  current_status,_,current=client.request(API+'/manifest')
  if current_status!=200 or json.loads(current).get('releaseID')!=manifest['releaseID']:raise RuntimeError('Manifest race: current feed changed. Restore/regenerate in a new run; no overwrite attempted')
 elif status not in (200,201,204):raise RuntimeError(f'Manifest promotion failed: HTTP {status}')
 status,_,body=client.request(API+'/manifest')
 if status!=200 or validate_manifest(json.loads(body))['releaseID']!=manifest['releaseID']:raise RuntimeError('Promoted manifest readback not confirmed')
 print(json.dumps({'status':'published-and-read-back','releaseID':manifest['releaseID'],'uploadedBytes':uploaded,'activeBytes':sum(x['bytes'] for x in manifest['objects'].values())}));return manifest

def main():
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=('restore','publish','validate'));parser.add_argument('--data',required=True,type=Path);parser.add_argument('--state',type=Path,default=Path('forecast-publish-state.json'));parser.add_argument('--allow-bootstrap',action='store_true');args=parser.parse_args()
 if args.command=='validate':
  m=build_manifest(args.data);print(json.dumps({'releaseID':m['releaseID'],'objects':len(m['objects']),'activeBytes':sum(x['bytes'] for x in m['objects'].values())}));return
 client=Client()
 if args.command=='restore':restore(client,args.data,args.state,args.allow_bootstrap)
 else:publish(client,args.data,args.state)
if __name__=='__main__':main()
