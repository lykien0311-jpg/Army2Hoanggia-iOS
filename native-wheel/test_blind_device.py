"""Apple ARM64 packet observer -> installed native painter -> white draw/HUD.

The real Graphics translate/clip/color methods execute. Only the final GPU fill
and unrelated world/HUD backends are controlled boundaries. No live account.
"""
import json,struct
import lief
import test_device_bridge as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.u;B=t.MAIN;R=t.ROOT
prepared=(R/'build/prepared-native').read_bytes();report=json.loads((R/'build/hook-report.json').read_text())
turns=json.loads((R/'turn-map.json').read_text());notes=json.loads((R/'notes-map.json').read_text())
pm=lief.MachO.parse(str(R/'build/prepared-native')).at(0)
last=max(end+1 for start,end,perms in U.mem_regions() if B<=start<B+0x4000000)
for seg in pm.segments:
    if seg.name=='__PAGEZERO':continue
    end=(seg.virtual_address+seg.virtual_size+4095)&-4096
    if end>last:U.mem_map(last,end-last);last=end
    if seg.file_size:U.mem_write(seg.virtual_address,prepared[seg.file_offset:seg.file_offset+seg.file_size])
stop=mode_get=0;fills=[];throw_fill=False
def hook(uc,pc,size,_):
    if pc==B+report['dlsym']:
        name=bytes(U.mem_read(t.reg(1),100)).split(b'\0')[0].decode();t.ret(t.symbols['_'+name]);return
    if pc==stop:U.emu_stop();return
    if pc==mode_get:t.ret(0);return
    if pc==B+0x1c6170:
        g=t.reg(1)
        fills.append(dict(rect=[t.reg(i) for i in range(2,6)],
            rgba=list(struct.unpack('<4f',U.mem_read(g+0x28,16))),
            clip=list(struct.unpack('<4i',U.mem_read(g+0x38,16))),
            translation=list(struct.unpack('<2i',U.mem_read(g+0x48,8)))))
        if throw_fill:
            t.put(t.ENV+0x10,'<Q',t.HEAP+0x800)
            U.reg_write(UC_ARM64_REG_X0,t.get(t.ENV+0x38,'<Q'))
            U.reg_write(UC_ARM64_REG_PC,B+0x1300d9c)
        else:t.ret()
        return
    t.hook(uc,pc,size,_)
U.hook_del(t.BASE_HOOK);U.hook_add(UC_HOOK_CODE,hook)
def execute(pc,*args):
    U.mem_write(t.STACK+0x2f000,b'\xa5'*0x1000)
    U.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000);U.reg_write(UC_ARM64_REG_LR,t.STOP)
    for i,a in enumerate(args):U.reg_write(UC_ARM64_REG_X0+i,a&((1<<64)-1))
    U.emu_start(pc,t.STOP+4,count=300000)
    assert U.reg_read(UC_ARM64_REG_PC) in (stop,t.STOP)
    assert t.lockDepth==0 and t.get(t.ENV+0x10,'<Q')==0
def active(v):return t.call('_AGBlindActive',v)
def packet(v,state,target):
    global stop
    msg=t.message(bytes([state,target]));t.put(msg+0x30,'<B',106)
    stream=t.get(msg+0x20,'<Q');saved=bytes(U.mem_read(stream,0x30))
    stop=B+report['hooks'][v]['controller']+4
    execute(B+report['hooks'][v]['controller'],t.ENV,t.HEAP+0x9000,msg)
    assert bytes(U.mem_read(stream,0x30))==saved,'Observer consumed or changed native reader'
    assert U.reg_read(UC_ARM64_REG_SP)==t.STACK+0x30000-96
    stop=0
checks=0
for v,bm in enumerate(report['blind_hooks']):
    glob=t.alloc(0x400);canvas=t.alloc(0x300);arena=t.alloc(0x200);graphics=t.alloc(0x100)
    t.put(B+turns[v]['arena_class'],'<Q',glob);t.put(B+notes[v]['canvas'],'<Q',canvas)
    t.put(glob+0xe8,'<Q',arena);t.put(canvas+0xb8,'<Q',arena)
    t.put(canvas+0x130,'<i',320);t.put(canvas+0x128,'<i',480)
    # This getter is the native HUD border mode. Keep the ordinary HUD path.
    word=int.from_bytes(prepared[bm['hud']+0x44:bm['hud']+0x48],'little')
    imm=word&0x3ffffff;mode_get=B+bm['hud']+0x44+4*(imm-(1<<26) if imm&(1<<25) else imm)
    for local in (0,7):
        t.put(glob+0x266,'<B',local)
        start=t.message(b'');t.put(start+0x30,'<B',20);t.call('_AGBlindReceive',t.ENV,start,v);assert not active(v)
        packet(v,0,(local+1)%8);assert not active(v)
        packet(v,0,local);assert active(v)
        packet(v,1,(local+1)%8);assert active(v)
        for time in (100.,1000000.):
            t.now=time;t.call('_AGBlindTick',v);assert active(v)
        for fail in (False,True):
            throw_fill=fail;fills.clear()
            U.mem_write(graphics+0x28,struct.pack('<4f',.2,.3,.4,.5))
            U.mem_write(graphics+0x38,struct.pack('<6i',5,7,50,40,13,-9)+bytes([1,1,0,0]))
            saved=bytes(U.mem_read(graphics+0x28,0x2c))
            stop=B+(bm['site']+4 if fail else bm['hud_first_widget'])
            execute(B+bm['paint'],t.ENV,arena,graphics)
            assert len(fills)==1 and fills[0]==dict(rect=[0,0,320,480],rgba=[1.,1.,1.,1.],clip=[0,0,320,480],translation=[0,0]),fills
            if fail:assert bytes(U.mem_read(graphics+0x28,0x2c))==saved,'Java throw did not restore Graphics state'
            else:
                assert bytes(U.mem_read(graphics+0x28,16))==saved[:16],'Blind mask changed HUD color'
                assert struct.unpack('<6i',U.mem_read(graphics+0x38,24))==(0,0,320,480,0,0)
            checks+=1
        stop=0;throw_fill=False
        packet(v,1,local);assert not active(v)
        fills.clear();stop=B+bm['site']+4;execute(B+bm['paint'],t.ENV,arena,graphics)
        assert not fills;checks+=1;stop=0
        # Truncated data cannot set blindness, including nonzero reader offset.
        msg=t.message(b'\0');t.put(msg+0x30,'<B',106);t.call('_AGBlindReceive',t.ENV,msg,v);assert not active(v)
        packet(v,0,local);t.put(canvas+0xb8,'<Q',0);t.call('_AGBlindTick',v);assert not active(v)
        t.put(canvas+0xb8,'<Q',arena);packet(v,0,local);t.call('_AGBlindReceive',t.ENV,start,v);assert not active(v)
        checks+=5
report_out=dict(passed=True,apple_native_cases=checks,variants=6,local_slots=[0,7],
    protocol=106,wire_order=['state','target'],original_reader_unchanged=True,
    white_rectangle=[0,0,320,480],opaque_white=True,actual_native_graphics_state_methods=True,
    original_HUD_entry_executed=True,graphics_restored_on_Java_exception=True,
    new_match_exit_and_server_clear_reset=True,live_requests=0)
(R/'build/blind-device-check.json').write_text(json.dumps(report_out,indent=2)+'\n');print('PASS',report_out)
