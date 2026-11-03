"""Run the original six ARM64 room builders, sorters, and title dispatch.

Only Java allocation/Vector primitives and display metric getters are mocked;
the room grouping, sorting, constructors, and title selection execute native
instructions from the user's exact IPA.
"""
import struct,json,random
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
ROOT=Path(__file__).resolve().parent
B=0x100000000;D=0x600000000;S=0x700000000;STOP=B+0x7000
raw=Path('review/patched-native').read_bytes();maps=json.loads((ROOT/'native-map.json').read_text())
u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(B,(len(raw)+4095)&-4096);u.mem_write(B,raw)
u.mem_map(D,0x400000);u.mem_map(S,0x40000)
def q(a,v):u.mem_write(a,struct.pack('<Q',v))
def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
def rq(a):return struct.unpack('<Q',u.mem_read(a,8))[0]
def rw(a):return struct.unpack('<I',u.mem_read(a,4))[0]
def branch(a):
    x=struct.unpack_from('<I',raw,a)[0];assert x&0xfc000000==0x94000000
    n=x&0x3ffffff;return a+4*(n-(1<<26) if n&(1<<25) else n)
heap=D+0x1000
def alloc(n=0x80):
    global heap
    p=heap;heap+=(n+15)&-16;u.mem_write(p,bytes(n));return p
def vector():
    v=alloc();a=alloc(0x18+512*8);q(v+0x18,a);w(a+0x10,512);return v
def values(v):return [rq(rq(v+0x18)+0x18+i*8) for i in range(rw(v+0x24))]
def store(v,items):
    w(v+0x24,len(items))
    for i,x in enumerate(items):q(rq(v+0x18)+0x18+i*8,x)
def ret(x=0):u.reg_write(UC_ARM64_REG_X0,x);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
def r(i):return u.reg_read(UC_ARM64_REG_X0+i) if i<29 else u.reg_read(UC_ARM64_REG_X29)
# X0...X28 are consecutive in Unicorn's ARM64 enum.
handlers={};endpoints=set();stopped=0
def hook(uc,pc,size,_):
    global stopped
    off=pc-B
    if off in handlers:handlers[off]()
    elif pc in endpoints:stopped=pc;u.emu_stop()
u.hook_add(UC_HOOK_CODE,hook)
empty=D+0x100;screen=D+0x200;env=D+0x300
group=lambda i:0 if i==0 else 1 if i==1 else 2 if i==2 else 4 if i==17 else 3
expected=[(255,0),(0,0),(255,1),(1,1),(255,2),(2,2),(255,3)]+[(i,3)for i in range(3,17)]+[(255,4),(17,4)]
build_cases=0;paint_cases=0
for m in maps:
    f=m['room_build'];ctor=branch(f+0xf4)
    def vecsize():ret(len(values(r(1))))
    def element():ret(values(r(1))[r(2)])
    def add():v=r(1);items=values(v);items.append(r(2));store(v,items);ret()
    def insert():v=r(1);items=values(v);items.insert(r(3),r(2));store(v,items);ret()
    def setat():v=r(1);items=values(v);items[r(3)]=r(2);store(v,items);ret()
    handlers={0xbe3f1c:lambda:ret(vector()),0xbe6b7c:lambda:ret(),0x1dfce8:vecsize,0x1dfcb8:element,0x1dfcac:add,0x1dfcc8:insert,0x1dfce4:setat,
      branch(f+0xb4):lambda:ret(r(1)),branch(f+0xdc):lambda:ret(alloc()),branch(ctor+0x24):lambda:ret(),branch(ctor+0x2c):lambda:ret(empty),
      branch(f+0x1c4):lambda:ret(1),branch(f+0x1dc):lambda:ret(40),branch(f+0x200):lambda:ret(800)}
    for seed in (0,1,52):
        heap=D+0x1000;source=vector();ids=list(range(18));random.Random(seed).shuffle(ids);rooms=[]
        for i in ids:
            obj=alloc();q(obj+0x10,empty);u.mem_write(obj+0x18,bytes([i,0,group(i)]));rooms.append(obj)
        store(source,rooms);u.mem_write(screen,bytes(0x80))
        u.reg_write(UC_ARM64_REG_SP,S+0x28000);u.reg_write(UC_ARM64_REG_LR,STOP)
        u.reg_write(UC_ARM64_REG_X0,env);u.reg_write(UC_ARM64_REG_X1,screen);u.reg_write(UC_ARM64_REG_X2,source)
        endpoints={STOP};stopped=0;u.emu_start(B+f,STOP+4,count=100000)
        assert stopped==STOP
        out=values(rq(screen+0x48));assert [(u.mem_read(x+0x18,1)[0],u.mem_read(x+0x1a,1)[0])for x in out]==expected
        assert set(x for x in out if u.mem_read(x+0x18,1)[0]!=255)==set(rooms)
        build_cases+=1
    # Both NULL and the interned empty literal select default "Phòng <id>".
    # A separately allocated empty string takes the custom branch (old == bug).
    start=f-0x4e4;default=f-0x4a0;custom=f-0x4b0
    assert raw[start:start+20]==raw[0x54e8ac:0x54e8ac+20]
    handlers={0x1f64a4:lambda:ret(empty)};endpoints={B+default,B+custom}
    sp=S+0x28000;fp=sp+0x300;room=D+0x400
    for title,go_default in ((0,True),(empty,True),(D+0x500,False),(D+0x600,False)):
        q(room+0x10,title);q(sp+0x128,room)
        u.reg_write(UC_ARM64_REG_SP,sp);u.reg_write(UC_ARM64_REG_X29,fp);u.reg_write(UC_ARM64_REG_X19,env)
        stopped=0;u.emu_start(B+start,STOP+4,count=1000);assert stopped==B+(default if go_default else custom)
        paint_cases+=1
print(f'PASS: {build_cases} actual ARM64 room builds/sorts across six variants match reference group IDs; {paint_cases} native title dispatch cases verify NULL fallback')
