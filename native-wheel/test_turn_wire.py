"""Run Apple UFO bridge -> installed fire hook -> original native shot writer.

Only JVM/OS primitives, harmless debug strings, and the final transport are
mocked. The actual player firing body and Service packet construction execute.
The resulting command 22 bytes must match the server's shootMessage reader.
"""
import json,struct
import lief
import test_device_bridge as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *

U=t.u;B=t.MAIN;ROOT=t.ROOT
X=[UC_ARM64_REG_X0+i for i in range(31)]
raw=(ROOT.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes()
prepared=(ROOT/'build/prepared-native').read_bytes()
report=json.loads((ROOT/'build/hook-report.json').read_text())
turns=json.loads((ROOT/'turn-map.json').read_text())
notes=json.loads((ROOT/'notes-map.json').read_text())
pm=lief.MachO.parse(str(ROOT/'build/prepared-native')).at(0)
last=max(e+1 for a,e,p in U.mem_regions() if B<=a<B+0x4000000)
for seg in pm.segments:
    if seg.name=='__PAGEZERO':continue
    end=(seg.virtual_address+seg.virtual_size+4095)&-4096
    if end>last:U.mem_map(last,end-last);last=end
    if seg.file_size:U.mem_write(seg.virtual_address,prepared[seg.file_offset:seg.file_offset+seg.file_size])

def branch(off):
    word=struct.unpack_from('<I',raw,off)[0];assert word&0xfc000000==0x94000000
    n=word&0x3ffffff;return off+4*(n-(1<<26)if n&(1<<25)else n)
def r(i):return U.reg_read(X[i])
def ret(value=0):t.ret(value)
primitives={B+0x12e8038:'string',B+0xab96d8:'append'};packets=[];commands={}

# Replace the original transport fixture so command 22 can share its JVM
# allocation primitives with the pre-existing wheel command -101 tests.
U.hook_del(t.BASE_HOOK)
def hook(uc,pc,size,_):
    if pc==B+report['dlsym']:
        name=bytes(U.mem_read(r(1),100)).split(b'\0')[0].decode()
        ret(t.symbols['_'+name]);return
    if pc in primitives:
        kind=primitives[pc]
        if kind=='builder':ret(t.alloc(0x40))
        elif kind=='string':ret(t.alloc(0x20))
        elif kind=='append':ret(r(1))
        elif kind in ('bullet','variant','secondary'):ret(0)
        elif kind=='writer':ret(t.get(r(1)+0x18,'<Q'))
        elif kind=='short':t.writers[r(1)].extend(struct.pack('>H',r(2)&65535));ret()
        elif kind=='close':ret()
        else:raise AssertionError(kind)
        return
    if pc in t.native:
        kind,v=t.native[pc]
        if kind=='ctor':
            msg=r(1);commands[msg]=r(2)&255;writer=t.alloc(0x40)
            t.put(msg+0x18,'<Q',writer);t.writers[writer]=bytearray();ret();return
        if kind=='send':
            assert r(1)==t.get(t.SERVICE+0x10,'<Q')
            msg=r(2);writer=t.get(msg+0x18,'<Q');packets.append((commands[msg],bytes(t.writers[writer])));ret();return
    if pc==t.symbols['_AGNotesBlocksAuto']:ret(0);return
    t.hook(uc,pc,size,_)
U.hook_add(UC_HOOK_CODE,hook)

def call(name,*args):
    U.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000);U.reg_write(UC_ARM64_REG_LR,t.STOP)
    for i,value in enumerate(args):U.reg_write(X[i],value&((1<<64)-1))
    U.emu_start(t.symbols['_'+name],t.STOP+4,count=200000)
    assert U.reg_read(UC_ARM64_REG_PC)==t.STOP

def receive(v,cmd,wire):
    msg=t.message(wire);t.put(msg+0x30,'<B',cmd&255);call('AGTurnReceive',t.ENV,msg,v)
    stream=t.get(msg+0x20,'<Q');assert t.get(stream+0x20,'<I')==0

cases=0
for v,m in enumerate(turns):
    fire=m['fire'];helper=branch(fire+0x1f4);service=branch(helper+0xd0)
    # These addresses are derived from the actual native call sites for each
    # variant, including the normal Service.shoot path and short writer.
    for at,kind in [(fire+0x50,'builder'),(fire+0x5c,'string'),(fire+0x6c,'append'),
                    (fire+0x80,'append'),(fire+0x90,'bullet'),(helper+0x30,'variant'),
                    (service+0xf0,'writer'),(service+0x16c,'short'),
                    (service+0x258,'secondary'),(service+0x33c,'close')]:
        primitives[B+branch(at)]=kind
    # Branches using shared StringBuilder primitives are safe to reuse.
    g=t.alloc(0x400);pg=t.alloc(0x400);ag=t.alloc(0x200);canvas=t.alloc(0x200)
    arena=t.alloc(0x200);array=t.alloc(0x200);player=t.alloc(0x200)
    for address,value in [(m['arena_class'],g),(m['player_class'],pg),(m['array_class'],ag),(notes[v]['canvas'],canvas)]:t.put(B+address,'<Q',value)
    t.put(g+0xe8,'<Q',arena);t.put(g+0x266,'<B',2);t.put(ag+0xa0,'<Q',array);t.put(ag+0xd0,'<B',2)
    t.put(canvas+0xb8,'<Q',arena);t.put(array+0x10,'<I',8);t.put(array+0x28,'<Q',player)
    t.put(t.SERVICE+0x10,'<Q',t.SESSION)
    receive(v,-115,struct.pack('>I',0x55464f01))
    for num,(x,y) in enumerate([(240,350),(500,200)],8):
        U.mem_write(pg+0x1a7,bytes(2));U.mem_write(player+0x166,bytes(1));U.mem_write(player+0x16a,bytes(1))
        t.put(player+0x80,'<i',110);t.put(player+0x84,'<i',90)
        t.put(player+0x114,'<i',x);t.put(player+0x118,'<i',y);t.put(player+0xa4,'<I',0x55aa0000)
        ticket=987654+num
        receive(v,24,bytes([2])+struct.pack('>IiQ',1429485652,num,ticket))
        receive(v,-115,struct.pack('>iBQHBBhh',num,2,ticket,173,28,0,x,y))
        packets.clear();call('AGTurnTick',t.ENV,v)
        expected=struct.pack('>BhhhBB',0,x,y,173,28,1)
        assert packets==[(22,expected)],(v,num,packets,expected.hex())
        assert t.get(player+0xa4,'<I')==173
        assert t.get(player+0x80,'<i')==110 and t.get(player+0x84,'<i')==90
        assert t.get(player+0x114,'<i')==x and t.get(player+0x118,'<i')==y
        call('AGTurnTick',t.ENV,v);assert packets==[(22,expected)]
        cases+=1
print('PASS:',cases,'Apple UFO-to-original-player-to-Service command22 wire cases; current origin after falling/movement, angle, force, exactly-once and native int32 position/angle fields')
