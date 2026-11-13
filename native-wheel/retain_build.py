"""Retain a private QA artifact when the Actions artifact quota is full."""
import base64,hashlib,json,os,subprocess,sys
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
label,target,*sources=sys.argv[1:]
if sources:
    with ZipFile(target,'w',ZIP_DEFLATED) as z:
        for pattern in sources:
            import glob
            for p in glob.glob(pattern):z.write(p,Path(p).name)
repo=os.environ['GITHUB_REPOSITORY']
assert subprocess.check_output(['gh','api',f'repos/{repo}','--jq','.private'],text=True).strip()=='true'
data=Path(target).read_bytes();chunks=[]
for off in range(0,len(data),48000):
    body=json.dumps({'encoding':'utf-8','content':base64.b64encode(data[off:off+48000]).decode()})
    chunks.append(subprocess.check_output(['gh','api','--method','POST',f'repos/{repo}/git/blobs','--input','-','--jq','.sha'],input=body,text=True).strip())
print(label+'_CHUNKS='+json.dumps(chunks));print(label+'_SHA256='+hashlib.sha256(data).hexdigest())
