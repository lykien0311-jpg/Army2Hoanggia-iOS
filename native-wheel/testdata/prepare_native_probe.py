from base64 import b64decode
from pathlib import Path
from struct import pack
from sys import argv
from zipfile import ZipFile
import plistlib
import zlib

from patch_boss_maps import patch_boss_maps
from patch_menu_269 import patch_menu

archive, framework, output = map(Path, argv[1:])
with ZipFile(archive) as base:
    base.extractall(output)
app = output / "Payload/Army2Hoanggia.app"
exe = app / "Army2Hoanggia"
exe.write_bytes(patch_boss_maps(patch_menu(exe.read_bytes())))
(app / "Frameworks/AGWheel.framework/AGWheel").write_bytes(framework.read_bytes())

for info in [app / "Info.plist", *app.glob("Frameworks/*.framework/Info.plist")]:
    plist = plistlib.loads(info.read_bytes())
    plist["CFBundleSupportedPlatforms"] = ["iPhoneSimulator"]
    plist["DTPlatformName"] = "iphonesimulator"
    plist["DTSDKName"] = "iphonesimulator18.5"
    info.write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_BINARY))

def chunk(tag, content):
    return pack(">I", len(content)) + tag + content + pack(">I", zlib.crc32(tag + content))

def png():
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", pack(">IIBBBBB", 8, 8, 8, 6, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress((b"\0" + b"\x99\x88\x77\xff" * 8) * 8)) + chunk(b"IEND", b"")

data = [
    (41, "dragon105", "BGADSBRaAIwBLFsBXgEYXAJ2ASRdAzQBNl4AAAGpXwCgAdZgATYBs2EB/gHWYgLQAcdjA+gBrmQAKAImZQEOAitmArwCNWcDwAImaAAAArJpANICxmoBmgKKawJ2ArxsAz4CqG0EEAK8CADSATcBGAE4AZABJQHWASUCqAEwAu4BMANIAUMDjgFD",
     ["background.png", "fire-226.png", "fire-100.png", "ice-226.png", "ice-100.png", "egg-0.png", "egg-1.png"]),
    (42, "mimic111", "A8ACMApaADYAolsC9ACiXAC+APRdAmwA9F4AKgFmXwL+AWZgANsBsGECTgGwYgGJAUBmAAACGAgAfgCiA0IAogEHAPQCuQD0AG8BZgNRAWYBJAGwApwBsA==",
     ["background.png", "boss.png"]),
]
for index, key, encoded, art in data:
    root = app / "BossMaps" / key
    root.mkdir(parents=True)
    layout = b64decode(encoded)
    (root / f"{index}.map").write_bytes(layout)
    for name in [*art, *(f"tile-{tile}.png" for tile in layout[5:5 + 5 * layout[4]:5])]:
        (root / name).write_bytes(png())
