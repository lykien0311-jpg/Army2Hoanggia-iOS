"""Static ARM64 hooks, with separate RX/RW segments and __LINKEDIT kept last.

This edits ONLY the exact, previously repaired native executable. No runtime
code patching/JIT, new network socket, embedded account, or server connection.
Use --prepare for inspectable native hooks without creating an installable IPA.
"""
from pathlib import Path
import struct, hashlib, json, argparse, zipfile
from keystone import Ks, KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN
BASE=0x100000000
ROOT=Path(__file__).resolve().parent
APP='Payload/Army2Hoanggia.app/'
EXPECTED_IPA='8c4779afad7981f4bf8cf5e756bdf03450437cc4e56cf949c805e2d2affc636d'
EXPECTED_ORIGINAL='34778a89dac9103a1fd62a6e712dce1bedd012da3bbb47c7ce908724b1d4c7d6'
PAGE=0x8000
CODE_LIMIT=0x7800
KS=Ks(KS_ARCH_ARM64,KS_MODE_LITTLE_ENDIAN)
# Exact text read from the user's seven-second reference video (video 2).
# IDs are the protocol IDs stored in each room, never their display row.
REFERENCE_TITLES = {
    3:'Phòng 3: Bom',4:'Phòng 4: Bom 2',5:'Phòng 5: Nhện máy',
    6:'Phòng 6: Người máy',7:'Phòng 7: T-rex máy',8:'Phòng 8: UFO',
    9:'Phòng 9: UFO',10:'Phòng 10: Khí cầu',11:'Phòng 11: Nhện độc',
    12:'Phòng 12: Ma',13:'Phòng 13: Ma 2',14:'Phòng 14: Trùm liên hoàn',
    15:'Phòng 15: Trùm liên hoàn',16:'Phòng 16: Super Boss',
}
def asm(text,address):return bytes(KS.asm(text,address)[0])
def align(n,a=8):return (n+a-1)&-a
def cstr(b,offset):return bytes(b[offset:]).split(b'\0',1)[0].decode()
def commands(b):
    p=32
    for _ in range(struct.unpack_from('<I',b,16)[0]):
        cmd,size=struct.unpack_from('<II',b,p);yield p,cmd,size;p+=size
def segment(name,vm,off,size,prot,sections=()):
    data=struct.pack('<II16sQQQQiiII',25,72+80*len(sections),name.encode(),BASE+vm,size,off,size,prot,prot,len(sections),0)
    for sname,svm,soff,ssize,flags,alignment in sections:
        data+=struct.pack('<16s16sQQIIIIIIII',sname.encode(),name.encode(),BASE+svm,ssize,soff,alignment,0,0,flags,0,0,0)
    return data
def find_dlsym(b):
    for p,cmd,size in commands(b):
        if cmd==2:symoff,nsyms,stroff,strsize=struct.unpack_from('<4I',b,p+8)
        elif cmd==11:indoff,nind=struct.unpack_from('<2I',b,p+56)
        elif cmd==25:
            for i in range(struct.unpack_from('<I',b,p+64)[0]):
                q=p+72+80*i
                if cstr(b,q)=='__stubs':
                    va,sz,off=struct.unpack_from('<QQI',b,q+32);indstart,stride=struct.unpack_from('<II',b,q+68)
    for i in range(sz//stride):
        idx=struct.unpack_from('<I',b,indoff+(indstart+i)*4)[0]
        if idx&0xc0000000:continue
        name=struct.unpack_from('<I',b,symoff+16*idx)[0]
        if cstr(b,stroff+name)=='_dlsym':return va-BASE+i*stride
    raise ValueError('dlsym import not found')

def build_native(old,original,maps):
    assert hashlib.sha256(original).hexdigest()==EXPECTED_ORIGINAL
    assert len(old)==len(original)
    cmds=list(commands(old));segments=[(p,struct.unpack_from('<16sQQQQiiII',old,p+8))for p,c,s in cmds if c==25]
    assert segments[-1][1][0].rstrip(b'\0')==b'__LINKEDIT'
    link_p,link=segments[-1];rxvm=link[1]-BASE;rxoff=link[3];rwvm=rxvm+PAGE;rwoff=rxoff+PAGE;delta=2*PAGE
    assert rxvm%PAGE==rxoff%PAGE==0
    assert link[3]+link[4]==len(old)
    assert not any(c in (0x1d,0x80000034,0x80000033)for p,c,s in cmds), 'Unexpected signature/chained fixups/export trie'
    dlsym=find_dlsym(old);b=bytearray(old[:rxoff]+bytes(delta)+old[rxoff:]);rx=bytearray(PAGE);records=[];cursor=0
    symbols={};strcursor=CODE_LIMIT
    camera_maps=json.loads((ROOT/'camera-map.json').read_text())
    camera_hooks=[]
    corpse_maps=json.loads((ROOT/'corpse-map.json').read_text());corpse_hooks=[]
    blind_maps=json.loads((ROOT/'blind-map.json').read_text());blind_hooks=[]
    for name in ('AGWheelOpen','AGWheelTick','AGWheelReceive','AGRoomReceive','AGRoomRebuild','AGMoveAllow','AGNotesReceive','AGNotesInput','AGNotesSettings','AGNotesInbox','AGGridAdjust','AGTurnReceive','AGTurnManual','AGTurnPulse','AGBattleAwait','AGTurnChange','AGViewportKeypad','AGWheelSuppressFooter','VÒNG XOAY MAY MẮN',*REFERENCE_TITLES.values(),'2.4.1-HG78-IPA'):
        raw=name.encode('utf-8')+b'\0';symbols[name]=rxvm+strcursor;rx[strcursor:strcursor+len(raw)]=raw;strcursor+=len(raw)
    raw=b'AGCameraAllow\0';symbols['AGCameraAllow']=rxvm+strcursor
    rx[strcursor:strcursor+len(raw)]=raw;strcursor+=len(raw)
    raw=b'AGBlindPaint\0';symbols['AGBlindPaint']=rxvm+strcursor
    rx[strcursor:strcursor+len(raw)]=raw;strcursor+=len(raw)
    for name in ('AGCorpseReceive','AGCorpseUpdate'):
        raw=name.encode()+b'\0';symbols[name]=rxvm+strcursor
        rx[strcursor:strcursor+len(raw)]=raw;strcursor+=len(raw)
    strcursor=align(strcursor,16);room_table=rxvm+strcursor
    for title in REFERENCE_TITLES.values():
        rx[strcursor:strcursor+8]=struct.pack('<iI',symbols[title]-(rxvm+strcursor),len(title.encode('utf-16-le'))//2)
        strcursor+=8
    def lookup(symbol,slot):
        # Aligned 64-bit function pointer cache. All racing resolvers write the
        # same address. Cache pages are RW, never executable.
        ptr=rwvm+slot*8;string=symbols[symbol]
        return f'''
            adrp x9, {ptr&-4096}
            ldr x10, [x9, #{ptr&4095}]
            cbnz x10, resolved{slot}
            mov x0, #-2
            adrp x1, {string&-4096}
            add x1, x1, #{string&4095}
            bl {dlsym}
            adrp x9, {ptr&-4096}
            str x0, [x9, #{ptr&4095}]
            mov x10, x0
          resolved{slot}:
        '''
    def emit(code):
        nonlocal cursor
        addr=rxvm+cursor;raw=asm(code,addr);assert cursor+len(raw)<=CODE_LIMIT
        rx[cursor:cursor+len(raw)]=raw;cursor=align(cursor+len(raw),16);return addr,raw
    def patch(at,raw,label):
        assert old[at:at+len(raw)]==original[at:at+len(raw)],(hex(at),label)
        records.append(dict(offset=at,label=label,before=b[at:at+len(raw)].hex(),after=raw.hex()))
        b[at:at+len(raw)]=raw
    keypad_paint=0x1fcbc4
    assert original[keypad_paint:keypad_paint+4]==asm('stp x22, x21, [sp, #-48]!',0)
    keypad_hook,_=emit(f'''
        stp x29, x30, [sp, #-48]!
        mov x29, sp
        stp x0, x1, [sp, #16]
        str x2, [sp, #32]
        {lookup('AGViewportKeypad',37)}
        cbz x10, keypad_original
        ldp x0, x1, [sp, #16]
        ldr x2, [sp, #32]
        blr x10
      keypad_original:
        ldp x0, x1, [sp, #16]
        ldr x2, [sp, #32]
        ldp x29, x30, [sp], #48
        stp x22, x21, [sp, #-48]!
        b {keypad_paint+4}
    ''')
    patch(keypad_paint,asm(f'b {keypad_hook}',keypad_paint),'Capture actual native keypad projection for the wheel footer')
    # Clan member packet 118 sends the absolute member rank as a short.
    # Reading one byte desynchronizes cup, equipment and contribution strings.
    for at in [5426252, 6399636, 7336792, 8273948, 9211104, 10148260]:
        assert original[at:at+4]==asm('bl 0xa64274',at)
        patch(at,asm('bl 0xa64208',at),'Clan members: read full 16-bit rank in packet 118')
    grid_map=json.loads((ROOT/'grid-map.json').read_text())
    save=['sub sp, sp, #800']
    for r in range(0,30,2):save.append(f'stp x{r}, x{r+1}, [sp, #{r*8}]')
    save += ['str x30, [sp, #240]','mrs x9, nzcv','str x9, [sp, #248]']
    for r in range(0,32,2):save.append(f'stp q{r}, q{r+1}, [sp, #{256+r*16}]')
    restore=[]
    for r in range(0,32,2):restore.append(f'ldp q{r}, q{r+1}, [sp, #{256+r*16}]')
    restore+=['ldr x9, [sp, #248]','msr nzcv, x9']
    for r in range(0,30,2):restore.append(f'ldp x{r}, x{r+1}, [sp, #{r*8}]')
    restore+=['ldr x30, [sp, #240]','add sp, sp, #800','ret']
    grid_hook,_=emit('\n'.join(save)+lookup('AGGridAdjust',32)+"""
        cbz x10, grid_restore
        mov x0, sp
        ldr x1, [sp, #240]
        sub x1, x1, #4
        blr x10
      grid_restore:
    """+'\n'.join(restore))
    for site in grid_map['sites']:
        at=site['site'];assert struct.unpack_from('<I',original,at)[0]==site['word']
        patch(at,asm(f'bl {grid_hook}',at),f"V{site['variant']+1} responsive inventory/shop {site['metric']}")
    # Match the app's literal-string getters. RoboVM registers the stable
    # cache slot itself; it must never point to a temporary stack location.
    label=symbols['VÒNG XOAY MAY MẮN'];label_cache=rwvm+40
    label_addr,_=emit(f'''
        stp x29, x30, [sp, #-16]!
        mov x29, sp
        adrp x1, {label_cache&-4096}
        add x1, x1, #{label_cache&4095}
        adrp x2, {label&-4096}
        add x2, x2, #{label&4095}
        mov w3, #{len('VÒNG XOAY MAY MẮN')}
        bl {0x12e8038}
        ldp x29, x30, [sp], #16
        ret
    ''')
    # Resolve the displayed title at the native paint site, so neither an
    # absent/late name packet nor a legacy shifted packet can repaint the
    # reference room IDs with the wrong label. Keep actual IDs, groups,
    # occupancy and enter-room dispatch untouched. Unknown IDs retain server
    # titles. Stable per-literal caches are registered by RoboVM itself.
    room_cache=rwvm+48
    room_title_addr,_=emit(f'''
        stp x29, x30, [sp, #-176]!
        mov x29, sp
        stp x0, x1, [sp, #16]
        stp x2, x3, [sp, #32]
        stp x4, x5, [sp, #48]
        stp x6, x7, [sp, #64]
        str x9, [sp, #80]
        stp x10, x11, [sp, #96]
        stp x12, x13, [sp, #112]
        stp x14, x15, [sp, #128]
        stp x16, x17, [sp, #144]
        mrs x10, nzcv
        str x10, [sp, #160]
        ldrb w9, [x8, #24]
        cmp w9, #18
        b.hs original
        cmp w9, #3
        b.lo plain
        cmp w9, #17
        b.eq plain
        sub w9, w9, #3
        adrp x1, {room_cache&-4096}
        add x1, x1, #{room_cache&4095}
        add x1, x1, x9, lsl #3
        ldr x8, [x1]
        cbnz x8, done
        adrp x10, {room_table&-4096}
        add x10, x10, #{room_table&4095}
        add x10, x10, x9, lsl #3
        ldrsw x2, [x10]
        add x2, x10, x2
        ldr w3, [x10, #4]
        mov x0, x19
        bl {0x12e8038}
        mov x8, x0
        b done
      plain:
        mov x8, xzr
        b done
      original:
        ldr x8, [x8, #16]
      done:
        ldr x10, [sp, #160]
        msr nzcv, x10
        ldp x0, x1, [sp, #16]
        ldp x2, x3, [sp, #32]
        ldp x4, x5, [sp, #48]
        ldp x6, x7, [sp, #64]
        ldr x9, [sp, #80]
        ldp x10, x11, [sp, #96]
        ldp x12, x13, [sp, #112]
        ldp x14, x15, [sp, #128]
        ldp x16, x17, [sp, #144]
        ldp x29, x30, [sp], #176
        ret
    ''')
    turn_map=json.loads((ROOT/'turn-map.json').read_text())
    turn_sequence=json.loads((ROOT/'turn-sequence-map.json').read_text())
    # The old "boss_sites" were X-coordinate subtractions in player-slot
    # painting, not boss identity calculations. Leave all twelve intact.
    presentation=json.loads((ROOT/'presentation-map.json').read_text())
    boss_hooks=[];footer_hooks=[];canvas_footer_hooks=[];zone_patches=[];arena_update_hooks=[];turn_wait_hooks=[];turn_change_hooks=[]
    notes=json.loads((ROOT/'notes-map.json').read_text())
    hooks=[]
    for i,m in enumerate(maps):
        n=notes[i]
        pm=presentation[i];room=pm['room_class'];renderer=pm['boss_renderer']
        bm=blind_maps[i];arena_class=turn_map[i]['arena_class'];site=bm['site']
        blind_addr,_=emit(f'''
            stp x29, x30, [sp, #-32]!
            str x2, [sp, #16]
            {lookup('AGBlindPaint',41)}
            cbz x10, blind_original
            mov x0, x19
            ldr x1, [sp, #16]
            mov w2, #{i}
            blr x10
            cbz w0, blind_original
            ldp x29, x30, [sp], #32
            adrp x22, {arena_class&-4096}
            add x22, x22, #{arena_class&4095}
            mov w8, #2
            stur w8, [x29, #-0x6c]
            mov w8, #5
            stur w8, [x29, #-0x8c]
            mov w8, #10
            stur w8, [x29, #-0x90]
            stur w8, [x29, #-0x94]
            mov w8, #1
            str w8, [sp, #0x6c]
            mov w8, #60
            stur w8, [x29, #-0x80]
            mov w8, #30
            stur w8, [x29, #-0x88]
            b {bm['hud']}
          blind_original:
            ldr x2, [sp, #16]
            ldp x29, x30, [sp], #32
            mov x0, x19
            mov x1, x2
            b {site+4}
        ''')
        assert original[site:site+4]==asm('mov x1,x2',site)
        patch(site,asm(f'b {blind_addr}',site),f'V{i+1} white blind-bomb world layer, then original HUD/menu/keypad')
        blind_hooks.append(dict(**bm,hook=blind_addr))
        # Resolve the boss argument at the actual sprite-renderer call.
        # R5.l0 (0x130) is the room number. R5.w0 at 132 is the area number,
        # NOT the current map. Linked rooms retain the native stage's type.
        # The original renderer has explicit ghost branches at IDs 25/26.
        boss_addr,_=emit(f'''
            stp x9, x10, [sp, #-32]!
            mrs x9, nzcv
            str x9, [sp, #16]
            adrp x9, {room&-4096}
            ldr x9, [x9, #{room&4095}]
            cbz x9, boss_done
            ldrb w10, [x9, #0x130]
            sub w10, w10, #3
            cmp w10, #13
            b.hi boss_done
            adr x9, boss_table
            ldrb w10, [x9, w10, uxtw]
            cmp w10, #255
            b.eq boss_done
            mov w2, w10
            b boss_done
          boss_done:
            ldr x9, [sp, #16]
            msr nzcv, x9
            ldp x9, x10, [sp], #32
            b {renderer}
          boss_table:
            .byte 12,12,13,14,15,16,16,17,22,25,26,255,255,15
        ''')
        site=pm['boss_call'];assert original[site:site+4]==asm(f'bl {renderer}',site)
        patch(site,asm(f'bl {boss_addr}',site),f'V{i+1} choose room boss at the actual sprite draw call')
        boss_hooks.append(dict(**pm,hook=boss_addr))
        footer=pm['footer'];displaced=original[footer:footer+4]
        assert displaced==asm('stp x22, x21, [sp, #-48]!',0)
        footer_addr,_=emit(f'''
            stp x29, x30, [sp, #-48]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            str x2, [sp, #32]
            {lookup('AGWheelSuppressFooter',35)}
            cbz x10, footer_original
            mov w0, #{i}
            blr x10
            cbz w0, footer_original
            ldp x29, x30, [sp], #48
            ret
          footer_original:
            ldp x0, x1, [sp, #16]
            ldr x2, [sp, #32]
            ldp x29, x30, [sp], #48
            stp x22, x21, [sp, #-48]!
            b {footer+4}
        ''')
        patch(footer,asm(f'b {footer_addr}',footer),f'V{i+1} hide native small softkeys only while the wheel is visible')
        footer_hooks.append(dict(variant=i,site=footer,hook=footer_addr))
        # GameCanvas independently paints the default small left/right
        # commands after the screen's painter. Suppress these too.
        font=pm['font_renderer']
        glyph_addr,_=emit(f'''
            stp x29, x30, [sp, #-80]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            stp x2, x3, [sp, #32]
            stp x4, x5, [sp, #48]
            stp x6, x7, [sp, #64]
            {lookup('AGWheelSuppressFooter',35)}
            cbz x10, glyph_original
            mov w0, #{i}
            blr x10
            cbz w0, glyph_original
            ldp x29, x30, [sp], #80
            ret
          glyph_original:
            ldp x0, x1, [sp, #16]
            ldp x2, x3, [sp, #32]
            ldp x4, x5, [sp, #48]
            ldp x6, x7, [sp, #64]
            ldp x29, x30, [sp], #80
            b {font}
        ''')
        for site in pm['canvas_footer_calls']:
            assert original[site:site+4]==asm(f'bl {font}',site)
            patch(site,asm(f'bl {glyph_addr}',site),f'V{i+1} suppress GameCanvas default small command while wheel visible')
            canvas_footer_hooks.append(dict(variant=i,site=site,hook=glyph_addr,renderer=font))
        open_addr,raw=emit(f'''
            stp x29, x30, [sp, #-32]!
            mov x29, sp
            str x0, [sp, #16]
            {lookup('AGWheelOpen',0)}
            cbz x10, done
            ldr x0, [sp, #16]
            mov w1, #{i}
            blr x10
          done:
            ldp x29, x30, [sp], #32
            ret
        ''')
        # A dedicated callback instance in the existing clock callback class
        # adds an independent command without changing the real clock command.
        # The menu owns the live callback; its identity is retained per variant.
        callback_slot=rwvm+160+i*8
        v9_addr,_=emit(f'''
            stp x29, x30, [sp, #-64]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            bl {0xbe6b7c}
            ldr x0, [sp, #16]
            bl {m['command_alloc']}
            str x0, [sp, #32]
            ldr x0, [sp, #16]
            bl {m['clock_alloc']}
            str x0, [sp, #40]
            mov x1, x0
            ldr x0, [sp, #16]
            bl {m['clock_ctor']}
            ldr x0, [sp, #16]
            bl {label_addr}
            mov x2, x0
            ldr x0, [sp, #16]
            ldr x1, [sp, #32]
            ldr x3, [sp, #40]
            bl {m['command_ctor']}
            ldp x0, x1, [sp, #16]
            ldr x2, [sp, #32]
            bl {0x1dfcac}
            ldr x8, [sp, #40]
            adrp x9, {callback_slot&-4096}
            str x8, [x9, #{callback_slot&4095}]
            ldp x29, x30, [sp], #64
            ret
        ''')
        assert original[m['v9_ctor_call']:m['v9_ctor_call']+4]==asm(f'bl {0xbe6b7c}',m['v9_ctor_call'])
        patch(m['v9_ctor_call'],asm(f'bl {v9_addr}',m['v9_ctor_call']),f'V{i+1} prepend wheel to in-battle V9')
        clock_addr,_=emit(f'''
            adrp x9, {callback_slot&-4096}
            ldr x9, [x9, #{callback_slot&4095}]
            cmp x1, x9
            b.ne original
            cbz x1, original
            stp x29, x30, [sp, #-32]!
            str x0, [sp, #16]
            bl {m['key_reset']}
            ldr x0, [sp, #16]
            bl {open_addr}
            ldp x29, x30, [sp], #32
            ret
          original:
            stp x22, x21, [sp, #-48]!
            b {m['clock']+4}
        ''')
        assert original[m['clock']:m['clock']+4]==asm('stp x22, x21, [sp, #-48]!',0)
        patch(m['clock'],asm(f'b {clock_addr}',m['clock']),f'V{i+1} distinguish new wheel action from unchanged clock action')
        move_addr,_=emit(f'''
            stp x29, x30, [sp, #-48]!
            stp x0, x1, [sp, #16]
            str x2, [sp, #32]
            {lookup('AGMoveAllow',26)}
            cbz x10, walk
            mov w0, #{i}
            ldr x1, [sp, #24]
            ldr w2, [sp, #32]
            blr x10
            cbz w0, done
          walk:
            ldp x0, x1, [sp, #16]
            ldr x2, [sp, #32]
            bl {m['walk']}
          done:
            ldp x29, x30, [sp], #48
            ret
        ''')
        for site in m['walk_input_calls']:
            assert original[site:site+4]==asm(f"bl {m['walk']}",site)
            patch(site,asm(f'bl {move_addr}',site),f'V{i+1} pace local left/right input independently of speed')
        # Only the directional delta setters are paced, and only in manual
        # camera mode (0). Native auto-follow/update/clamping remain intact.
        cm=camera_maps[i]
        for axis,site in enumerate((cm['pan_x'],cm['pan_y'])):
            clazz=cm['camera_class']
            camera_addr,_=emit(f'''
                stp x29, x30, [sp, #-48]!
                stp x0, x1, [sp, #16]
                adrp x16, {clazz&-4096}
                add x16, x16, #{clazz&4095}
                ldrb w15, [x16, #9]
                tbz w15, #1, camera_original
                ldr x15, [x16]
                cbz x15, camera_original
                str x15, [sp, #32]
                ldrb w16, [x15, #0xbc]
                cbnz w16, camera_original
                {lookup('AGCameraAllow',40)}
                cbz x10, camera_original
                mov w0, #{i}
                ldr x1, [sp, #32]
                mov w2, #{axis}
                ldr w3, [sp, #24]
                blr x10
                cbz w0, camera_done
              camera_original:
                ldp x0, x1, [sp, #16]
                ldp x29, x30, [sp], #48
                stp x20, x19, [sp, #-32]!
                b {site+4}
              camera_done:
                ldp x29, x30, [sp], #48
                ret
            ''')
            assert original[site:site+4]==asm('stp x20,x19,[sp,#-32]!',site)
            patch(site,asm(f'b {camera_addr}',site),f'V{i+1} pace manual camera axis {axis} without slowing auto-follow or game')
            camera_hooks.append(dict(variant=i,axis=axis,site=site,hook=camera_addr,**cm))
        # Home menu category 0 ends with Quay số at index 5. Extend only
        # this array and add the new action at index 6, preserving both
        # the existing lottery and V9's original Xem giờ action/label.
        assert original[m['home_count']:m['home_count']+4]==original[0x53c0c8:0x53c0cc]
        patch(m['home_count'],asm('mov w1, #7',0),f'V{i+1} home menu has seven entries')
        append_addr,_=emit(f'''
            stp x29, x30, [sp, #-32]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            bl {0x12e7f74}
            ldr x0, [sp, #16]
            bl {label_addr}
            mov x3, x0
            ldp x0, x1, [sp, #16]
            mov w2, #6
            bl {0x12e7f74}
            ldp x29, x30, [sp], #32
            ret
        ''')
        assert original[m['home_append_call']:m['home_append_call']+4]==asm(f'bl {0x12e7f74}',m['home_append_call'])
        patch(m['home_append_call'],asm(f'bl {append_addr}',m['home_append_call']),f'V{i+1} append lucky wheel immediately after Quay số')
        select_addr,_=emit(f'''
            sub w16, w9, #6
            cbnz w16, original
            ldr x16, [x24]
            strb wzr, [x16, #0x9f]
            mov x0, x19
            bl {open_addr}
            b {m['home_after_action']}
          original:
            cbnz w9, nonzero
            b {m['home_select_zero']}
          nonzero:
            b {m['home_select']+4}
        ''')
        assert original[m['home_select']:m['home_select']+4]==asm(f"cbz w9, {m['home_select_zero']}",m['home_select'])
        patch(m['home_select'],asm(f'b {select_addr}',m['home_select']),f'V{i+1} select the new wheel row')
        width_hooks=[];width_functions={}
        for w in m['home_widths']:
            key=(w['reg'],w['kind']);default=3 if w['kind']=='columns' else -152 if w['kind']=='negative' else 152
            if key not in width_functions:
                after='mov w%d, w17'%w['reg']
                if w['kind']!='columns':after='lsl w17, w17, #5; add w17, w17, #56; '+('neg w17, w17; 'if w['kind']=='negative'else '')+after
                address,_=emit(f'''
                    stp x15, x16, [sp, #-32]!
                    str x17, [sp, #16]
                    mrs x15, nzcv
                    mov w{w['reg']}, #{default}
                    adrp x16, {m['home_class']&-4096}
                    add x16, x16, #{m['home_class']&4095}
                    ldr x16, [x16]
                    ldr w17, [x16, #216]
                    cmp w17, #1
                    b.ne done
                    ldr w17, [x16, #220]
                    cbnz w17, done
                    adrp x16, {m['width_class']&-4096}
                    add x16, x16, #{m['width_class']&4095}
                    ldr x16, [x16]
                    ldr w17, [x16, #304]
                    sub w17, w17, #64
                    asr w17, w17, #5
                    mov w16, #3
                    cmp w17, #3
                    csel w17, w17, w16, ge
                    mov w16, #5
                    cmp w17, #5
                    csel w17, w17, w16, le
                    {after}
                  done:
                    msr nzcv, x15
                    ldr x17, [sp, #16]
                    ldp x15, x16, [sp], #32
                    ret
                ''')
                width_functions[key]=address
            address=width_functions[key]
            expected=original[0x53cb98:0x53cb9c] if w['kind']=='columns' else asm(f"mov w{w['reg']}, #{default}",0)
            assert original[w['site']:w['site']+4]==expected
            patch(w['site'],asm(f'bl {address}',w['site']),f'V{i+1} fit home wheel label ({w["kind"]}, w{w["reg"]})')
            width_hooks.append(dict(**w,hook=address))
        assert original[m['room_title_site']:m['room_title_site']+4]==asm('ldr x8, [x8, #16]',0)
        patch(m['room_title_site'],asm(f'bl {room_title_addr}',m['room_title_site']),f'V{i+1} display exact reference-video title by actual room ID')
        receive_addr,raw=emit(f'''
            stp x29, x30, [sp, #-48]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            str x2, [sp, #32]
            {lookup('AGCorpseReceive',40)}
            cbz x10, corpse_observed
            ldr x0, [sp, #16]
            ldr x1, [sp, #32]
            mov w2, #{i}
            blr x10
            cbz w0, corpse_observed
            ldp x29, x30, [sp], #48
            ret
          corpse_observed:
            {lookup('AGTurnReceive',33)}
            cbz x10, turn_observed
            ldr x0, [sp, #16]
            ldr x1, [sp, #32]
            mov w2, #{i}
            blr x10
            ldr x9, [sp, #32]
            cbz x9, turn_observed
            ldrsb w9, [x9, #48]
            cmn w9, #115
            b.ne turn_observed
            ldp x29, x30, [sp], #48
            ret
          turn_observed:
            ldp x0, x1, [sp, #16]
            ldr x2, [sp, #32]
            ldp x29, x30, [sp], #48
            cbz x2, original
            ldrsb w9, [x2, #48]
            cmp w9, #106
            b.eq notes77
            cmp w9, #20
            b.eq notes77
            cmn w9, #101
            b.eq wheel
            cmn w9, #122
            b.eq notes77
            cmn w9, #123
            b.eq notes77
            cmn w9, #19
            b.ne original
            stp x29, x30, [sp, #-48]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            str x2, [sp, #32]
            {lookup('AGRoomReceive',3)}
            cbz x10, fallback
            ldr x0, [sp, #16]
            ldr x1, [sp, #32]
            mov w2, #{i}
            blr x10
            cbz w0, fallback
            ldp x29, x30, [sp], #48
            ret
          notes77:
            stp x29, x30, [sp, #-48]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            str x2, [sp, #32]
            {lookup('AGNotesReceive',27)}
            cbz x10, fallback
            ldr x0, [sp, #16]
            ldr x1, [sp, #32]
            mov w2, #{i}
            blr x10
            ldr x9, [sp, #32]
            ldrsb w9, [x9, #48]
            cmp w9, #106
            b.eq fallback
            cmp w9, #20
            b.eq fallback
            ldp x29, x30, [sp], #48
            ret
          wheel:
            stp x29, x30, [sp, #-48]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            str x2, [sp, #32]
            {lookup('AGWheelReceive',2)}
            cbz x10, fallback
            ldr x0, [sp, #16]
            ldr x1, [sp, #32]
            mov w2, #{i}
            blr x10
            ldp x29, x30, [sp], #48
            ret
          fallback:
            ldp x0, x1, [sp, #16]
            ldr x2, [sp, #32]
            ldp x29, x30, [sp], #48
          original:
            stp x28, x27, [sp, #-96]!
            b {m['controller']+4}
        ''')
        assert original[m['controller']:m['controller']+4]==asm('stp x28, x27, [sp, #-96]!',0)
        patch(m['controller'],asm(f'b {receive_addr}',m['controller']),f'V{i+1} receive wheel -101 and cache room names -19')
        corpse=corpse_maps[i];site=corpse['update'];first=original[site:site+4]
        assert first.hex()==corpse['first'] and first==asm('stp x28, x27, [sp, #-80]!',0)
        corpse_hook,_=emit(f'''
            stp x29, x30, [sp, #-48]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            {lookup('AGCorpseUpdate',41)}
            cbz x10, corpse_native_update
            ldp x0, x1, [sp, #16]
            mov w2, #{i}
            blr x10
            cbz w0, corpse_native_update
            ldp x29, x30, [sp], #48
            ret
          corpse_native_update:
            ldp x0, x1, [sp, #16]
            ldp x29, x30, [sp], #48
            stp x28, x27, [sp, #-80]!
            b {site+4}
        ''')
        patch(site,asm(f'b {corpse_hook}',site),f'V{i+1} keep dead airship parts out of live-flight state')
        corpse_hooks.append(dict(**corpse,hook=corpse_hook))
        change=turn_sequence[i]
        change_hook,_=emit(f"""
            stp x29, x30, [sp, #-48]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            {lookup('AGTurnChange',39)}
            cbz x10, native_change
            ldp x0, x1, [sp, #16]
            mov w2, #{i}
            blr x10
            cbz w0, deferred_change
            b changed
          native_change:
            ldp x0, x1, [sp, #16]
            bl {change['original']}
          changed:
            ldp x29, x30, [sp], #48
            ret
          deferred_change:
            ldp x29, x30, [sp], #48
            b {change['return_site']}
        """)
        assert original[change['site']:change['site']+4]==asm(f"bl {change['original']}",change['site'])
        patch(change['site'],asm(f'bl {change_hook}',change['site']),f'V{i+1} serialize UFO native turn handoff after previous effects')
        turn_change_hooks.append(dict(**change,hook=change_hook))
        fire_site=turn_map[i]['fire']
        fire_trampoline,_=emit(f'nop; b {fire_site+4}')
        rx[fire_trampoline-rxvm:fire_trampoline-rxvm+4]=original[fire_site:fire_site+4]
        fire_hook,_=emit(f'''
            stp x29, x30, [sp, #-32]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            {lookup('AGTurnManual',34)}
            cbz x10, fire_original
            mov w0, #{i}
            blr x10
          fire_original:
            ldp x0, x1, [sp, #16]
            ldp x29, x30, [sp], #32
            b {fire_trampoline}
        ''')
        patch(fire_site,asm(f'b {fire_hook}',fire_site),f'V{i+1} cancel queued UFO aim on native manual fire')
        for wait in turn_map[i]['waits']:
            site=wait['site'];kind=wait['kind'];actor=wait['actor_offset']
            load_actor=f"{'ldur' if actor<0 else 'ldr'} w9, [{wait['actor_register']}, #{actor}]" if kind in (2,3) else 'mov w9, #-1'
            wait_hook,_=emit(f'''
                {load_actor}
                stp x29, x30, [sp, #-48]!
                mov x29, sp
                stp x0, x1, [sp, #16]
                str w9, [sp, #32]
                {lookup('AGBattleAwait',38)}
                cbz x10, old_wait
                ldp x0, x1, [sp, #16]
                mov w2, #{i}
                mov w3, #{kind}
                ldr w4, [sp, #32]
                blr x10
                b wait_done
              old_wait:
                ldp x0, x1, [sp, #16]
                bl {0xaaa6e8}
              wait_done:
                ldp x29, x30, [sp], #48
                ret
            ''')
            assert original[site:site+4]==asm(f'bl {0xaaa6e8}',site)
            patch(site,asm(f'bl {wait_hook}',site),f'V{i+1} UFO predicate wait kind {kind}; preserve native monitor')
            turn_wait_hooks.append(dict(variant=i,hook=wait_hook,**wait))
        # Turn33.pulse is called after the arena update in the working JAR.
        # Hook both native update entries, preserving the original method,
        # Env, this and callee-saved registers. The ticket makes two callbacks
        # idempotent when one update calls the other.
        for update in presentation[i]['arena_updates']:
            site=update['entry'];first=original[site:site+4]
            assert struct.unpack('<I',first)[0]&0xffc003e0==0xa98003e0,(hex(site),first.hex())
            trampoline,_=emit(f'nop; b {site+4}')
            rx[trampoline-rxvm:trampoline-rxvm+4]=first
            update_hook,_=emit(f'''
                stp x29, x30, [sp, #-48]!
                mov x29, sp
                stp x0, x1, [sp, #16]
                bl {trampoline}
                str x0, [sp, #32]
                {lookup('AGTurnPulse',36)}
                cbz x10, arena_done
                ldr x0, [sp, #16]
                mov w1, #{i}
                blr x10
              arena_done:
                ldr x0, [sp, #32]
                ldp x29, x30, [sp], #48
                ret
            ''')
            patch(site,asm(f'b {update_hook}',site),f'V{i+1} process UFO aim after native arena {update["method"]} update')
            arena_update_hooks.append(dict(variant=i,site=site,hook=update_hook,trampoline=trampoline,first=first.hex(),method=update['method']))
        build_addr,raw=emit(f'''
            stp x29, x30, [sp, #-48]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            bl {m['room_build']}
            str x0, [sp, #32]
            {lookup('AGRoomRebuild',4)}
            cbz x10, done
            ldp x0, x1, [sp, #16]
            mov w2, #{i}
            blr x10
          done:
            ldr x0, [sp, #32]
            ldp x29, x30, [sp], #48
            ret
        ''')
        assert original[m['room_build_call']:m['room_build_call']+4]==asm(f"bl {m['room_build']}",m['room_build_call'])
        patch(m['room_build_call'],asm(f'bl {build_addr}',m['room_build_call']),f'V{i+1} replay names after room list rebuild')
        # The original level-10 calculation still calls Thread.sleep(0).
        # At that level bypass its scheduler yield; all lower levels retain
        # their original delay calculation, and no gameplay tick is duplicated.
        speed_tail=m['tick']+0x64
        word=struct.unpack_from('<I',original,speed_tail)[0]
        assert word&0xfc000000==0x14000000
        imm=word&0x3ffffff
        sleep_start=speed_tail+4*(imm-(1<<26) if imm&(1<<25) else imm)
        speed_resume=sleep_start+0x14
        assert original[sleep_start:sleep_start+16]==asm('str x8,[sp,#0xe8]; str w23,[sp,#0x18]; ldr x1,[sp,#0xe8]; mov x0,x19',sleep_start)
        assert original[speed_resume:speed_resume+4]==asm('str wzr,[sp,#0x18]',speed_resume)
        tick_addr,raw=emit(f'''
            stp x29, x30, [sp, #-32]!
            mov x29, sp
            str x0, [sp, #16]
            {lookup('AGWheelTick',1)}
            cbz x10, original
            ldr x0, [sp, #16]
            mov w1, #{i}
            blr x10
          original:
            ldr x0, [sp, #16]
            bl {m['speed']}
            cmp w0, #10
            b.eq maximum_speed
            ldp x29, x30, [sp], #32
            ret
          maximum_speed:
            ldp x29, x30, [sp], #32
            b {speed_resume}
        ''')
        assert original[m['tick']:m['tick']+4]==asm(f"bl {m['speed']}",m['tick'])
        patch(m['tick'],asm(f'bl {tick_addr}',m['tick']),f'V{i+1} poll/send on original game thread')
        # A single typed bridge adds the seventh native configuration row,
        # without replacing the six existing setting implementations.
        def setting_hook(stage,site):
            trampoline,traw=emit(f"nop; b {site+4}")
            rawfirst=original[site:site+4]
            assert struct.unpack("<I",rawfirst)[0]&0xffc003e0==0xa98003e0, (hex(site),rawfirst.hex())
            rx[trampoline-rxvm:trampoline-rxvm+4]=rawfirst
            before=f"bl {trampoline}" if stage in (0,2) else ''
            after=f"bl {trampoline}" if stage in (1,3) else ''
            address,_=emit(f'''
                stp x29, x30, [sp, #-48]!
                mov x29, sp
                stp x0, x1, [sp, #16]
                str x2, [sp, #32]
                {before}
                {lookup('AGNotesSettings',29)}
                cbz x10, fallback
                ldp x0, x1, [sp, #16]
                ldr x2, [sp, #32]
                mov w3, #{i}
                mov w4, #{stage}
                blr x10

              fallback:
                ldp x0, x1, [sp, #16]
                ldr x2, [sp, #32]
                {after}
              done:
                ldp x29, x30, [sp], #48
                ret
            ''')
            patch(site,asm(f'b {address}',site),f'V{i+1} Notes77 configuration stage {stage}')
            return dict(stage=stage,site=site,hook=address,trampoline=trampoline)
        config_hooks=[]
        for stage,key in enumerate(['settings_begin','settings_input','settings_paint','settings_ok']):
            config_hooks.append(setting_hook(stage,n[key]))
        origin=n['settings_origin']+12
        assert original[origin:origin+4]==asm('sub w0, w0, #94',0)
        patch(origin,asm('sub w0, w0, #110',0),f'V{i+1} center seven configuration rows')
        input_hooks=[]
        for kind,site in enumerate(n['input']):
            # Copy the exact first instruction; no PC-relative prologues.
            first=original[site:site+4]
            # key methods save x22/x21, pointer methods use different but
            # non-relative stack prologues or a MOV/STR instruction.
            trampoline,raw=emit('nop; b '+str(site+4))
            if kind>=2:
                page=n['canvas']&-4096
                assert first==asm(f'adrp x8, {page}',site)
                first=asm(f'adrp x8, {page}',trampoline)
            rx[trampoline-rxvm:trampoline-rxvm+4]=first
            address,_=emit(f'''
                stp x29, x30, [sp, #-48]!
                mov x29, sp
                stp x0, x1, [sp, #16]
                stp x2, x3, [sp, #32]
                {lookup('AGNotesInput',28)}
                cbz x10, original
                mov w0, #{i}
                mov w1, #{kind}
                ldr w2, [sp, #32]
                ldr w3, [sp, #40]
                blr x10
                cbnz w0, done
              original:
                ldp x0, x1, [sp, #16]
                ldp x2, x3, [sp, #32]
                bl {trampoline}
              done:
                ldp x29, x30, [sp], #48
                ret
            ''')
            patch(site,asm(f'b {address}',site),f'V{i+1} modal input guard {kind}')
            input_hooks.append(dict(kind=kind,site=site,hook=address,trampoline=trampoline))
        inbox_site=n['inbox_open']
        assert original[inbox_site:inbox_site+4]==asm(f"bl {n['dialog_show']}",inbox_site)
        inbox_addr,_=emit(f'''
            stp x29, x30, [sp, #-80]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            stp x2, x3, [sp, #32]
            stp x4, x5, [sp, #48]
            bl {n['dialog_show']}
            {lookup('AGNotesInbox',30)}
            cbz x10, done
            ldp x0, x1, [sp, #16]
            ldr x2, [sp, #32]
            mov w3, #{i}
            blr x10
          done:
            ldp x29, x30, [sp], #80
            ret
        ''')
        patch(inbox_site,asm(f'bl {inbox_addr}',inbox_site),f'V{i+1} retain full inbox text and original dialog actions')
        hooks.append(dict(notes77=n,config_hooks=config_hooks,input_hooks=input_hooks,inbox_hook=inbox_addr,speed_resume=speed_resume,variant=i,open_hook=open_addr,receive_hook=receive_addr,tick_hook=tick_addr,room_build_hook=build_addr,home_append_hook=append_addr,home_select_hook=select_addr,width_hooks=width_hooks,v9_hook=v9_addr,clock_hook=clock_addr,move_hook=move_addr,callback_slot=callback_slot,**m))
    # Notes78: only the third UTF in login changes. Registration, credentials,
    # platform tail and every other service packet retain their native path.
    release=json.loads((ROOT/'login-map.json').read_text())
    marker=symbols['2.4.1-HG78-IPA'];cache=rwvm+248
    login_hook,_=emit(f'''
        stp x29, x30, [sp, #-32]!
        mov x29, sp
        stp x0, x1, [sp, #16]
        adrp x1, {cache&-4096}
        add x1, x1, #{cache&4095}
        adrp x2, {marker&-4096}
        add x2, x2, #{marker&4095}
        mov w3, #{len('2.4.1-HG78-IPA')}
        bl {0x12e8038}
        mov x2, x0
        ldp x0, x1, [sp, #16]
        ldp x29, x30, [sp], #32
        b {release['write_utf']}
    ''')
    for i,v in enumerate(release['variants']):
        at=v['utf_calls'][2]
        assert old[at:at+4]==asm(f"bl {release['write_utf']}",at)
        patch(at,asm(f'bl {login_hook}',at),f'V{i+1} Notes78 login build marker')
    # Area IDs are an unsigned protocol byte. Keep the byte on the wire;
    # remove sign extension only at numeric labels and area-index reads.
    for z in json.loads((ROOT/'zone-map.json').read_text()):
        i=z['variant'];site=z['row_id_load']
        assert original[site:site+4]==asm('ldrsb w2, [x8, #0x1d]',site)
        patch(site,asm('ldrb w2, [x8, #0x1d]',site),f'V{i+1} unsigned area number in list (128..255)')
        zone_patches.append(dict(variant=i,site=site,kind='list'))
        site=z['title_id_arg'];assert original[site:site+4]==asm('mov w2, w22',site)
        patch(site,asm('uxtb w2, w22',site),f'V{i+1} unsigned area number in formatted title')
        zone_patches.append(dict(variant=i,site=site,kind='title'))
        pm=presentation[i]
        for site in range(pm['room_paint'],pm['room_paint']+pm['room_paint_size'],4):
            word=struct.unpack_from('<I',original,site)[0]
            if word&0xffc00000==0x39c00000 and (word>>10)&4095==0x132:
                raw=struct.pack('<I',word&~0x00800000)
                patch(site,raw,f'V{i+1} unsigned waiting-room area label/index')
                zone_patches.append(dict(variant=i,site=site,kind='waiting'))
    at=release['version_offset']
    assert old[at:at+6]==b'2.4.0\0'
    patch(at,b'2.4.1','Native version label 2.4.1')
    b[rxoff:rxoff+PAGE]=rx
    # Relocate only link-edit FILE offsets; no original text/data VM address
    # changes. Existing rebases/bindings target segment 1/2, never LINKEDIT.
    load=[]
    file_fields={2:[8,16],11:[32,40,48,56,64,72],0x22:[8,16,24,32,40],0x80000022:[8,16,24,32,40],0x26:[8],0x29:[8],0x2e:[8],0x1e:[8]}
    for p,cmd,size in cmds:
        c=bytearray(old[p:p+size])
        if p==link_p:
            load.append(segment('__AGWHEEL',rxvm,rxoff,PAGE,5,[('__text',rxvm,rxoff,CODE_LIMIT,0x80000400,2),('__cstring',rxvm+CODE_LIMIT,rxoff+CODE_LIMIT,strcursor-CODE_LIMIT,2,0)]))
            load.append(segment('__AGDATA',rwvm,rwoff,PAGE,3,[('__data',rwvm,rwoff,512,0,3)]))
            struct.pack_into('<Q',c,24,link[1]+delta);struct.pack_into('<Q',c,40,rxoff+delta)
        for field in file_fields.get(cmd,[]):
            value=struct.unpack_from('<I',c,field)[0]
            if value:
                assert value>=rxoff,(hex(cmd),field,hex(value));struct.pack_into('<I',c,field,value+delta)
        if cmd==25:
            for j in range(struct.unpack_from('<I',c,64)[0]):
                q=72+80*j;reloc=struct.unpack_from('<I',c,q+56)[0]
                if reloc:assert reloc>=rxoff;struct.pack_into('<I',c,q+56,reloc+delta)
        load.append(bytes(c))
    dylib=b'@executable_path/Frameworks/AGWheel.dylib\0';sz=align(24+len(dylib))
    # clang's default LC_ID_DYLIB version is 0.0.0. Do not demand 1.0.0
    # here: dyld would reject the correctly built module as incompatible.
    load.append(struct.pack('<6I',12,sz,24,0,0,0)+dylib+bytes(sz-24-len(dylib)))
    header=b''.join(load);assert 32+len(header)<0x8000
    b[32:32+len(header)]=header;struct.pack_into('<II',b,16,len(load),len(header))
    return bytes(b),dict(hooks=hooks,patches=records,rxvm=rxvm,rxoff=rxoff,rwvm=rwvm,rwoff=rwoff,code_size=cursor,dlsym=dlsym,linkedit_shift=delta,label_hook=label_addr,room_title_hook=room_title_addr,room_reference_titles=REFERENCE_TITLES,boss_hooks=boss_hooks,footer_hooks=footer_hooks,canvas_footer_hooks=canvas_footer_hooks,camera_hooks=camera_hooks,blind_hooks=blind_hooks,corpse_hooks=corpse_hooks,arena_update_hooks=arena_update_hooks,turn_wait_hooks=turn_wait_hooks,turn_change_hooks=turn_change_hooks,zone_patches=zone_patches,turn_map=turn_map,keypad_hook=keypad_hook,keypad_paint=keypad_paint,grid_hook=grid_hook,grid_sites=grid_map["sites"],login_hook=login_hook,release_version='2.4.1',login_marker='2.4.1-HG78-IPA')

def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--dylib',type=Path,default=ROOT/'build/AGWheel.dylib');p.add_argument('--output',type=Path,default=Path('deliverables/Army2Hoanggia-LuckyWheel-Test.ipa'));args=p.parse_args()
    source=Path('deliverables/Army2Hoanggia-Room-Clan-Fix.ipa');assert hashlib.sha256(source.read_bytes()).hexdigest()==EXPECTED_IPA
    with zipfile.ZipFile(source)as z:old=z.read(APP+'Army2Hoanggia')
    original=Path('inspect-ipa/Army2Hoanggia').read_bytes();maps=json.loads((ROOT/'native-map.json').read_text())
    native,report=build_native(old,original,maps);(ROOT/'build').mkdir(exist_ok=True)
    (ROOT/'build/prepared-native').write_bytes(native);(ROOT/'build/hook-report.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.prepare:print('Prepared native hooks only. No IPA has been created.');return
    lib=args.dylib.read_bytes();assert lib[:4]==bytes.fromhex('cffaedfe')
    assert struct.unpack_from('<I',lib,4)[0]==0x100000c
    assert struct.unpack_from('<I',lib,12)[0]==6 # MH_DYLIB
    versions=[struct.unpack_from('<II',lib,p+8)for p,c,s in commands(lib)if c==0x32]
    assert versions and all(platform==2 and minimum<=0xc0000 for platform,minimum in versions),'Require device iOS dylib supporting iOS 12'
    for name in (b'_AGWheelOpen\0',b'_AGWheelReceive\0',b'_AGWheelTick\0',b'_AGRoomReceive\0',b'_AGRoomRebuild\0',b'_AGMoveAllow\0'):assert name in lib
    assert b'_AGWheelPreview'not in lib,'Simulator fixture must not enter IPA'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(source)as src,zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as dst:
        for info in src.infolist():
            if '/_CodeSignature/'in info.filename or info.filename.endswith('embedded.mobileprovision'):continue
            dst.writestr(info,native if info.filename==APP+'Army2Hoanggia'else src.read(info.filename))
        info=zipfile.ZipInfo(APP+'Frameworks/AGWheel.dylib');info.create_system=3;info.external_attr=0o100755<<16;info.compress_type=zipfile.ZIP_DEFLATED;dst.writestr(info,lib)
    print(args.output,hashlib.sha256(args.output.read_bytes()).hexdigest())
if __name__=='__main__':main()



