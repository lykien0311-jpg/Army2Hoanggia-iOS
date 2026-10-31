"""Execute the built iPhone dylib's bridge in ARM64 Unicorn.

UIKit, OS calls, and Java allocation/network primitives are mocked. The actual
compiled state machine, wire codecs, room cache, JNI dispatch, and catch guard
run together. No real account, game socket, or wager is used.
"""
import sys,struct,json,ctypes as C
from pathlib import Path
import lief
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
from test_protocol import Snapshot,fixture
ROOT=Path(__file__).resolve().parent
path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'build/AGWheel.dylib'
blob=path.read_bytes();m=lief.MachO.parse(str(path)).at(0)
MAIN=0x100000000;LIB=0x200000000;FAKE=0x400000000;HEAP=0x600000000;STACK=0x700000000;STOP=FAKE+0x30000
u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
for s in m.segments:
    u.mem_map(LIB+s.virtual_address,(s.virtual_size+4095)&-4096)
    u.mem_write(LIB+s.virtual_address,blob[s.file_offset:s.file_offset+s.file_size])
main=(ROOT.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes()
u.mem_map(MAIN,(len(main)+4095)&-4096);u.mem_write(MAIN,main)
u.mem_map(FAKE,0x40000);u.mem_map(HEAP,0x2000000);u.mem_map(STACK,0x40000)
symbols={s.name:LIB+s.value for s in m.symbols if s.value}
def put(a,fmt,*v):u.mem_write(a,struct.pack(fmt,*v))
def get(a,fmt):return struct.unpack(fmt,u.mem_read(a,struct.calcsize(fmt)))[0]
for rel in m.relocations:
    assert rel.size==64 and int(rel.type)==1
    put(LIB+rel.address,'<Q',get(LIB+rel.address,'<Q')+LIB)
imports={};names={}
for b in m.dyld_info.bindings:
    name=b.symbol.name
    if name not in names:names[name]=FAKE+len(names)*256;imports[names[name]]=name
    put(LIB+b.address,'<Q',names[name])
class Model(C.Structure):
    _fields_=[('snapshot',Snapshot)]+[(f,C.c_int)for f in 'variant visible loaded waiting sendNow page'.split()]+[('generation',C.c_uint64),('connection',C.c_uint64)]+[(f,C.c_double)for f in 'openedAt receivedAt lastPoll lastBet noticeUntil'.split()]+[(f,C.c_int64)for f in 'nonce betRound amount'.split()]+[('notice',C.c_char*1024)]
def state():return Model.from_buffer_copy(bytes(u.mem_read(symbols['_AGState'],C.sizeof(Model))))
def save(s):u.mem_write(symbols['_AGState'],bytes(s))
def reg(i):return u.reg_read(UC_ARM64_REG_X0+i)
def ret(v=0):u.reg_write(UC_ARM64_REG_X0,v&((1<<64)-1));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
cursor=HEAP+0x10000
def alloc(n):
    global cursor
    p=cursor;cursor+=(n+15)&-16;assert cursor<HEAP+0x2000000;u.mem_write(p,bytes(n));return p
ENV=HEAP;SERVICE=HEAP+0x100;SESSION=HEAP+0x200;JNI=HEAP+0x1000
put(ENV,'<Q',JNI);NEWSTRING=FAKE+0x20000;DELETES=NEWSTRING+0x100;CLEAR=NEWSTRING+0x200
put(JNI+163*8,'<Q',NEWSTRING);put(JNI+23*8,'<Q',DELETES);put(JNI+17*8,'<Q',CLEAR)
put(SERVICE+0x10,'<Q',SESSION)
maps=json.loads((ROOT/'native-map.json').read_text());native={}
for idx,mp in enumerate(maps):
    for name in ('service','alloc','ctor','send','room_get'):native[MAIN+mp[name]]=(name,idx)
now=100.;sent=[];writers={};titles={0:''};screen=0;raiseWrite=False;lockDepth=0;made=[];released=[]
def hook(uc,pc,size,_):
    global lockDepth
    if pc==STOP:uc.emu_stop();return
    if pc==symbols.get("_AGTurnStatusUpdate"):
        ret();return
    if pc in imports:
        name=imports[pc]
        if name=='_clock_gettime':put(reg(1),'<qq',int(now),int(now%1*1e9));ret()
        elif name=='__dyld_get_image_header':assert reg(0)==0;ret(MAIN)
        elif name=='_pthread_mutex_lock':lockDepth+=1;ret()
        elif name=='_pthread_mutex_unlock':lockDepth-=1;assert lockDepth>=0;ret()
        elif name=='_malloc':ret(alloc(reg(0)))
        elif name in ('_free','_dispatch_async'):ret()
        elif name=='_bzero':u.mem_write(reg(0),bytes(reg(1)));ret()
        elif name=='_memcpy':u.mem_write(reg(0),bytes(u.mem_read(reg(1),reg(2))));ret(reg(0))
        elif name=='_snprintf':
            # Notice text is tested by UI preview, not by this state test.
            u.mem_write(reg(0),b'notice\0');ret(6)
        else:raise AssertionError(('unexpected OS call',name))
    elif pc in native:
        name,v=native[pc];assert reg(0)==ENV
        if name=='service':ret(SERVICE)
        elif name=='alloc':ret(alloc(0x40))
        elif name=='ctor':
            assert reg(2)&255==155;writer=alloc(0x40);put(reg(1)+0x18,'<Q',writer);writers[writer]=bytearray();ret()
        elif name=='send':
            assert reg(1)==get(SERVICE+0x10,'<Q');writer=get(reg(2)+0x18,'<Q');sent.append(bytes(writers[writer]));ret()
        elif name=='room_get':ret(screen)
    elif pc==MAIN+0xa64a3c:
        assert reg(0)==ENV
        if raiseWrite:
            put(ENV+0x10,'<Q',HEAP+0x800);u.reg_write(UC_ARM64_REG_X0,get(ENV+0x38,'<Q'));u.reg_write(UC_ARM64_REG_PC,MAIN+0x1300d9c)
        else:writers[reg(1)].append(reg(2)&255);ret()
    elif pc==NEWSTRING:
        assert reg(0)==ENV
        s=alloc(0x40);titles[s]=bytes(u.mem_read(reg(1),reg(2)*2)).decode('utf-16-le','surrogatepass');made.append(s);ret(s)
    elif pc==DELETES:assert reg(0)==ENV;released.append(reg(1));ret()
    elif pc==CLEAR:put(ENV+0x10,'<Q',0);ret()
BASE_HOOK=u.hook_add(UC_HOOK_CODE,hook)
def call(name,*args):
    u.reg_write(UC_ARM64_REG_SP,STACK+0x30000);u.reg_write(UC_ARM64_REG_LR,STOP)
    for i,arg in enumerate(args):u.reg_write(UC_ARM64_REG_X0+i,arg)
    u.emu_start(symbols[name],STOP+4,count=2000000)
    assert u.reg_read(UC_ARM64_REG_PC)==STOP,name
    assert lockDepth==0 and get(ENV+0x10,'<Q')==0 and get(ENV+0x38,'<Q')==0
    return u.reg_read(UC_ARM64_REG_W0)
def message(wire):
    a=alloc(0x14+len(wire));put(a+0x10,'<i',len(wire));u.mem_write(a+0x14,bytes(wire))
    inp=alloc(0x30);put(inp+0x10,'<Q',a);put(inp+0x18,'<i',len(wire));put(inp+0x20,'<i',0)
    msg=alloc(0x40);put(msg+0x20,'<Q',inp);return msg
def receive(v,ack=0,timestamp=1800000000000):
    wire=bytearray(fixture(ack=ack));start=4+2+int.from_bytes(wire[4:6],'big');struct.pack_into('>q',wire,start+8,timestamp)
    call('_AGWheelReceive',ENV,message(wire),v)
wheelcases=0
for v in range(6):
    put(SERVICE+0x10,'<Q',SESSION);now+=100;sent.clear();call('_AGWheelOpen',ENV,v)
    assert state().variant==v and state().visible and not state().loaded
    call('_AGWheelTick',ENV,v);assert sent==[bytes.fromhex('5752020000000000')]
    call('_AGWheelTick',ENV,v);assert len(sent)==1
    receive(v);assert state().loaded and state().snapshot.balance==8000000000
    s=state();s.nonce=123456789;s.betRound=52;s.amount=2000000;s.waiting=1;s.sendNow=1;save(s)
    call('_AGWheelTick',ENV,v);bet=bytes.fromhex('57520201')+struct.pack('>qqq',52,123456789,2000000);assert sent[-1]==bet
    now+=7.1;call('_AGWheelTick',ENV,v);assert sent[-1]==bet and sent.count(bet)==2
    receive(v,timestamp=1800000001000);receive(v,ack=123456789)
    assert not state().waiting and not state().nonce and state().snapshot.serverTime==1800000001000
    s=state();s.waiting=1;s.sendNow=1;s.nonce=333;s.amount=2000000;s.betRound=52;save(s)
    n=len(sent);put(SERVICE+0x10,'<Q',SESSION+0x100);call('_AGWheelTick',ENV,v)
    assert len(sent)==n and not state().waiting and not state().loaded and state().connection==SESSION+0x100
    # Actual Java exception longjmp through compiled NativeGuard must unlock.
    raiseWrite=True;now+=3;call('_AGWheelTick',ENV,v);raiseWrite=False
    assert len(sent)==n and not state().loaded
    wheelcases+=8

def roomlist():
    s=alloc(0x80);vec=alloc(0x30);ids=[255,0,255,1,255,2,255,*range(3,17),255,17]
    arr=alloc(0x18+len(ids)*8);put(s+0x48,'<Q',vec);put(vec+0x18,'<Q',arr);put(vec+0x24,'<i',len(ids));put(arr+0x10,'<i',len(ids));rooms=[]
    for i,rid in enumerate(ids):
        r=alloc(0x20);put(r+0x10,'<Q',0x1234);u.mem_write(r+0x18,bytes([rid,1,i%5]));put(arr+0x18+i*8,'<Q',r);rooms.append(r)
    return s,rooms
def roomwire(entries):
    data=bytearray([len(entries)])
    for i,title in entries:
        raw=title.encode('utf-8');data.extend(bytes([i])+struct.pack('>H',len(raw))+raw+b'\xff')
    return bytes(data)
def check(rooms,expected):
    for r in rooms:
        rid=u.mem_read(r+0x18,1)[0];title=get(r+0x10,'<Q')
        if rid==255:assert title==0x1234
        else:assert titles[title]==expected.get(rid,'')
        if rid in (0,1,2,17):assert title==0
    assert sorted(made)==sorted(released)
roomcases=0
for v in range(6):
    screen=0;expected={3:'Phòng 3: Bom',4:'Phòng 4: Bom 2',16:'Phòng 16: Super Boss'}
    assert call('_AGRoomReceive',ENV,message(roomwire(expected.items())),v)==1
    screen,rooms=roomlist();call('_AGRoomRebuild',ENV,screen,v);check(rooms,expected)
    screen,rooms=roomlist();call('_AGRoomRebuild',ENV,screen,v);check(rooms,expected)
    expected[5]='Phòng 5: Nhện máy';assert call('_AGRoomReceive',ENV,message(roomwire(expected.items())),v)==1;check(rooms,expected)
    assert call('_AGRoomReceive',ENV,message(roomwire(expected.items())[:-1]),v)==0
    screen,rooms=roomlist();call('_AGRoomRebuild',ENV,screen,v);check(rooms,expected)
    assert call('_AGRoomReceive',ENV,message(b'\0'),v)==1;check(rooms,{})
    roomcases+=6
print(f'PASS: compiled iPhone dylib: {wheelcases} wheel bridge/state checks and {roomcases} room-cache/JNI checks across all six variants; exact outgoing bytes, same-nonce retry, stale ack, changed connection, real RoboVM exception recovery; no live server calls')

if '_AGMoveAllow' in symbols:
    for variant in range(6):
        now=100.;assert call('_AGMoveAllow',variant,HEAP+0x9000,0)==1
        now=100.01;assert call('_AGMoveAllow',variant,HEAP+0x9000,0)==0
        now=100.06;assert call('_AGMoveAllow',variant,HEAP+0x9000,0)==1
        assert call('_AGMoveAllow',variant,HEAP+0x9000,1)==1
        now=105.;assert call('_AGMoveAllow',variant,HEAP+0x9000,1)==1
        assert call('_AGMoveAllow',variant,HEAP+0x9000,1)==0
    print('PASS: compiled device movement pacing, 36 monotonic-clock checks across six variants')


