"""Execute new in-battle menu, identity dispatch and local movement hooks."""
import test_hooks as t
import struct
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.U;B=t.BASE;R=t.R;X=t.X;SP=t.SP;ENV=t.ENV;OBJECT=t.OBJECT;STOP=t.STOP
MOVE=0x300008000;D=0x620000000;U.mem_map(D,0x100000)
heap=D+0x1000;primitives={};ends=set();stopped=0;strings={};commands={};items=[];movement=[];allow=1
def r(i):return U.reg_read(X[i])
def q(a,v):U.mem_write(a,struct.pack('<Q',v))
def alloc():
    global heap
    p=heap;heap+=0x100;return p
def ret(v=0):
    for reg in X[:18]:U.reg_write(reg,0xdead)
    t.returned(v)
def literal():
    assert r(0)==ENV and r(1)==B+R['rwvm']+40
    s=t.string(r(2));assert s=='VÒNG XOAY MAY MẮN';p=alloc();strings[p]=s;q(r(1),p);ret(p)
def initvec():assert(r(0),r(1))==(ENV,OBJECT);ret()
def ctor():assert r(0)==ENV;commands[r(1)]=(strings[r(2)],r(3));ret()
def add():assert(r(0),r(1))==(ENV,OBJECT);items.append(r(2));ret()
def hook(uc,pc,size,_):
    global stopped
    if pc in ends:stopped=pc;U.emu_stop()
    elif pc==MOVE:
        movement.append(('allow',r(0),r(1),r(2)));ret(allow)
    elif pc-B in primitives:primitives[pc-B]()
U.hook_add(UC_HOOK_CODE,hook)
def reset():
    global stopped
    t.reset();t.missing=False;t.continuation=0;t.speedAddr=0;t.buildAddr=0;stopped=0
def run(a):U.emu_start(B+a,STOP+4,count=10000)
cases=0
for h in R['hooks']:
    v=h['variant'];reset();items.clear();ends=set()
    primitives={0xbe6b7c:initvec,h['command_alloc']:lambda:ret(alloc()),h['clock_alloc']:lambda:ret(alloc()),h['clock_ctor']:lambda:ret(),h['command_ctor']:ctor,0x1dfcac:add,0x12e8038:literal}
    run(h['v9_hook']);t.preserved();assert len(items)==1
    label,callback=commands[items[0]];assert label=='VÒNG XOAY MAY MẮN'and t.readq(B+h['callback_slot'])==callback
    cases+=1
    for iswheel in (True,False):
        reset();q(B+h['callback_slot'],callback);U.reg_write(X[1],callback if iswheel else callback+0x100)
        cleared=[];primitives={h['key_reset']:lambda:(cleared.append(r(0)),ret())};ends={B+h['clock']+4}
        run(h['clock'])
        calls=[c for c in t.calls if c[0]=='AGWheelOpen'];assert bool(calls)==iswheel
        if iswheel:assert calls[0][1][:2]==(ENV,v)and cleared==[ENV];t.preserved()
        else:
            assert stopped==B+h['clock']+4 and U.reg_read(UC_ARM64_REG_SP)==SP-48 and not cleared
            assert t.readq(SP-48)==0xc016 and t.readq(SP-40)==0xc015
        cases+=1
    for direction in (0,1):
        for allow in (0,1):
            reset();q(B+R['rwvm']+208,MOVE);movement.clear();ends=set()
            def walk():movement.append(('walk',r(0),r(1),r(2)));ret()
            primitives={h['walk']:walk};U.reg_write(X[2],direction)
            run(h['move_hook']);t.preserved()
            assert movement[0]==('allow',v,OBJECT,direction)
            assert movement[1:]==([('walk',ENV,OBJECT,direction)]if allow else [])
            cases+=1
    # A missing optional function preserves the original movement call.
    reset();t.missing=True;movement.clear();run(h['move_hook']);t.preserved()
    assert movement==[('walk',ENV,OBJECT,t.MSG)];cases+=1
print(f'PASS: {cases} ARM64 V9 construction/clock identity/input gating cases across six variants; existing clock and original movement body preserved')
