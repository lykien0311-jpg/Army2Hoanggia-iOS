"""Execute the Apple-compiled rebuilt auto and installed native hooks in ARM64.

The original native bullet mapper executes. JVM allocation, byte writes, clock,
modal state and final session queue are controlled boundaries. No live account,
server, iPhone or production combat is used by this test.
"""
import json,struct
from pathlib import Path
import capstone,lief
import test_device_bridge as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *

U=t.u;B=t.MAIN;ROOT=t.ROOT
X=[getattr(__import__('unicorn.arm64_const',fromlist=['']),f'UC_ARM64_REG_X{i}') for i in range(31)]
raw=(ROOT.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes()
prepared=(ROOT/'build/prepared-native').read_bytes()
report=json.loads((ROOT/'build/hook-report.json').read_text())
turns=json.loads((ROOT/'turn-map.json').read_text());notes=json.loads((ROOT/'notes-map.json').read_text())
main=lief.MachO.parse(str(ROOT/'build/prepared-native')).at(0)
end=max(e+1 for a,e,p in U.mem_regions() if B<=a<B+0x4000000)
for seg in main.segments:
    if seg.name=='__PAGEZERO':continue
    top=(seg.virtual_address+seg.virtual_size+4095)&-4096
    if top>end:U.mem_map(end,top-end);end=top
    if seg.file_size:U.mem_write(seg.virtual_address,prepared[seg.file_offset:seg.file_offset+seg.file_size])

packets=[];commands={};writer_commands={};fail_command=None;blocked=0;wheel=0
legacy=[];timed=[];watched=0;clear_after=3;leave_canvas=0
continuation=0;first=0
primitives={};phase_log=[];settling=False;settle_calls={};flying=False;flight_calls={}

def r(n):return U.reg_read(X[n])
def branch(a):
    word=struct.unpack_from('<I',raw,a)[0];assert word&0xfc000000==0x94000000
    delta=word&0x3ffffff
    if delta&(1<<25):delta-=1<<26
    return a+4*delta

def hook(uc,pc,size,_):
    global fail_command
    if settling and pc in settle_calls:t.ret(settle_calls[pc]);return
    if flying and pc in flight_calls:
        fn=flight_calls[pc];t.ret(fn() if callable(fn) else fn);return
    if pc in primitives:
        result=primitives[pc]();t.ret(0 if result is None else result);return
    if pc==B+report['dlsym']:
        name=bytes(U.mem_read(r(1),100)).split(b'\0')[0].decode();t.ret(t.symbols.get('_'+name,0));return
    if pc in (t.symbols['_AGNotesBlocksAuto'],t.symbols['_AGWheelSuppressFooter']):
        t.ret(blocked if pc==t.symbols['_AGNotesBlocksAuto'] else wheel);return
    if pc in t.native:
        kind,v=t.native[pc]
        if kind=='ctor':
            msg=r(1);commands[msg]=r(2)&255;writer=t.alloc(0x40)
            t.put(msg+0x18,'<Q',writer);t.writers[writer]=bytearray();writer_commands[writer]=commands[msg];t.ret();return
        if kind=='send':
            assert r(1)==t.get(t.SERVICE+0x10,'<Q')
            msg=r(2);writer=t.get(msg+0x18,'<Q');packets.append((commands[msg],bytes(t.writers[writer])));t.ret();return
    if pc==B+0xa64a3c:
        if fail_command is not None and writer_commands.get(r(1))==fail_command:
            fail_command=None
            t.put(t.ENV+0x10,'<Q',t.HEAP+0x800)
            U.reg_write(X[0],t.get(t.ENV+0x38,'<Q'));U.reg_write(UC_ARM64_REG_PC,B+0x1300d9c);return
        t.writers[r(1)].append(r(2)&255);t.ret();return
    if pc==B+0xaaa6e8:legacy.append((r(0),r(1)));t.ret();return
    if pc==B+0xaaa730:
        timed.append((r(0),r(1),r(2)));assert r(2)==16;t.now+=.016
        if leave_canvas:t.put(leave_canvas+0xb8,'<Q',0)
        elif clear_after is not None and len(timed)>=clear_after:t.put(watched,'<B',0)
        t.ret();return
    if pc==continuation:
        sp=U.reg_read(UC_ARM64_REG_SP);imm=(first>>15)&127;imm=imm-128 if imm&64 else imm
        U.reg_write(X[first&31],t.get(sp,'<Q'));U.reg_write(X[(first>>10)&31],t.get(sp+8,'<Q'))
        U.reg_write(UC_ARM64_REG_SP,sp-imm*8);t.ret();return
    t.hook(uc,pc,size,_)

U.hook_del(t.BASE_HOOK);U.hook_add(UC_HOOK_CODE,hook)
def call_address(address,*args):
    U.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000);U.reg_write(UC_ARM64_REG_LR,t.STOP)
    for i,arg in enumerate(args):U.reg_write(X[i],arg&((1<<64)-1))
    U.emu_start(address,t.STOP+4,count=2000000)
    assert U.reg_read(UC_ARM64_REG_PC)==t.STOP,hex(U.reg_read(UC_ARM64_REG_PC))
    assert t.lockDepth==0 and t.get(t.ENV+0x10,'<Q')==0 and t.get(t.ENV+0x38,'<Q')==0
    return r(0)
def call(name,*args):return call_address(t.symbols['_'+name],*args)
def receive(v,cmd,wire):
    msg=t.message(wire);t.put(msg+0x30,'<B',cmd&255);call('AGTurnReceive',t.ENV,msg,v)
    stream=t.get(msg+0x20,'<Q');assert t.get(stream+0x20,'<i')==0

def setup(v,room_id=8):
    m=turns[v];g=t.alloc(0x400);pg=t.alloc(0x400);ag=t.alloc(0x200);canvas=t.alloc(0x200)
    arena=t.alloc(0x200);array=t.alloc(0x200);p=t.alloc(0x200);boss=t.alloc(0x200)
    room=t.alloc(0x200);proj=t.alloc(0x200)
    for address,value in [(m['arena_class'],g),(m['player_class'],pg),(m['array_class'],ag),
        (m['projectile_class'],proj),(notes[v]['canvas'],canvas),(notes[v]['room_class'],room)]:t.put(B+address,'<Q',value)
    t.put(g+0xe8,'<Q',arena);t.put(g+0x266,'<B',2);t.put(ag+0xa0,'<Q',array);t.put(ag+0xd0,'<B',2)
    t.put(canvas+0xb8,'<Q',arena);t.put(array+0x10,'<i',10)
    t.put(array+0x18+2*8,'<Q',p);t.put(array+0x18+8*8,'<Q',boss)
    t.put(p+0x68,'<q',10000);t.put(boss+0x68,'<q',16000)
    t.put(p+0x114,'<i',240);t.put(p+0x118,'<i',350)
    t.put(p+0x11c,'<i',240);t.put(p+0x124,'<i',350)
    t.put(boss+0x114,'<i',500);t.put(boss+0x118,'<i',120)
    U.mem_write(room+0x130,bytes([room_id,5]));t.put(t.SERVICE+0x10,'<Q',t.SESSION)
    # Execute the real native bullet wrapper and its jump table. Only skip its
    # already-completed Java class initialization, as on an active game screen.
    mapper=branch(m['fire']+0x90)
    dis=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);dis.detail=True
    ins=list(dis.disasm(raw[mapper+0x10:mapper+0x18],B+mapper+0x10))
    assert ins[0].mnemonic=='adrp' and ins[1].mnemonic=='add'
    class_address=ins[0].operands[1].imm+ins[1].operands[2].imm
    t.put(class_address+9,'<B',2)
    # Item and UFO gravity flags stay set; actual flight and projectile
    # completion will be driven through the original native methods.
    for actor in (p,boss):
        for off in (0x16a,0x169):t.put(actor+off,'<B',1)
    t.put(pg+0x1a8,'<B',1);t.put(boss+0x166,'<B',1)
    receive(v,-115,struct.pack('>I',0x55464f01));receive(v,20,b'')
    for address in (m['arena_class'],m['array_class'],m['player_class'],m['projectile_class']):t.put(B+address+9,'<B',2)
    return dict(g=g,pg=pg,ag=ag,canvas=canvas,arena=arena,array=array,p=p,boss=boss,room=room,proj=proj,mapper=mapper)

def queue(v,num,owner=2):
    ticket=900000+num
    receive(v,24,bytes([owner])+struct.pack('>IiQ',1429485652,num,ticket))
    receive(v,-115,struct.pack('>iBQHBBhh',num,owner,ticket,173,28,13,240,350))
    return ticket

def pulse(v):call('AGTurnPulse',t.ENV,v)
def settle(v):pulse(v);t.now+=.061;pulse(v)
def expected(bullet):
    data=struct.pack('>BhhhB',bullet,240,350,173,28)
    if bullet in (17,19):data+=bytes([13])
    return 22,data+bytes([1])

