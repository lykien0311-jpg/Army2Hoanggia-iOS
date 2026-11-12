"""Add the two native menu actions to the exact build-269 ARM64 executable."""
from hashlib import sha256
import json
from pathlib import Path
from struct import pack, unpack_from


NATIVE_SHA = 'a80b8ceb31fd3d3090a126fa9555c46ce7c50134ee051f53c6c8a1e5de2d0c77'
RX_VM, RX_FILE = 0x24f8000, 0x24b8000
RX_END = 0x2500000
ENTRY_SPACE = 0x24ffb20
STRINGS = 0x24fff80
INTERN = 0x12e8038
ARRAY_SET = 0x12e7f74
DLSYM = 0x131cf70


def branch(at, target, link=False):
    offset = target - at
    assert not offset % 4 and -(1 << 27) <= offset < (1 << 27)
    return (0x94000000 if link else 0x14000000) | ((offset >> 2) & 0x3ffffff)


def near(at, target, instruction):
    offset = target - at
    assert not offset % 4 and -(1 << 20) <= offset < (1 << 20)
    return instruction | (((offset >> 2) & 0x7ffff) << 5)


def address(at, target, register, page=False):
    offset = (target >> 12) - (at >> 12) if page else target - at
    assert -(1 << 20) <= offset < (1 << 20)
    return (0x90000000 if page else 0x10000000) | ((offset & 3) << 29) | ((offset >> 2 & 0x7ffff) << 5) | register


def mov(register, immediate):
    return 0x52800000 | (immediate << 5) | register


def add(register, immediate):
    return 0x91000000 | (immediate << 10) | (register << 5) | register


def patch_menu(native):
    if sha256(native).hexdigest() != NATIVE_SHA:
        raise ValueError('Unexpected native executable')
    out = bytearray(native)
    def write(at, data, expected):
        assert out[at:at + len(data)] == expected, hex(at)
        out[at:at + len(data)] = data

    def edit(at, before, after):
        write(at, pack('<I', after), pack('<I', before))

    def emit(at, words):
        data = pack(f'<{len(words)}I', *words)
        file = RX_FILE + at - RX_VM
        assert ENTRY_SPACE <= at and at + len(data) <= STRINGS
        write(file, data, bytes(len(data)))

    symbol, field, market = STRINGS, STRINGS + 0x20, STRINGS + 0x40
    aura = STRINGS + 0x60
    for at, label in [(symbol, 'AGLobbyOpenNative'), (field, 'CHIẾN TRƯỜNG'), (market, 'GIAN HÀNG'), (aura, 'AGAuraPaintActor')]:
        data = label.encode('utf-8') + b'\0'
        assert at + len(data) <= RX_END
        write(RX_FILE + at - RX_VM, data, bytes(len(data)))

    # String[] construction calls the same Java allocator/setter as the
    # original menu. Attack index 0 replaces the previous random action.
    field_label = ENTRY_SPACE
    emit(field_label, [
        address(field_label, 0x2500000, 1, page=True), add(1, 0x1c0),
        address(field_label + 8, field, 2), mov(3, len('CHIẾN TRƯỜNG')),
        branch(field_label + 16, INTERN),
    ])
    market_label = field_label + 0x20
    emit(market_label, [
        0xa9be7bfd,  # stp x29,x30,[sp,#-32]!
        0x910003fd,  # mov x29,sp
        0xa90107e0,  # stp x0,x1,[sp,#16]
        branch(market_label + 12, ARRAY_SET, True),  # original Sự kiện at index 5
        0xf9400be0,  # ldr x0,[sp,#16]
        address(market_label + 20, 0x2500000, 1, page=True), add(1, 0x1c8),
        address(market_label + 28, market, 2), mov(3, len('GIAN HÀNG')),
        branch(market_label + 36, INTERN, True),
        0xaa0003e3,  # mov x3,x0
        0xa94107e0,  # ldp x0,x1,[sp,#16]
        mov(2, 3), branch(market_label + 52, ARRAY_SET, True),
        0xa8c27bfd, 0xd65f03c0,  # ldp x29,x30,[sp],#32; ret
    ])

    # The key and touch paths both enter here with x8 = Home class statics,
    # x22 = screen, x19 = Java Env. The shim's two continuation branches
    # resume the original selection or return to the same open menu.
    select = market_label + 0x50
    fallback = select + 31 * 4
    invoke = select + 15 * 4
    emit(select, [
        0x7100053f, near(select + 4, fallback, 0x54000001),  # depth != 1
        0xb940dd10, 0xb94062d1,  # ldr w16,[x8,#220]; ldr w17,[x22,#96]
        0x71001a1f, near(select + 20, select + 48, 0x54000000),  # attack category 6
        0x7100061f, near(select + 28, fallback, 0x54000001),  # shop category 1
        0x71000e3f, near(select + 36, fallback, 0x54000001),  # market row 3
        mov(17, 2), branch(select + 44, invoke),
        near(select + 48, fallback, 0x35000011),  # original random row 0
        mov(17, 1), 0xd503201f,
        0xa9bd7bfd, 0x910003fd, 0xa90137ee, 0xb90023f1,  # save continuations and tab
        0x92800020, address(select + 80, symbol, 1), branch(select + 84, DLSYM, True),
        0xaa0003f0, near(select + 92, select + 112, 0xb4000010),  # cbz x16,restore
        0xaa1303e0, 0xb9401be1, 0xb94023e2, 0xd63f0200,  # env, variant, tab; blr x16
        0xa94137ee, 0xa8c37bfd, 0x910011ce, 0xd61f01c0,  # restore and return via handled branch
    ])

    maps = json.loads(Path(__file__).with_name('native-map.json').read_text())
    assert len(maps) == 6
    for variant, entry in enumerate(maps):
        build = entry['home_build']
        at = build + 0x394
        original = unpack_from('<I', native, at)[0]
        assert original >> 26 == 0b100101
        edit(at, original, branch(at, field_label, True))

        edit(build + 0x4d4, mov(1, 5), mov(1, 6))
        edit(build + 0x528, 0x320007e2, mov(2, 4))  # Item đội
        edit(build + 0x548, 0x321e03e2, mov(2, 5))  # Sự kiện
        at = build + 0x550
        edit(at, branch(at, ARRAY_SET, True), branch(at, market_label, True))

        confirm = entry['home_select'] - 0x1d4
        at = confirm + 0x500
        edit(at, 0x6b0a013f, 0x7100113f)  # native Item đội moves from 3 to 4
        edit(confirm + 0x844, 0x7100113f, 0x7100153f)  # native Sự kiện moves from 4 to 5
        shim = select + 0x90 + variant * 28
        emit(shim, [
            near(shim, shim + 8, 0x35000009), branch(shim + 4, confirm + 152),
            mov(13, variant), address(shim + 12, shim + 20, 14),
            branch(shim + 16, select), branch(shim + 20, confirm + 4),
            branch(shim + 24, entry['home_after_action'] + 0x28),
        ])
        edit(confirm, 0x340004c9, branch(confirm, shim))

    # Wrap the native arena's player paint call so both aura layers follow the
    # original camera, visibility and drawing order. x4 carries the original
    # renderer trampoline. A missing framework export falls back to it.
    draw = 0x24ffd00
    emit(draw, [
        0xa9bc7bfd, 0x910003fd,  # stp x29,x30,[sp,#-64]!; mov x29,sp
        0xa90107e0, 0xa9020fe2, 0xf9001be4,  # save env, actor, graphics, variant, trampoline
        address(draw + 20, 0x2500000, 9, page=True), 0xf940e930,
        near(draw + 28, draw + 56, 0xb5000010),  # cbnz x16,resolved
        0x92800020, address(draw + 36, aura, 1), branch(draw + 40, DLSYM, True),
        address(draw + 44, 0x2500000, 9, page=True), 0xf900e920, 0xaa0003f0,
        0xa94107e0, 0xa9420fe2, 0xf9401be4, 0xa8c47bfd,
        near(draw + 72, draw + 80, 0xb4000010), 0xd61f0200, 0xd61f0080,  # br x16 or br x4
    ])
    paint_maps = json.loads(Path(__file__).with_name('blind-map.json').read_text())
    painters = (0x59bdbc, 0x684b80, 0x769844, 0x84e508, 0x9331cc, 0xa17e90)
    assert len(paint_maps) == len(painters)
    for variant,(entry,original) in enumerate(zip(paint_maps,painters)):
        assert entry['variant'] == variant
        site = entry['paint'] + 0x438
        assert native[site - 12:site] == bytes.fromhex('21feffb4a28359f8e00313aa')
        shim = draw + 0x60 + variant * 16
        emit(shim, [mov(3, variant), address(shim+4, shim+12, 4),
                    branch(shim+8, draw), branch(shim+12, original)])
        edit(site, branch(site, original, True), branch(site, shim, True))
    return bytes(out)
