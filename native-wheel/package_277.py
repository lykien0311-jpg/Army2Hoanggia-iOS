"""Assemble the iOS 2.4.1 build 277 QA IPA from the verified build 275."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
from struct import pack, unpack_from
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from patch_menu_269 import RX_FILE, RX_VM, branch, near


BASE_SHA = '0ba3ff8e8492511638fb68f1b09af1ed558b69f7b45e3547e6dc61519471180f'
FRAMEWORK_276_SHA = '9d300dca332e3c84cac4a90af658cd7a2c42008f8410683b4c6da6e40fdc856b'
APP = 'Payload/Army2Hoanggia.app/'
INFO = APP + 'Info.plist'
NATIVE = APP + 'Army2Hoanggia'
FW = 'AGWheel.framework/'
EMBEDDED_FW = APP + 'Frameworks/' + FW


def patch_menu_return(native):
    result = bytearray(native)

    def edit(file, before, after):
        expected = pack('<I', before)
        if native[file:file + 4] != expected:
            raise ValueError(f'Unexpected menu instruction at {file:#x}')
        result[file:file + 4] = pack('<I', after)

    def code(pc, before, after):
        edit(RX_FILE + pc - RX_VM, before, after)

    select = 0x24ffb90
    fallback = select + 0x80
    rank = 0x24ff7c4
    invoke = select + 0x3c
    # Only intercept row 3 of the existing rank submenu (depth 2, category
    # stored in Home's Xem thông tin field). The login response fills its
    # four labels, including BXH SỰ KIỆN, in the same order as the APK.
    rank_words = (
        0x7100093f, near(rank + 4, fallback, 0x54000001),  # cmp w9,#2; b.ne
        0xb940dd10, 0x39c39911, 0x6b11021f,              # category, rank parent; cmp
        near(rank + 20, fallback, 0x54000001),
        0xb94062d1, 0x71000e3f,                           # selected row == 3
        near(rank + 32, fallback, 0x54000001),
        branch(rank + 36, invoke),                        # w17=3 (event)
    )
    for i, word in enumerate(rank_words):
        code(rank + i * 4, 0, word)

    code(select + 4, near(select + 4, select + 0x7c, 0x54000001), near(select + 4, rank, 0x54000001))
    for offset, opcode in ((0x1c, 0x54000001), (0x24, 0x54000001), (0x30, 0x35000011)):
        pc = select + offset
        code(pc, near(pc, select + 0x7c, opcode), near(pc, fallback, opcode))
    # Resume the original menu cleanup with the current submenu selected.
    # Its action flag otherwise stays armed and invokes the row again.
    code(select + 0x78, 0x910011ce, 0x39027edf)  # strb wzr,[x22,#159]
    code(select + 0x7c, 0xd61f01c0, 0x910011ce)  # add x14,x14,#4
    code(fallback, 0, 0xd61f01c0)                # br x14

    maps = json.loads(Path(__file__).with_name('native-map.json').read_text())
    for variant, entry in enumerate(maps):
        pc = select + 0x90 + variant * 28 + 24
        cleanup = entry['home_after_action']
        code(pc, branch(pc, cleanup + 0x28), branch(pc, cleanup))
        if unpack_from('<I', result, cleanup + 0x10)[0] != 0x3902711f:
            raise ValueError('Native menu cleanup moved')
    return bytes(result)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def framework_files(archive):
    result = {}
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if (not info.filename.startswith(FW) or '..' in path.parts or '\\' in info.filename
                or ((info.external_attr >> 16) & 0o170000) == 0o120000):
            raise ValueError('Unexpected framework member')
        if info.is_dir():
            continue
        if info.filename in result:
            raise ValueError('Duplicate framework member')
        result[info.filename] = archive.read(info)
    return result


def read_framework(archive, retained_base):
    with ZipFile(archive) as package:
        if 'framework-sha256.json' not in package.namelist():
            return framework_files(package)
        if retained_base is None or digest(retained_base) != FRAMEWORK_276_SHA:
            raise ValueError('The retained build requires the verified 276 framework resources')
        manifest = json.loads(package.read('framework-sha256.json'))
        with ZipFile(retained_base) as old:
            files = framework_files(old)
        for name in package.namelist():
            if name.startswith(FW) and not name.endswith('/'):
                files[name] = package.read(name)
        files = {name: files[name] for name in manifest}
        if any(sha256(data).hexdigest() != manifest[name] for name, data in files.items()):
            raise ValueError('Restored framework differs from the macOS build')
        return files


def assemble(base, framework, target, retained_base=None):
    if target.exists() or digest(base) != BASE_SHA:
        raise ValueError('Use the exact build 275 and a new output path')
    replacement = read_framework(framework, retained_base)
    framework_code = replacement[FW + 'AGWheel']
    for symbol in (b'_AGLobbyOpenNative', b'_AGAuraPaintActor', b'_AGBossNativeHook', b'2.4.1-B275-IPA'):
        if symbol + b'\0' not in framework_code:
            raise ValueError('Missing native framework hook')
    resources = plistlib.loads(replacement[FW + '_CodeSignature/CodeResources'])
    for name, data in replacement.items():
        if name.startswith(FW + 'viewer/'):
            record = resources['files2'][name.removeprefix(FW)]
            if sha256(data).digest() != record['hash2']:
                raise ValueError('Viewer file differs from signed resources')

    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(base) as original, TemporaryDirectory(dir=target.parent) as tmp:
        info = plistlib.loads(original.read(INFO))
        if (info['CFBundleIdentifier'], info['CFBundleVersion']) != ('vn.army2hoanggia.game', '275'):
            raise ValueError('Unexpected application identity')
        info['CFBundleVersion'] = '277'
        if plistlib.loads(replacement[FW + 'Info.plist']) != plistlib.loads(original.read(EMBEDDED_FW + 'Info.plist')):
            raise ValueError('Framework identity changed')
        changed = {INFO: plistlib.dumps(info, fmt=plistlib.FMT_BINARY),
                   NATIVE: patch_menu_return(original.read(NATIVE))}
        staged = Path(tmp) / 'Army2.ipa'
        with ZipFile(staged, 'w', compression=8, compresslevel=6) as output:
            for entry in original.infolist():
                if not entry.filename.startswith(EMBEDDED_FW):
                    output.writestr(entry, changed.get(entry.filename) or original.read(entry))
            for name, data in replacement.items():
                output.writestr(APP + 'Frameworks/' + name, data)
        with ZipFile(staged) as check:
            expected = {n for n in original.namelist() if not n.startswith(EMBEDDED_FW)}
            expected.update(APP + 'Frameworks/' + name for name in replacement)
            if set(check.namelist()) != expected or len(check.namelist()) != len(expected) or check.testzip():
                raise ValueError('Incomplete IPA')
            for name in expected:
                if name in changed:
                    want = changed[name]
                elif name.startswith(EMBEDDED_FW):
                    want = replacement[name.removeprefix(APP + 'Frameworks/')]
                else:
                    want = original.read(name)
                if check.read(name) != want:
                    raise ValueError(f'Unexpected file content at {name}')
        os.link(staged, target)
    print(f'Unsigned QA IPA {target.name} {digest(target)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'framework', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--framework-276', type=Path)
    args = parser.parse_args()
    assemble(args.baseline, args.framework, args.output, args.framework_276)
