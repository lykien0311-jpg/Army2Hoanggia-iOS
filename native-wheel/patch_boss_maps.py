"""Install the room 18/19 bridges on the guarded build-269 native image."""
import json
from pathlib import Path
from struct import pack, unpack_from

from patch_menu_269 import RX_FILE, RX_VM, DLSYM, add, address, branch, mov, near

OLD_MARKER = b"2.4.1-HG78-IPA"
MARKER = b"2.4.1-B275-IPA"
MAP_LOADS = (
    (0x4f85b8, 0x51a07c, 0x524ccc),
    (0x5e6f38, 0x607ac4, 0x612714),
    (0x6cbbfc, 0x6ec788, 0x6f73d8),
    (0x7b08c0, 0x7d144c, 0x7dc09c),
    (0x895584, 0x8b6110, 0x8c0d60),
    (0x97a248, 0x99add4, 0x9a5a24),
)
TERRAIN = (0x4f7998, 0x5e6390, 0x6cb054, 0x7afd18, 0x8949dc, 0x9796a0)
FLIGHT = (0x583650, 0x66d2cc, 0x751f90, 0x836c54, 0x91b918, 0xa005dc)


def patch_boss_maps(native):
    data = bytearray(native)
    bridge = 0x24ff690
    symbol = 0x24ffdc0
    slot = 0x25001d8
    low, high = bridge, symbol + 0x20

    def write(file, payload, expected):
        if data[file:file + len(payload)] != expected:
            raise ValueError(f"Unexpected native bytes at {file:#x}")
        data[file:file + len(payload)] = payload

    def word(at):
        return unpack_from("<I", data, at)[0]

    def edit(at, before, after):
        write(at, pack("<I", after), pack("<I", before))

    def target(at):
        delta = word(at) & 0x3ffffff
        return at + ((delta ^ 0x2000000) - 0x2000000) * 4

    def emit(at, words):
        payload = pack(f"<{len(words)}I", *words)
        if not (bridge <= at and at + len(payload) <= 0x24ff800 or
                symbol + 0x20 <= at and at + len(payload) <= 0x24fff80):
            raise ValueError(f"Native boss bridge out of range at {at:#x}")
        write(RX_FILE + at - RX_VM, payload, bytes(len(payload)))
        return at + len(payload)

    raw = b"AGBossNativeHook\0"
    write(RX_FILE + symbol - RX_VM, raw, bytes(len(raw)))
    cache = RX_FILE + slot - RX_VM
    if data[cache:cache + 8] != bytes(8):
        raise ValueError("Expected an unused map bridge cache slot")
    # x0..x3 retain native arguments. w4/w5 identify variant and operation.
    # x6 is the original call, or zero for an inserted paint callback.
    low = emit(bridge, [
        0xa9bb7bfd, 0x910003fd,                      # fp/lr; 80-byte aligned frame
        0xa90107e0, 0xa9020fe2, 0xa90317e4, 0xf90023e6,
        address(bridge + 24, slot, 9, page=True), 0xf940ed30,
        near(bridge + 32, bridge + 60, 0xb5000010),
        0x92800020, address(bridge + 40, symbol, 1), branch(bridge + 44, DLSYM, True),
        address(bridge + 48, slot, 9, page=True), 0xf900ed20, 0xaa0003f0,
        near(bridge + 60, bridge + 84, 0xb4000010),
        0xa94107e0, 0xa9420fe2, 0xa94317e4, 0xd63f0200,
        near(bridge + 80, bridge + 108, 0x35000000),  # handled
        0xa94107e0, 0xa9420fe2, 0xf94023e6, 0xa8c57bfd,
        near(bridge + 100, bridge + 112, 0xb4000006), 0xd61f00c0,
        0xa8c57bfd, 0xd65f03c0,
    ])

    def shim(at, variant, operation, original):
        return emit(at, [mov(4, variant), mov(5, operation),
                        address(at + 8, original, 6, page=True), add(6, original & 4095),
                        branch(at + 16, bridge)])

    background = low
    # b from the original painter skipped three instructions in the loop's
    # increment path. The inserted callback returns to the same location.
    low = emit(background, [
        0x910033de, 0xf85983a1, 0xaa1303e0, mov(5, 2), 0xaa1f03e6,
        branch(background + 20, bridge),
    ])
    painters = json.loads(Path(__file__).with_name("blind-map.json").read_text())
    for v, ((load, *sites), destroy, paint) in enumerate(zip(MAP_LOADS, TERRAIN, painters, strict=True)):
        start = low
        low = shim(low, v, 0, load)
        for site in sites:
            edit(site, branch(site, load, True), branch(site, start, True))
        start = high
        high = shim(high, v, 1, destroy)
        site = destroy - 0x8d8
        edit(site, branch(site, destroy, True), branch(site, start, True))

        site = paint["paint"] + 0x100
        start = low
        low = emit(low, [mov(4, v), branch(low + 4, background)])
        edit(site, branch(site, site + 16), branch(site, start, True))
        site = paint["paint"] + 0x454
        if word(site) >> 26 != 37 or data[site - 8:site] != bytes.fromhex("a28359f8e00313aa"):
            raise ValueError("Unexpected projectile renderer call")
        start = high
        high = shim(high, v, 3, target(site))
        edit(site, word(site), branch(site, start, True))

        site = FLIGHT[v] + 0x84
        if word(FLIGHT[v] + 0x0c) != 0x39017c24 or word(FLIGHT[v] + 0x18) != 0x39018023:
            raise ValueError("Unexpected projectile state layout")
        start = high
        high = emit(high, [mov(4, v), mov(5, 4), 0xaa1f03e6, branch(high + 12, bridge)])
        edit(site, 0xd65f03c0, branch(site, start))

    if native.count(OLD_MARKER + b"\0") != 1 or len(OLD_MARKER) != len(MARKER):
        raise ValueError("Unexpected iOS build marker")
    write(native.index(OLD_MARKER + b"\0"), MARKER, OLD_MARKER)
    return bytes(data)
