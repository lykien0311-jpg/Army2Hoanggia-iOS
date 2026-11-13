"""Execute packaged ARM64 menu/scene hooks and the Apple-built AGSceneHook.

UIKit presentation, Java allocation/array access, the JVM exception guard, OS
services and final image draws are controlled boundaries. Aura packet parsing,
per-player lookup, native call sites, trampolines and compiled scene selection
execute from the delivered IPA. No live server or physical iPhone is used.
"""
import argparse
import ctypes
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import lief
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *

from package_278 import APP, EMBEDDED_FW, NATIVE, SCENE_CACHE, called

ROOT = Path(__file__).parent
MAIN, LIB, FAKE, HEAP, STACK = 0x100000000, 0x200000000, 0x400000000, 0x600000000, 0x700000000
STOP, GUARD_RETURN = FAKE + 0x30000, FAKE + 0x30100
SP = STACK + 0x30000
X = [getattr(__import__('unicorn.arm64_const', fromlist=['']), f'UC_ARM64_REG_X{i}') for i in range(31)]


class AuraRow(ctypes.Structure):
    _fields_ = [('serial', ctypes.c_uint64), ('id', ctypes.c_uint32),
                ('hero', ctypes.c_uint8), ('tier', ctypes.c_uint8), ('level', ctypes.c_uint8)]


class AuraState(ctypes.Structure):
    _fields_ = [('connection', ctypes.c_uint64), ('epoch', ctypes.c_uint64),
                ('scene', ctypes.c_uint64), ('serial', ctypes.c_uint64),
                ('peer', ctypes.c_uint32), ('count', ctypes.c_uint64),
                ('globalRows', AuraRow * 8192), ('roster', AuraRow * 128)]


def test(ipa):
    archive = ZipFile(ipa)
    raw = archive.read(NATIVE)
    library = archive.read(EMBEDDED_FW + 'AGWheel')
    # Keep the owning LIEF FatBinary objects alive while using their views.
    with TemporaryDirectory() as tmp:
        main_path, lib_path = Path(tmp) / 'main', Path(tmp) / 'AGWheel'
        main_path.write_bytes(raw)
        lib_path.write_bytes(library)
        main_owner, lib_owner = lief.MachO.parse(str(main_path)), lief.MachO.parse(str(lib_path))
        main, lib = main_owner.at(0), lib_owner.at(0)
        u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        for macho, blob, slide in [(main, raw, 0), (lib, library, LIB)]:
            for segment in macho.segments:
                if segment.name == '__PAGEZERO':
                    continue
                u.mem_map(slide + segment.virtual_address, (segment.virtual_size + 4095) & -4096)
                u.mem_write(slide + segment.virtual_address, blob[segment.file_offset:segment.file_offset + segment.file_size])
        for address, size in [(FAKE, 0x40000), (HEAP, 0x400000), (STACK, 0x40000)]:
            u.mem_map(address, size)
        symbols = {s.name: LIB + s.value for s in lib.symbols if s.value}

        def put(at, fmt, *values): u.mem_write(at, struct.pack(fmt, *values))
        def get(at, fmt): return struct.unpack(fmt, u.mem_read(at, struct.calcsize(fmt)))[0]
        def reg(i): return u.reg_read(X[i])
        def ret(value=0):
            u.reg_write(X[0], value & 0xffffffffffffffff)
            u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_LR))

        for relocation in lib.relocations:
            assert relocation.size == 64 and int(relocation.type) == 1
            address = LIB + relocation.address
            put(address, '<Q', get(address, '<Q') + LIB)
        imports, imported_names = {}, {}
        for binding in lib.dyld_info.bindings:
            name = binding.symbol.name
            if name not in imported_names:
                address = FAKE + len(imported_names) * 256
                imported_names[name], imports[address] = address, name
            put(LIB + binding.address, '<Q', imported_names[name])

        cursor = HEAP + 0x10000
        def alloc(size=0x100):
            nonlocal cursor
            value = cursor
            cursor += (size + 15) & -16
            assert cursor < HEAP + 0x400000
            u.mem_write(value, bytes(size))
            return value

        env, graphics, jni = HEAP, HEAP + 0x1000, HEAP + 0x2000
        put(env, '<Q', jni)
        jni_targets = {}
        for index in [23, 31, 172]:
            jni_targets[FAKE + 0x20000 + index * 16] = index
            put(jni + index * 8, '<Q', FAKE + 0x20000 + index * 16)
        home = json.loads((ROOT / 'native-map.json').read_text())
        rooms = json.loads((ROOT / 'presentation-map.json').read_text())
        stats = [0x56ff3c, 0x65a4f0, 0x73f1b4, 0x823e78, 0x908b3c, 0x9ed800]
        local_player, other_player = alloc(0x200), alloc(0x200)
        put(local_player + 0xb8, '<I', 7)
        put(other_player + 0xb8, '<I', 9)
        strings, events, boundaries, guard_returns = {}, [], {}, []
        endpoint, unavailable, mutex_depth = STOP, False, 0

        def hook(uc, pc, size, context):
            nonlocal mutex_depth
            if pc == endpoint:
                uc.emu_stop()
            elif pc == GUARD_RETURN:
                u.reg_write(UC_ARM64_REG_PC, guard_returns.pop())
            elif pc in boundaries:
                boundaries[pc]()
            elif pc == symbols['_AGWheelGuard']:
                body, job = reg(1), reg(2)
                guard_returns.append(u.reg_read(UC_ARM64_REG_LR))
                u.reg_write(X[1], job)
                u.reg_write(UC_ARM64_REG_LR, GUARD_RETURN)
                u.reg_write(UC_ARM64_REG_PC, body)
            elif pc == symbols['_AGAuraSpritePaint']:
                events.append(('aura', tuple(reg(i) for i in range(8))))
                ret(1)
            elif pc == symbols['_AGLobbyOpenNative']:
                events.append(('open', tuple(reg(i) for i in range(3))))
                ret()
            elif pc == MAIN + 0x131cf70:
                name = bytes(u.mem_read(reg(1), 128)).split(b'\0')[0].decode()
                ret(0 if unavailable else symbols['_' + name])
            elif pc == MAIN + 0x12e8038:
                value = bytes(u.mem_read(reg(2), 256)).split(b'\0')[0].decode('utf-8')
                assert reg(3) == len(value.encode('utf-16-le')) // 2
                obj = alloc()
                strings[obj] = value
                ret(obj)
            elif pc == MAIN + 0x12e7f74:
                put(reg(1) + 0x18 + reg(2) * 8, '<Q', reg(3))
                ret()
            elif pc in jni_targets:
                index = jni_targets[pc]
                if index == 172:
                    array = alloc(0x18 + reg(1) * 8)
                    put(array + 0x10, '<I', reg(1))
                    ret(array)
                elif index == 31: ret(HEAP + 0x4000)
                else: ret()
            elif pc == MAIN + 0x1c6144:
                events.append(('image', tuple(reg(i) for i in range(6))))
                ret()
            elif pc == MAIN + 0x1c6150:
                stack = u.reg_read(UC_ARM64_REG_SP)
                events.append(('region', tuple(reg(i) for i in range(8)) + tuple(get(stack + 8 * i, '<Q') for i in range(3))))
                ret()
            elif pc in imports:
                name = imports[pc]
                if name == '__dyld_get_image_header': ret(MAIN)
                elif name == '_pthread_mutex_lock': mutex_depth += 1; ret()
                elif name == '_pthread_mutex_unlock': mutex_depth -= 1; assert mutex_depth >= 0; ret()
                elif name == '_clock_gettime': put(reg(1), '<qq', 100, 125000000); ret()
                elif name in ('_memcpy', '_memmove', '___memcpy_chk'):
                    u.mem_write(reg(0), bytes(u.mem_read(reg(1), reg(2)))); ret(reg(0))
                elif name in ('_bzero', '_memset'):
                    length = reg(1) if name == '_bzero' else reg(2)
                    u.mem_write(reg(0), bytes([0 if name == '_bzero' else reg(1) & 255]) * length); ret()
                elif name == '_memcmp':
                    a, b = bytes(u.mem_read(reg(0), reg(2))), bytes(u.mem_read(reg(1), reg(2)))
                    ret((a > b) - (a < b))
                else: raise AssertionError(('Unexpected OS boundary', name))

        u.hook_add(UC_HOOK_CODE, hook)
        def run(pc, args=(), end=STOP):
            nonlocal endpoint
            endpoint = end
            events.clear()
            u.reg_write(UC_ARM64_REG_SP, SP)
            u.reg_write(UC_ARM64_REG_LR, STOP)
            for i in range(31): u.reg_write(X[i], 0xc000 + i)
            u.reg_write(UC_ARM64_REG_LR, STOP)
            for i, value in enumerate(args): u.reg_write(X[i], value)
            u.emu_start(pc, end + 4, count=1000000)
            assert u.reg_read(UC_ARM64_REG_PC) == end, hex(u.reg_read(UC_ARM64_REG_PC))
            assert u.reg_read(UC_ARM64_REG_SP) == SP
            assert mutex_depth == 0 and not guard_returns

        # Initialize the actual Apple-built aura table using its wire parser.
        global_wire = b'AURA\1' + struct.pack('>QIBH', 9, 15, 0, 2)
        global_wire += struct.pack('>IBBBQ', 7, 6, 7, 16, 11) + struct.pack('>IBBBQ', 9, 1, 3, 2, 12)
        scene_wire = b'AURA\2' + struct.pack('>QIQQH', 9, 15, 1, 99, 2)
        scene_wire += struct.pack('>IBBB', 7, 6, 5, 12) + struct.pack('>IBBB', 9, 1, 6, 8)
        for v in range(6):
            for packet in [global_wire, scene_wire]:
                p = alloc(len(packet)); u.mem_write(p, packet)
                run(symbols['_AGAuraApply'], [symbols['_states'] + v * ctypes.sizeof(AuraState), 44, p, len(packet)])
                assert reg(0) == 1

        scene_cases = 0
        for v, (menu, room) in enumerate(zip(home, rooms)):
            renderer = MAIN + room['boss_renderer']
            boundaries[renderer] = lambda: (events.append(('body', tuple(reg(i) for i in range(8)))), ret())
            boundaries[MAIN + stats[v]] = lambda: ret(local_player)
            sites = [(menu['home_build'] + (0xdd8 if v else 0xec8), None),
                     (room['boss_renderer'] + (0x171c4 if v else 0x17cdc), None),
                     (room['room_paint'] + 0x1620, 528), (room['room_paint'] + 0x2138, 696)]
            for site, slot in sites:
                for missing in [False, True]:
                    for hero in ([6, 1] if slot is None else [1, 6]):
                        unavailable = missing
                        put(MAIN + SCENE_CACHE, '<Q', 0)
                        put(SP + (slot or 0), '<Q', other_player)
                        args = [env, graphics, hero, 2, 120, 250, 20, HEAP + 0x5000]
                        run(MAIN + site, args, MAIN + site + 4)
                        expected = 240 if slot is None and hero == 6 else 200 if slot is not None and hero == 1 else 0
                        assert [e[0] for e in events] == (['aura', 'body', 'aura'] if expected and not missing else ['body'])
                        assert next(e[1] for e in events if e[0] == 'body') == tuple(args)
                        if expected and not missing:
                            assert events[0][1][4:7] == (expected >> 5, expected & 31, 0)
                            assert events[2][1][4:7] == (expected >> 5, expected & 31, 1)
                        for i in range(19, 30): assert reg(i) == 0xc000 + i
                        scene_cases += 1
            boundaries.pop(renderer)
            boundaries.pop(MAIN + stats[v])
        unavailable = False

        # Cached image objects stand in for decoded package PNGs. Execute the
        # compiled preview-array update and actual native image draw arguments.
        preview_cases, boss_cases = 0, 0
        for index, (prefix, width, height) in enumerate([('dragon105', 100, 93), ('dragon105', 160, 149), ('mimic111', 100, 93)]):
            state = symbols['_waitRoomArt'] + index * 40
            pictures = [alloc() for _ in range(3)]
            label = alloc()
            strings[label] = 'Thung Lũng Rồng' if index < 2 else 'Đền Gương Vỡ'
            put(state, '<QQQQii', *pictures, label, width, height)
        for v, room in enumerate(rooms):
            for room_id in [18, 19]:
                for screen_width in [224, 390]:
                    index = (screen_width >= 350) if room_id == 18 else 2
                    state = symbols['_waitRoomArt'] + index * 40
                    rg = alloc(0x200)
                    put(MAIN + room['room_class'], '<Q', rg)
                    put(rg + 0x130, '<BB', room_id, 5)
                    put(graphics + 0x48, '<I', screen_width)
                    site = room['room_paint'] + 0x84
                    # Names getter comes from the original call, unchanged by this build.
                    names_getter = called(raw, room['room_paint'] + 0x338c)
                    old = alloc(0x18 + 40 * 8); put(old + 0x10, '<I', 40)
                    thumb = alloc(0x18 + 40 * 8); put(thumb + 0x10, '<I', 40)
                    put(rg + 0xb0, '<Q', thumb)
                    saved_names = [old]
                    def set_names(): saved_names[0] = reg(1); ret()
                    boundaries[MAIN + names_getter] = lambda: ret(saved_names[0])
                    boundaries[MAIN + names_getter + 0x3c] = set_names
                    # The displaced graphics reset is passed as callback stack arg 10.
                    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
                    # Its address is available in the trampoline's ADRP/ADD pair;
                    # let it execute until the callback, then use a safe no-op.
                    branch_word = int.from_bytes(raw[site:site+4], 'little')
                    delta = (branch_word & 0x3ffffff) - ((branch_word & 0x2000000) << 1)
                    shim = site + delta * 4
                    shim_off = shim - 0x40000
                    code = list(Cs(CS_ARCH_ARM64, CS_MODE_ARM).disasm(raw[shim_off:shim_off+12], shim))
                    original = int(code[1].op_str.split('#')[1], 16) + ((int.from_bytes(raw[shim_off+8:shim_off+12], 'little') >> 10) & 4095)
                    boundaries[MAIN + original] = lambda: ret()
                    run(MAIN + site, [env, graphics], MAIN + site + 4)
                    entry = 41 if room_id == 18 else 42
                    assert get(saved_names[0] + 0x18 + entry * 8, '<Q') == get(state + 24, '<Q')
                    assert get(get(rg + 0xb0, '<Q') + 0x18 + entry * 8, '<Q') == get(state, '<Q')
                    assert get(saved_names[0] + 0x10, '<I') == 43
                    preview_cases += 1
                    args = [env, graphics, 15, 1, 120, 250, 2, 0]
                    run(MAIN + room['boss_call'], args, MAIN + room['boss_call'] + 4)
                    if room_id == 18:
                        assert [e[0] for e in events] == ['region', 'region']
                        assert [e[1][2] for e in events] == [get(state + 8, '<Q'), get(state + 16, '<Q')]
                    else:
                        assert events == [('image', (env, graphics, get(state + 8, '<Q'), 120, 250, 33))]
                    boss_cases += 1
                    for address in [MAIN + names_getter, MAIN + names_getter + 0x3c, MAIN + original]: boundaries.pop(address)

        menu_cases = 0
        for v, menu in enumerate(home):
            widget = alloc(0x200)
            for row in [0, 1, 3, 6]:
                put(widget + 0x60, '<I', row)
                put(widget + 0x9f, '<B', 1)
                site = menu['home_select'] - 0x94
                endpoint = MAIN + (menu['home_after_action'] if row == 0 else site + 4)
                # x19 and x22 are live locals in this original menu method.
                args = [env] + [0xc000 + i for i in range(1, 23)]
                args[19], args[22] = env, widget
                run(MAIN + site, args, endpoint)
                assert events == ([('open', (env, v, 1))] if row == 0 else [])
                assert get(widget + 0x9f, '<B') == (0 if row == 0 else 1)
                menu_cases += 1
            array = alloc(0x30); put(array + 0x10, '<I', 3)
            site = menu['home_build'] + 0x1d8
            run(MAIN + site, [env, array, 0, 0], MAIN + site + 4)
            assert strings[get(array + 0x18, '<Q')] == 'CHIẾN TRƯỜNG'
            menu_cases += 1
            parent = alloc(0x200)
            for depth in [0, 1, 2]:
                for category in [0, 1, 6, 7]:
                    for row in [0, 1, 3, 6]:
                        put(parent + 0xdc, '<I', category)
                        put(parent + 0xe6, '<B', 7)
                        put(widget + 0x60, '<I', row)
                        put(widget + 0x9f, '<B', 1)
                        tab = 1 if (depth, category, row) == (2, 6, 0) else 3 if (depth, category, row) == (2, 7, 3) else 0
                        args = [0xc000 + i for i in range(23)]
                        args[8], args[9], args[13], args[14] = parent, depth, v, MAIN + menu['home_after_action'] - 4
                        args[19], args[22] = env, widget
                        end = MAIN + (menu['home_after_action'] if tab else 0x24ffc10)
                        run(MAIN + 0x24ff7c4, args, end)
                        assert events == ([('open', (env, v, tab))] if tab else [])
                        assert get(widget + 0x9f, '<B') == (0 if tab else 1)
                        menu_cases += 1
        result = dict(passed=True, scene_cases=scene_cases, room_preview_cases=preview_cases,
                      room_boss_draw_cases=boss_cases, native_menu_cases=menu_cases,
                      compiled_apple_scene=True, physical_device_tested=False, live_server_tested=False)
        print('PASS', json.dumps(result))
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = test(args.ipa)
    if args.report: args.report.write_text(json.dumps(result, indent=2))
