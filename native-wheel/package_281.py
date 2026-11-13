"""Apply the six shared native leaderboard hooks to the exact supplied B280."""
from hashlib import sha256
from pathlib import Path
from struct import pack_into,unpack_from
from patch_menu_269 import branch,address,add,mov

BASE_NATIVE='917c6479a14187d4deb5538b58cdfc245dfba92f34fb85a79a71d23dce41e63c'
SITES=[0x54b838,0x637034,0x71bcf8,0x8009bc,0x8e5680,0x9ca344]
RENDER=[0x5931e8,0x67c754,0x761418,0x8460dc,0x92ada0,0xa0fa64]
SCENE=0x2508000
FILE=0x24c8000

def patch(native):
    assert sha256(native).hexdigest()==BASE_NATIVE,'Use the attached Build280 executable'
    data=bytearray(native)
    for v,(site,target)in enumerate(zip(SITES,RENDER)):
        assert unpack_from('<I',data,site)[0]==branch(site,target,True)
        # Every leaderboard uses the actual row User in x24, never the viewer.
        assert pack(0x39c36702) in data[site-80:site],hex(site)
        at=SCENE+0x1000+v*32
        words=[mov(8,v*16+4),address(at+4,target,9,page=True),add(9,target&4095),0xaa1803ea,branch(at+16,SCENE)]
        offset=FILE+at-SCENE
        assert data[offset:offset+len(words)*4]==bytes(len(words)*4)
        pack_into('<5I',data,offset,*words)
        pack_into('<I',data,site,branch(site,at,True))
    return bytes(data)

def pack(word):return word.to_bytes(4,'little')

if __name__=='__main__':
    import sys
    source,target=map(Path,sys.argv[1:]);target.write_bytes(patch(source.read_bytes()))
    print('B281 native rank hooks',sha256(target.read_bytes()).hexdigest())


def strip_signature(blob):
    """Use the same unsigned, ready-to-resign form as the supplied IPA."""
    image=bytearray(blob);count,size=unpack_from('<II',blob,16);p=32;commands=[]
    for _ in range(count):
        command,length=unpack_from('<II',blob,p)
        if command!=0x1d:commands.append(blob[p:p+length])
        p+=length
    header=b''.join(commands)
    image[32:32+size]=header+bytes(size-len(header))
    pack_into('<II',image,16,len(commands),len(header))
    return bytes(image)


def assemble(source,retained,target):
    from copy import copy
    import json,plistlib
    from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
    source,retained,target=map(Path,(source,retained,target))
    assert sha256(source.read_bytes()).hexdigest()=='1fc2febe2519732728cc5e3ef58ff30839fe7f542883277a1ac55d22abbf67f5'
    app='Payload/Army2Hoanggia.app/';fw=app+'Frameworks/';replaced={}
    with ZipFile(source)as base,ZipFile(retained)as retained:
        manifest=json.loads(retained.read('framework-sha256.json'))
        for name,digest in manifest.items():
            data=retained.read(name) if name in retained.namelist() else base.read(fw+name)
            assert sha256(data).hexdigest()==digest,name
            replaced[fw+name]=data
        raw=replaced[fw+'AGWheel.framework/AGWheel']
        assert b'_AGNativeWatchPacket\0' in raw and b'_AGSceneHook\0' in raw
        assert raw[:8]==bytes.fromhex('cffaedfe0c000001')
        replaced[fw+'AGWheel.framework/AGWheel']=strip_signature(raw)
        info=plistlib.loads(base.read(app+'Info.plist'));assert info['CFBundleVersion']=='280'
        info['CFBundleVersion']='281';replaced[app+'Info.plist']=plistlib.dumps(info,fmt=plistlib.FMT_BINARY)
        old=base.read(app+'Army2Hoanggia');replaced[app+'Army2Hoanggia']=patch(old)
        # No original byte outside the six row calls and their new shims changes.
        allowed=set()
        for v,site in enumerate(SITES):
            allowed.update(range(site,site+4));a=FILE+0x1000+v*32;allowed.update(range(a,a+20))
        assert all(i in allowed for i,(a,b)in enumerate(zip(old,replaced[app+'Army2Hoanggia']))if a!=b)
        target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
        with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=6)as out:
            for entry in base.infolist():
                name=entry.filename
                if '/_CodeSignature/' in name or name.endswith('embedded.mobileprovision') or name.startswith(fw+'AGWheel.framework/'):continue
                out.writestr(copy(entry),replaced.pop(name) if name in replaced else base.read(name))
            for name,data in replaced.items():
                if '/_CodeSignature/' in name:continue
                entry=ZipInfo(name);entry.create_system=3;entry.external_attr=(0o100755 if name.endswith('/AGWheel') else 0o100644)<<16;entry.compress_type=ZIP_DEFLATED
                out.writestr(entry,data)
    with ZipFile(target)as z,ZipFile(source)as base:
        assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))
        assert plistlib.loads(z.read(app+'Info.plist'))['CFBundleVersion']=='281'
        for name in z.namelist():
            if name not in (app+'Info.plist',app+'Army2Hoanggia') and not name.startswith(fw+'AGWheel.framework/'):
                assert z.read(name)==base.read(name),name
        for name in (app+'Army2Hoanggia',fw+'AGWheel.framework/AGWheel'):
            b=z.read(name);n=unpack_from('<I',b,16)[0];p=32
            for _ in range(n):
                command,size=unpack_from('<II',b,p);assert command!=0x1d
                if command==0x2c:assert unpack_from('<I',b,p+16)[0]==0
                p+=size
    print('Verified B281 IPA',target,sha256(target.read_bytes()).hexdigest())
