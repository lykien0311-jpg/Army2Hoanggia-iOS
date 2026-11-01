"""UFO -> finished effects -> original native player turn -> auto -> UFO.

Execute the shipped ARM64 turn changer, flight completion, gravity update and
projectile finalizer. Terrain/math, HUD/camera and JVM/network are controlled
boundaries. The tests do not establish physical-device acceptance.
"""
import re,struct
import ufo_sequence_harness as w
from unicorn.arm64_const import *
t=w.t;U=w.U;B=w.B;raw=w.raw

def copies(a,n=32):
    found=[m.start()for m in re.finditer(re.escape(raw[a:a+n]),raw) if m.start()>=a]
    assert len(found)==6,(hex(a),found);return found
fall=copies(0x597250,64);flight_start=copies(0x59a2e8,24)
flight_end=copies(0x59c174)
shot_end=[m.start() for m in re.finditer(re.escape(raw[0x580fdc:0x580ffc]),raw) if raw[m.start()+0x34:m.start()+0x38]==raw[0x581010:0x581014]]
assert len(shot_end)==6,shot_end
changes=w.report['turn_change_hooks']

def init_native(s,v):
    entry=changes[v]['original'];body=w.branch(entry+0x3c)
    # The native turn changer checks its empty chat/status string before
    # updating ownership. Run its real getter; mock only the Java String literal.
    empty=t.alloc(0x20);t.put(s['g']+0x148,'<Q',empty)
    w.primitives[B+w.branch(body+0x34)]=lambda:empty
    s['empty']=empty
    counter=t.alloc(0x200);t.put(s['g']+0xe0,'<Q',counter);s['counter']=counter
    controller=t.alloc(0x200);t.put(B+changes[v]['controller_class'],'<Q',controller)
    t.put(B+changes[v]['controller_class']+9,'<B',2);s['controller']=controller
    w.primitives[B+changes[v]['input_reset']]=lambda:w.phase_log.append(('input_reset',v))
    entry=w.t.maps[v]['controller']
    w.redirects[B+entry+0xc8]=B+changes[v]['case_entry']
    # Device I/O primitive: the unchanged message reader and case body run.
    def read_byte():
        stream=w.r(1);a=t.get(stream+0x10,'<Q');pos=t.get(stream+0x20,'<i')
        value=t.get(a+0x14+pos,'<b');t.put(stream+0x20,'<i',pos+1);return value
    w.primitives[B+0xa63e54]=read_byte
    hud=t.alloc(0x200);camera=t.alloc(0x200)
    w.primitives[B+w.branch(body+0x290)]=lambda:hud
    w.primitives[B+w.branch(body+0x2a4)]=lambda:w.phase_log.append(('timer',v))
    w.primitives[B+w.branch(body+0x2b8)]=lambda:camera
    w.primitives[B+w.branch(body+0x2d0)]=lambda:w.phase_log.append(('owner',v,w.r(2)))
    w.primitives[B+w.branch(body+0x22c)]=lambda:w.phase_log.append(('position',v))



def prepare_notifications(v):
    # Fixed native call sites from 580fdc..5810f0.
    for delta in (0xe8,0xf4):
        pc=shot_end[v]+delta
        assert struct.unpack_from('<I',raw,pc)[0]&0xfc000000==0x94000000
        w.primitives[B+w.branch(pc)]=lambda:0


def settle_local(s,v):
    a=fall[v];w.settle_calls.clear()
    for pc in range(a,a+964,4):
        word=struct.unpack_from('<I',raw,pc)[0]
        if word&0xfc000000==0x94000000:w.settle_calls[B+w.branch(pc)]=0
    w.settle_calls.pop(B+w.branch(a+0x248),None)
    for off,value in ((0xb4,2000),(0x160,1),(0x194,1),(0x254,2)):
        w.settle_calls[B+w.branch(a+off)]=value
    w.settling=True;w.call_address(B+a,t.ENV,s['p']);w.settling=False
    assert t.get(s['p']+0x166,'<B')==0


def finish_flight(s,v):
    a=flight_end[v];w.flight_calls.clear();vector=t.alloc(0x20)
    for pc in range(a,a+552,4):
        word=struct.unpack_from('<I',raw,pc)[0]
        if word&0xfc000000==0x94000000:w.flight_calls[B+w.branch(pc)]=0
    w.flight_calls[B+w.branch(a+0x30)]=2000 # map width
    w.flight_calls[B+w.branch(a+0xd0)]=vector # vector allocation
    w.flight_calls[B+w.branch(a+0x19c)]=120 # terrain/map height
    w.flying=True;w.call_address(B+a,t.ENV,s['boss'],8);w.flying=False
    assert t.get(s['boss']+0x14e,'<B')==0


def owner(v,who,num):
    ticket=900000+num
    wire=bytes([who])+struct.pack('>IiQ',1429485652,num,ticket)
    msg=t.message(wire);t.put(msg+0x30,'<B',24)
    # Message.reader() returns its DataInputStream at28. The observer reads
    # the backing ByteArrayInputStream at20 without consuming it. At this
    # controlled Java boundary both share the same byte position.
    t.put(msg+0x28,'<Q',t.get(msg+0x20,'<Q'))
    this=t.alloc(0x20)
    # Original dispatcher frame/exception context, message reader, busy reset,
    # installed handoff hook and the actual command24 tail all execute.
    w.call_address(B+w.t.maps[v]['controller'],t.ENV,this,msg)
    stream=t.get(msg+0x20,'<Q');assert t.get(stream+0x20,'<i')==1
    return ticket

def aim(v,num):
    w.receive(v,-115,struct.pack('>iBQHBBhh',num,2,900000+num,173,28,13,240,350))

def finish_projectile(s,v):
    obj=t.alloc(0x80)
    w.call_address(B+shot_end[v],t.ENV,obj)
    assert t.get(s['proj']+0x118,'<B')==0

