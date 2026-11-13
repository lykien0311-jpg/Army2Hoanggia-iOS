"""Build the Army2 iOS 278 QA IPA from the verified build 277."""

import argparse
from copy import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import plistlib
from struct import pack, pack_into, unpack_from
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from package_277 import APP, EMBEDDED_FW, FW, INFO, NATIVE, digest, framework_files
from patch_menu_269 import DLSYM, RX_FILE, RX_VM, add, address, branch, mov, near


BASE = 'a84275ac535e73bf61a0c49be6ed01094717eccea4751947ffb96d789d3b0a79'
EXECUTABLE = '79400cc464862c6eb62f5ed8537fac0c46ce7b4d81de0657c69cc7c58a0deb66'
ASSETS = {
    'dragon105/preview-map.png': '69bfd3329ac1614dc62176381c76fc610baec67b07cddeeba67b9c4f0bc12fcb',
    'dragon105/fire-160.png': 'f1f6677b22f49382e2bff8cc50c9c9e553c38aaebab5326a90fbda2e284c36b5',
    'dragon105/ice-160.png': 'a767ab83819e26dcb1d472e438e4668785d3e451af3f75b58e1735bf7be69531',
    'mimic111/minimap.png': 'd997577ec1e01f3809a703623d2c7aa7168602c4e52c41bae352f458cfac321c',
}
MACH_BASE = 0x100000000
SCENE_VM, SCENE_FILE, PAGE = 0x2508000, 0x24c8000, 0x4000
SCENE_SYMBOL = SCENE_VM + 0xf0
SCENE_CACHE = 0x2500208
MENU_OPEN = 0x24ffbcc
FIELD_LABEL = 0x24ffb20
ARRAY_SET = 0x12e7f74


def opcode(data, offset):
    return unpack_from('<I', data, offset)[0]


def called(data, offset, vm=None):
    word = opcode(data, offset)
    if word >> 26 != 0b100101:
        raise ValueError(f'Expected a native call at {offset:#x}')
    distance = (word & 0x3ffffff) - ((word & 0x2000000) << 1)
    return (offset if vm is None else vm) + distance * 4


def ldr(destination, register, offset):
    assert offset % 8 == 0
    return 0xf9400000 | (offset // 8 << 10) | (register << 5) | destination


def stp(first, second, offset, load=False):
    assert offset % 8 == 0
    return (0xa9400000 if load else 0xa9000000) | (offset // 8 << 15) | (second << 10) | (31 << 5) | first


def add_scene_segment(original):
    image = bytearray(original[:SCENE_FILE] + bytes(PAGE) + original[SCENE_FILE:])
    count, size = unpack_from('<II', original, 16)
    offsets = {2: (8, 16), 0xb: (32, 40, 48, 56, 64, 72),
               0x80000022: (8, 16, 24, 32, 40), 0x26: (8,), 0x29: (8,)}
    cursor, linkedit = 32, None
    for _ in range(count):
        command, length = unpack_from('<II', original, cursor)
        if command == 0x19 and original[cursor + 8:cursor + 18] == b'__LINKEDIT':
            assert length == 72
            assert unpack_from('<Q', original, cursor + 24)[0] == MACH_BASE + SCENE_VM
            assert unpack_from('<Q', original, cursor + 40)[0] == SCENE_FILE
            linkedit = cursor
        for offset in offsets.get(command, ()):
            value = opcode(original, cursor + offset)
            if value:
                assert value >= SCENE_FILE
                pack_into('<I', image, cursor + offset, value + PAGE)
        cursor += length
    assert linkedit is not None and cursor == 32 + size
    assert original[cursor:cursor + 152] == bytes(152)
    last = bytearray(image[linkedit:linkedit + 72])
    pack_into('<Q', last, 24, MACH_BASE + SCENE_VM + PAGE)
    pack_into('<Q', last, 40, SCENE_FILE + PAGE)
    scene = pack('<II16sQQQQiiII', 0x19, 152, b'__AGSCENE',
                 MACH_BASE + SCENE_VM, PAGE, SCENE_FILE, PAGE, 5, 5, 1, 0)
    scene += pack('<16s16sQQIIIIIIII', b'__text', b'__AGSCENE',
                  MACH_BASE + SCENE_VM, PAGE, SCENE_FILE, 2, 0, 0, 0x80000400, 0, 0, 0)
    # Insert before __LINKEDIT, shifting its index only. It has no rebases,
    # binds or sections. Existing text, data and resource sections keep their indices.
    image[linkedit:cursor + 152] = scene + last + image[linkedit + 72:cursor]
    pack_into('<II', image, 16, count + 1, size + 152)
    return image


def patch_scene(original):
    if sha256(original).hexdigest() != EXECUTABLE:
        raise ValueError('Use the original build 277 executable')
    image = add_scene_segment(original)
    cursor = SCENE_VM + 0x100

    def emit(at, words):
        file = SCENE_FILE + at - SCENE_VM
        assert SCENE_VM <= at < SCENE_VM + PAGE - 4 * len(words)
        assert image[file:file + 4 * len(words)] == bytes(4 * len(words))
        pack_into(f'<{len(words)}I', image, file, *words)

    def hook(site, shim, link=False):
        pack_into('<I', image, site, branch(site, shim, link))

    def allocate(words):
        nonlocal cursor
        at = cursor
        cursor += 4 * words
        return at

    assert original[0x24c0208:0x24c0210] == bytes(8)
    label = b'AGSceneHook\0'
    image[SCENE_FILE + 0xf0:SCENE_FILE + 0xf0 + len(label)] = label
    # Eleven integer/pointer args use x0-x7 followed by x8-x10's saved values.
    # The original callback and the Java Env are available even without the dylib.
    emit(SCENE_VM, [
        0xd101c3ff, stp(29, 30, 96), 0x910183fd,  # sub sp, #112; save frame
        stp(8, 9, 0), stp(10, 31, 16),
        stp(0, 1, 32), stp(2, 3, 48), stp(4, 5, 64), stp(6, 7, 80),
        address(SCENE_VM + 36, SCENE_CACHE, 11, page=True), ldr(16, 11, SCENE_CACHE & 0xfff),
        near(SCENE_VM + 44, SCENE_VM + 76, 0xb5000010),  # cbnz x16
        0x92800020, address(SCENE_VM + 52, SCENE_SYMBOL, 1),
        branch(SCENE_VM + 56, DLSYM, True), 0xaa0003f0,
        address(SCENE_VM + 64, SCENE_CACHE, 11, page=True),
        0xf9000000 | ((SCENE_CACHE & 0xfff) // 8 << 10) | (11 << 5) | 16,
        0xd503201f,
        stp(0, 1, 32, True), stp(2, 3, 48, True), stp(4, 5, 64, True), stp(6, 7, 80, True),
        near(SCENE_VM + 92, SCENE_VM + 112, 0xb4000010),  # cbz x16
        0xd63f0200, stp(29, 30, 96, True), 0x9101c3ff, 0xd65f03c0,
        ldr(9, 31, 8), stp(29, 30, 96, True), 0x9101c3ff, 0xd61f0120,
    ])

    def paint(site, variant, operation, target, data=None, stack=None):
        at = allocate(6 if data is not None else 5)
        words = [mov(8, variant * 16 + operation),
                 address(at + 4, target, 9, page=True), add(9, target & 0xfff)]
        if data is not None:
            words.extend((address(at + 12, data, 10, page=True), add(10, data & 0xfff)))
        else:
            words.append(ldr(10, 31, stack) if stack is not None else mov(10, 0))
        words.append(branch(at + len(words) * 4, SCENE_VM))
        emit(at, words)
        hook(site, at, link=True)

    root = Path(__file__).parent
    home = json.loads((root / 'native-map.json').read_text())
    rooms = json.loads((root / 'presentation-map.json').read_text())
    for v, (menu, room) in enumerate(zip(home, rooms, strict=True)):
        paint_start = room['room_paint']
        reset = paint_start + 0x84
        assert opcode(original, reset - 4) == 0xaa1303e0
        names = called(original, paint_start + 0x338c)
        assert opcode(original, names + 0x2c) == 0xf9405100
        assert opcode(original, names + 0x6c) == 0xf9005113
        paint(reset, v, 0, called(original, reset), data=names)
        site = room['boss_call']
        boss = called(original, site)
        assert RX_VM <= boss < RX_VM + 0x8000
        paint(site, v, 1, boss)

        # Sảnh and Trang bị draw the local player. Both R5 paint paths
        # carry the individual room player in a known frame slot.
        renderer = room['boss_renderer']
        lobby = menu['home_build'] + (0xdd8 if v else 0xec8)
        equipment = renderer + (0x171c4 if v else 0x17cdc)
        for site, stack in ((lobby, None), (equipment, None),
                            (paint_start + 0x1620, 528), (paint_start + 0x2138, 696)):
            assert called(original, site) == renderer
            paint(site, v, 2 if stack is None else 3, renderer, stack=stack)

        # Both native soft keys and touch converge here for Chơi ngay's
        # first row. Skip command 28 only for this row and exit native
        # confirmation through its existing cleanup.
        site = menu['home_select'] - 0x94
        assert opcode(original, site) == 0xb94062c8 and opcode(original, site + 4) == 0x32081fe9
        assert opcode(original, menu['home_after_action'] + 0x10) == 0x3902711f
        at = allocate(8)
        emit(at, [
            0xb94062c8, near(at + 4, at + 24, 0x35000008),
            mov(13, v), address(at + 12, at + 24, 14), mov(17, 1),
            branch(at + 20, MENU_OPEN),
            branch(at + 24, site + 4), branch(at + 28, menu['home_after_action']),
        ])
        hook(site, at)

        # Use the existing localized title in Chơi ngay's category-0 array.
        site = menu['home_build'] + 0x1d8
        assert called(original, site) == ARRAY_SET
        assert opcode(original, site - 0x10) == 0x2a1f03e2
        at = allocate(9)
        emit(at, [
            0xa9be7bfd, 0x910003fd, stp(0, 1, 16),
            branch(at + 12, FIELD_LABEL, True),
            0xaa0003e3, stp(0, 1, 16, True), mov(2, 0),
            0xa8c27bfd, branch(at + 32, ARRAY_SET),
        ])
        hook(site, at, link=True)

    # The seven-row menu is also entered from the alternate layout, with
    # category 6 at depth 2. That route uses the same first-row action.
    rank = 0x24ff7c4
    rank_file = RX_FILE + rank - RX_VM
    assert opcode(original, rank_file) == 0x7100093f
    at = allocate(11)
    emit(at, [
        0x7100093f, near(at + 4, at + 36, 0x54000001),  # depth == 2
        0xb940dd10, 0x71001a1f, near(at + 16, at + 36, 0x54000001),  # category 6
        0xb94062d1, near(at + 24, at + 36, 0x35000011),  # first row
        mov(17, 1), branch(at + 32, MENU_OPEN),
        0x7100093f, branch(at + 40, rank + 4),  # reestablish depth flags for the event rank
    ])
    pack_into('<I', image, rank_file, branch(rank, at))
    return bytes(image)


def restored_framework(framework, original):
    with ZipFile(framework) as package:
        if 'framework-sha256.json' not in package.namelist():
            return framework_files(package)
        manifest = json.loads(package.read('framework-sha256.json'))
        files = {name.removeprefix(APP + 'Frameworks/'): original.read(name)
                 for name in original.namelist() if name.startswith(EMBEDDED_FW) and not name.endswith('/')}
        files.update({name: package.read(name) for name in package.namelist() if name.startswith(FW)})
        if any(sha256(files[name]).hexdigest() != value for name, value in manifest.items()):
            raise ValueError('Restored framework differs from the macOS build')
        return {name: files[name] for name in manifest}


def assemble(base, framework, art, target):
    if target.exists() or digest(base) != BASE:
        raise ValueError('Use the exact build 277 and a new output path')
    with ZipFile(base) as original, TemporaryDirectory(dir=target.parent) as tmp:
        info = plistlib.loads(original.read(INFO))
        assert (info['CFBundleIdentifier'], info['CFBundleVersion']) == ('vn.army2hoanggia.game', '277')
        info['CFBundleVersion'] = '278'
        replacement = restored_framework(framework, original)
        resources = plistlib.loads(replacement[FW + '_CodeSignature/CodeResources'])
        for name, data in replacement.items():
            if name.startswith(FW + 'viewer/'):
                assert sha256(data).digest() == resources['files2'][name.removeprefix(FW)]['hash2']
        assert plistlib.loads(replacement[FW + 'Info.plist']) == plistlib.loads(original.read(EMBEDDED_FW + 'Info.plist'))
        assert b'_AGSceneHook\0' in replacement[FW + 'AGWheel']
        changed = {INFO: plistlib.dumps(info, fmt=plistlib.FMT_BINARY),
                   NATIVE: patch_scene(original.read(NATIVE))}
        for path, expected in ASSETS.items():
            name = APP + 'BossMaps/' + path
            data = (art / path).read_bytes()
            assert sha256(data).hexdigest() == expected
            changed[name] = data
        staged = Path(tmp) / 'Army2.ipa'
        with ZipFile(staged, 'w', compression=ZIP_DEFLATED, compresslevel=6) as output:
            for entry in original.infolist():
                name = entry.filename
                if not name.startswith(EMBEDDED_FW):
                    output.writestr(copy(entry), changed.pop(name) if name in changed else original.read(entry))
            for name, data in changed.items():
                output.writestr(name, data)
            for name, data in replacement.items():
                output.writestr(APP + 'Frameworks/' + name, data)
        with ZipFile(staged) as check:
            assert check.testzip() is None and len(check.namelist()) == len(set(check.namelist()))
            assert plistlib.loads(check.read(INFO))['CFBundleVersion'] == '278'
            for path, expected in ASSETS.items():
                assert sha256(check.read(APP + 'BossMaps/' + path)).hexdigest() == expected
        os.link(staged, target)
    print(digest(target), target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('framework', type=Path)
    parser.add_argument('art', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    assemble(args.base, args.framework, args.art, args.output)
