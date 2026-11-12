"""Assemble a new unsigned QA IPA around the verified build-269 executable."""
import argparse
import copy
import hashlib
import os
from pathlib import Path, PurePosixPath
import plistlib
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED
from patch_menu_269 import patch_menu
from patch_boss_maps import patch_boss_maps, MARKER
from boss_assets import boss_assets

BASE_SHA = "cde926d904e076e428b6d3c911ed673f0b80fc10b8e4a5134cb44d5a2d809ee8"
APP = "Payload/Army2Hoanggia.app/"
FW = "AGWheel.framework/"
INFO = APP + "Info.plist"
NATIVE = APP + "Army2Hoanggia"
PREFIX = APP + "Frameworks/"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def assemble(base, framework, target, version, boss_client=None, boss_server=None):
    if target.exists() or version <= 269:
        raise ValueError("Choose a new output and a build number above 269")
    if digest(base) != BASE_SHA:
        raise ValueError("Unexpected baseline IPA")
    if version != 275 or boss_client is None or boss_server is None:
        raise ValueError("Build 275 requires the matching client and server JARs")
    maps = {APP + "BossMaps/" + name: data for name, data in boss_assets(boss_client, boss_server).items()}
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp, ZipFile(base) as old, ZipFile(framework) as lib:
        if len(lib.namelist()) != len(set(lib.namelist())) or lib.testzip():
            raise ValueError("Invalid framework archive")
        for entry in lib.infolist():
            path=PurePosixPath(entry.filename)
            if (not entry.filename.startswith(FW) or ".." in path.parts or chr(92) in entry.filename or
                    (entry.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("Invalid framework entry")
        required = {"AGWheel","Info.plist","_CodeSignature/CodeResources","viewer/index.html","viewer/screen.js","viewer/protocol.js","viewer/lobby.html","viewer/lobby.js"}
        paths = {p[len(FW):] for p in lib.namelist()}
        if not required.issubset(paths) or lib.read(FW+"AGWheel")==old.read(PREFIX+FW+"AGWheel"):
            raise ValueError("Incomplete or unchanged framework")
        fw_info=plistlib.loads(lib.read(FW+"Info.plist"))
        if fw_info != plistlib.loads(old.read(PREFIX+FW+"Info.plist")):
            raise ValueError("Framework identity changed")
        info=plistlib.loads(old.read(INFO))
        if (info["CFBundleIdentifier"],info["CFBundleVersion"]) != ("vn.army2hoanggia.game","269"):
            raise ValueError("Unexpected application identity")
        info["CFBundleVersion"]=str(version)
        native=patch_boss_maps(patch_menu(old.read(NATIVE)))
        framework_code=lib.read(FW+'AGWheel')
        if any(symbol not in framework_code for symbol in (b'_AGLobbyOpenNative\0',
                b'_AGAuraPaintActor\0', b'_AGBossNativeHook\0', MARKER + b'\0')):
            raise ValueError('Missing native menu or boss map callback')
        staged=Path(tmp)/"app.ipa"
        with ZipFile(staged,"w") as out:
            for e in old.infolist():
                if e.filename.startswith(PREFIX+FW): continue
                data=plistlib.dumps(info,fmt=plistlib.FMT_BINARY) if e.filename==INFO else native if e.filename==NATIVE else old.read(e)
                out.writestr(copy.copy(e),data)
            for e in lib.infolist():
                member=copy.copy(e);member.filename=PREFIX+e.filename
                out.writestr(member,lib.read(e))
            for name, data in maps.items():
                out.writestr(name, data, compress_type=ZIP_DEFLATED)
        with ZipFile(staged) as check:
            wanted={p for p in old.namelist() if not p.startswith(PREFIX+FW)}|{PREFIX+p for p in lib.namelist()}|maps.keys()
            if set(check.namelist())!=wanted or len(check.namelist())!=len(wanted) or check.testzip():
                raise ValueError("Incomplete QA IPA")
            for p in old.namelist():
                if p not in (INFO,NATIVE) and not p.startswith(PREFIX+FW) and old.read(p)!=check.read(p):
                    raise ValueError("Unexpected application change: "+p)
            if check.read(NATIVE)!=native:raise ValueError('Native menu patch missing')
            for p in lib.namelist():
                if lib.read(p)!=check.read(PREFIX+p):raise ValueError("Framework was modified after signing")
            for name, data in maps.items():
                if data != check.read(name): raise ValueError("Changed boss resource: " + name)
            if plistlib.loads(check.read(INFO))!=info:raise ValueError("Unexpected build metadata")
        # Publish only a fully checked file, without replacing a concurrent build.
        os.link(staged,target)
    print("Unsigned QA IPA",target.name,digest(target))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("baseline","framework","output"):parser.add_argument(name,type=Path)
    parser.add_argument("--build",type=int,required=True)
    parser.add_argument("--boss-client",type=Path,required=True)
    parser.add_argument("--boss-server",type=Path,required=True)
    args=parser.parse_args()
    assemble(args.baseline,args.framework,args.output,args.build,args.boss_client,args.boss_server)
