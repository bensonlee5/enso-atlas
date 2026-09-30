"""Download only predeclared public SubseasonalClimateUSA files; no account or paid access."""
from pathlib import Path
import urllib.request,json,concurrent.futures,hashlib
ROOT=Path(__file__).resolve().parent
FILES=['iri-cfsv2-precip-all-us1_5-ensembled.h5','iri-cfsv2-tmp2m-all-us1_5-ensembled.h5','gt-us_precip_1.5x1.5-14d.h5','gt-us_tmp2m_1.5x1.5-14d.h5','gt-mei.h5']
def main():
 token=json.load(urllib.request.urlopen('https://planetarycomputer.microsoft.com/api/sas/v1/token/subseasonalusa/subseasonalusa',timeout=60))['token']
 def get(name):
  p=ROOT/'raw'/name;p.parent.mkdir(exist_ok=True)
  if not p.exists():
   with urllib.request.urlopen('https://subseasonalusa.blob.core.windows.net/subseasonalusa/dataframes/'+name+'?'+token,timeout=120) as r,p.with_suffix('.part').open('wb') as f:
    while chunk:=r.read(4*1024*1024):f.write(chunk)
   p.with_suffix('.part').rename(p)
  h=hashlib.file_digest(p.open('rb'),'sha256').hexdigest(); print(name,p.stat().st_size,h,flush=True)
  return {'file':name,'bytes':p.stat().st_size,'sha256':h,'url':'https://subseasonalusa.blob.core.windows.net/subseasonalusa/dataframes/'+name}
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: result=list(pool.map(get,FILES))
 (ROOT/'source/download_manifest.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
