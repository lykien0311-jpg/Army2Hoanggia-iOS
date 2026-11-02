"""Package the exact Apple-built dylib into the checksum-guarded user IPA."""
from pathlib import Path
import argparse,base64,hashlib,json,struct,zipfile,zlib,plistlib
from patch_ipa import build_native,commands

ROOT=Path(__file__).resolve().parent
APP='Payload/Army2Hoanggia.app/'
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ipa',type=Path,required=True)
    p.add_argument('--dylib',type=Path,default=ROOT/'build/AGWheel.dylib')
    p.add_argument('--build-info',type=Path,default=ROOT/'build/build-info.json')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bundle-build',default='251')
    args=p.parse_args()
    r=json.loads((ROOT/'baseline-recovery.json').read_text())
    with zipfile.ZipFile(args.ipa) as src:native=src.read(APP+'Army2Hoanggia')
    identity=sha(native)
    extra=r.get('additional_natives',{}).get(identity)
    assert identity in (r['main_sha256'],r['updated_main_sha256']) or extra,'Use an untouched supported IPA, before re-signing'
    if identity==r['main_sha256']:assert sha(args.ipa.read_bytes())==r['ipa_sha256'],'Original baseline archive differs'
    recovery=json.loads(zlib.decompress(base64.b64decode(extra['hooks_zlib_base64']))) if extra else r if identity==r['main_sha256'] else r['updated_hooks']
    old=bytearray(native)
    for c in recovery['patches']:
        a=c['offset'];after=bytes.fromhex(c['after']);assert old[a:a+len(after)]==after
        old[a:a+len(after)]=bytes.fromhex(c['before'])
    del old[recovery['rxoff']:recovery['rxoff']+recovery['linkedit_shift']]
    old[:0x8000]=zlib.decompress(base64.b64decode(r['header_zlib_base64']))
    assert sha(old)==r['prewheel_sha256']
    original=bytearray(old)
    for c in r['original_delta']:
        b=bytes.fromhex(c['bytes']);original[c['offset']:c['offset']+len(b)]=b
    assert sha(original)==r['original_sha256']
    build=ROOT/'build';build.mkdir(exist_ok=True)
    fixtures=ROOT.parent/'validation'
    (fixtures/'inspect-ipa').mkdir(parents=True,exist_ok=True)
    (fixtures/'review').mkdir(parents=True,exist_ok=True)
    (fixtures/'inspect-ipa/Army2Hoanggia').write_bytes(original)
    (fixtures/'review/patched-native').write_bytes(old)
    patched,hooks=build_native(bytes(old),bytes(original),json.loads((ROOT/'native-map.json').read_text()))
    (build/'prepared-native').write_bytes(patched)
    (build/'hook-report.json').write_text(json.dumps(hooks,indent=2)+'\n')
    info=json.loads(args.build_info.read_text());lib=args.dylib.read_bytes()
    assert info['release_version']=='2.4.1' and info['login_marker']=='2.4.1-HG78-IPA'
    assert info['apple_codesign_strict_verified'] and info['apple_resign_strict_verified']
    assert sha(lib)==info['dylib_sha256'],'Dylib differs from verified GitHub output'
    assert struct.unpack_from('<I',lib)[0]==0xfeedfacf
    assert struct.unpack_from('<I',lib,4)[0]==0x100000c
    assert struct.unpack_from('<I',lib,12)[0]==6
    lc=list(commands(lib))
    versions=[struct.unpack_from('<II',lib,p+8) for p,c,s in lc if c==0x32]
    assert versions and all(platform==2 and minimum<=0xc0000 for platform,minimum in versions)
    signatures=[struct.unpack_from('<II',lib,p+8) for p,c,s in lc if c==0x1d]
    assert len(signatures)==1 and all(v>0 for v in signatures[0])
    assert signatures[0][0]+signatures[0][1]<=len(lib)
    assert b'_AGWheelPreview' not in lib
    for name in ('AGWheelOpen','AGWheelTick','AGWheelReceive','AGRoomReceive','AGRoomRebuild','AGMoveAllow','AGCameraAllow','AGBlindPaint','AGBlindReceive','AGNotesReceive','AGNotesInput','AGNotesSettings','AGNotesInbox','AGGridAdjust','AGWheelSuppressFooter','AGTurnReceive','AGTurnManual','AGTurnPulse','AGTurnChange','AGTurnAwait','AGBattleAwait','AGViewportKeypad'):
        assert ('_'+name+'\0').encode() in lib,name
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.ipa) as src,zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
        for zi in src.infolist():
            assert '/_CodeSignature/' not in zi.filename and not zi.filename.endswith('embedded.mobileprovision')
            data=patched if zi.filename==APP+'Army2Hoanggia' else lib if zi.filename==APP+'Frameworks/AGWheel.dylib' else src.read(zi.filename)
            if zi.filename==APP+'Info.plist':
                plist=plistlib.loads(data)
                assert plist['CFBundleShortVersionString'] in ('2.4.0','2.4.1')
                plist['CFBundleShortVersionString']='2.4.1';plist['CFBundleVersion']=args.bundle_build
                plist['UIFileSharingEnabled']=True;plist['LSSupportsOpeningDocumentsInPlace']=True
                data=plistlib.dumps(plist,fmt=plistlib.FMT_BINARY,sort_keys=False)
            dst.writestr(zi,data)
    with zipfile.ZipFile(args.ipa) as src,zipfile.ZipFile(args.output) as dst:
        assert dst.testzip() is None
        assert src.namelist()==dst.namelist()
        changed=[n for n in src.namelist() if src.read(n)!=dst.read(n)]
        assert set(changed)<={APP+'Army2Hoanggia',APP+'Frameworks/AGWheel.dylib',APP+'Info.plist'}
        if identity==r['main_sha256']:assert APP+'Army2Hoanggia' in changed
        assert dst.read(APP+'Frameworks/AGWheel.dylib')==lib
    report={'passed':True,'input_sha256':sha(args.ipa.read_bytes()),'output':args.output.name,'sha256':sha(args.output.read_bytes()),'bytes':args.output.stat().st_size,'changed_entries':changed,'other_entries_unchanged':len(src.namelist())-len(changed),'github_build':info,'physical_device_tested':False,'requires_user_certificate_resigning':True}
    (build/'package-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()


