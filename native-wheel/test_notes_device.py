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
now=100.;sent=[];writers={};messageCommands={};titles={0:''};objects={};painted=[];invoked=[];screen=0;raiseWrite=False;lockDepth=0;made=[];released=[]
def hook(uc,pc,size,_):
    global lockDepth
    if pc==STOP:uc.emu_stop();return
    if pc in imports:
        name=imports[pc]
        if name=='_clock_gettime':put(reg(1),'<qq',int(now),int(now%1*1e9));ret()
        elif name=='__dyld_get_image_header':assert reg(0)==0;ret(MAIN)
        elif name=='_pthread_mutex_lock':lockDepth+=1;ret()
        elif name=='_pthread_mutex_unlock':lockDepth-=1;assert lockDepth>=0;ret()
        elif name=='_malloc':ret(alloc(reg(0)))
        elif name in ('_free','_dispatch_async'):ret()
        elif name=='_dispatch_once':ret()
        elif name=='_bzero':u.mem_write(reg(0),bytes(reg(1)));ret()
        elif name in ('_memcpy','___memcpy_chk'):u.mem_write(reg(0),bytes(u.mem_read(reg(1),reg(2))));ret(reg(0))
        elif name=='_snprintf':
            fmt=bytes(u.mem_read(reg(2),1024)).split(b'\0')[0].decode()
            if '%s' in fmt:
                ptr=get(u.reg_read(UC_ARM64_REG_SP),'<Q');value=bytes(u.mem_read(ptr,4096)).split(b'\0')[0].decode();fmt=fmt.replace('%s',value,1)
            elif '%d' in fmt:fmt=fmt.replace('%d',str(get(u.reg_read(UC_ARM64_REG_SP),'<i')),1)
            data=fmt.encode()[:reg(1)-1];u.mem_write(reg(0),data+b'\0');ret(len(data))
        elif name in ('_objc_retainAutoreleasedReturnValue','_objc_retain','_objc_retainAutorelease','_objc_autoreleaseReturnValue','_objc_unsafeClaimAutoreleasedReturnValue'):ret(reg(0))
        elif name=='_objc_release':ret()
        elif name=='_objc_storeStrong':put(reg(0),'<Q',reg(1));ret()
        elif name=='_objc_alloc':ret(alloc(0x40))
        elif name=='_objc_msgSend':
            selector=bytes(u.mem_read(reg(1),128)).split(b'\0')[0].decode()
            if selector=='stringWithUTF8String:':
                text=bytes(u.mem_read(reg(2),4096)).split(b'\0')[0].decode();p=alloc(64);objects[p]=text;ret(p)
            elif selector=='initWithCharacters:length:':
                objects[reg(0)]=bytes(u.mem_read(reg(2),reg(3)*2)).decode('utf-16-le');ret(reg(0))
            else:raise AssertionError(('unexpected ObjC',selector))
        else:raise AssertionError(('unexpected OS call',name))
    elif pc in native:
        name,v=native[pc];assert reg(0)==ENV
        if name=='service':ret(SERVICE)
        elif name=='alloc':ret(alloc(0x40))
        elif name=='ctor':
            assert reg(2)&255 in (155,133,134);messageCommands[reg(1)]=C.c_int8(reg(2)&255).value;writer=alloc(0x40);put(reg(1)+0x18,'<Q',writer);writers[writer]=bytearray();ret()
        elif name=='send':
            assert reg(1)==get(SERVICE+0x10,'<Q');writer=get(reg(2)+0x18,'<Q');sent.append((messageCommands[reg(2)],bytes(writers[writer])));ret()
        elif name=='room_get':ret(screen)
        elif name=='fontget':ret(HEAP+0x8000)
        elif name=='fontdraw':painted.append((titles[reg(3)],C.c_int32(reg(4)).value,C.c_int32(reg(5)).value,reg(6)));ret()
        elif name=='callback':invoked.append(reg(1));ret()
    elif pc==MAIN+0xa64a3c:
        assert reg(0)==ENV
        if raiseWrite:
            put(ENV+0x10,'<Q',HEAP+0x800);u.reg_write(UC_ARM64_REG_X0,get(ENV+0x38,'<Q'));u.reg_write(UC_ARM64_REG_PC,MAIN+0x1300d9c)
        else:writers[reg(1)].append(reg(2)&255);ret()
    elif pc==NEWSTRING:
        assert reg(0)==ENV
        s=alloc(0x40);titles[s]=bytes(u.mem_read(reg(1),reg(2)*2)).decode('utf-16-le','surrogatepass');made.append(s);ret(s)
    elif pc==DELETES:assert reg(0)==ENV;released.append(reg(1));ret()
    elif pc==NEWUTF:
        text=bytes(u.mem_read(reg(1),256)).split(b'\0')[0].decode();p=alloc(64);titles[p]=text;ret(p)
    elif pc==GETLEN:ret(len(objects[reg(1)].encode('utf-16-le'))//2)
    elif pc==GETCHARS:
        data=objects[reg(1)].encode('utf-16-le');p=alloc(len(data));u.mem_write(p,data);ret(p)
    elif pc==RELEASECHARS:ret()
    elif pc==CLEAR:put(ENV+0x10,'<Q',0);ret()
NEWUTF=FAKE+0x24000;GETLEN=NEWUTF+0x100;GETCHARS=NEWUTF+0x200;RELEASECHARS=NEWUTF+0x300
for slot,ptr in [(167,NEWUTF),(164,GETLEN),(165,GETCHARS),(166,RELEASECHARS)]:put(JNI+slot*8,'<Q',ptr)
notes=json.loads((ROOT/'notes-map.json').read_text())
for idx,mp in enumerate(notes):
    for key,kind in [('font_get','fontget'),('font','fontdraw'),('callback','callback')]:native[MAIN+mp[key]]=(kind,idx)
u.hook_add(UC_HOOK_CODE,hook)
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
ns=dict(globals());exec((ROOT/'test_notes_protocol.py').read_text().split('lib=C.CDLL')[0].replace("R=Path(__file__).resolve().parent;D=R.parent/'fixtures/data'", "R=ROOT;D=ROOT.parent/'fixtures/data'"),ns)
Packet,State=ns['Packet'],ns['State']
class Notes(C.Structure):
 _fields_=[('cap',State),('connection',C.c_uint64),('inboxDialog',C.c_uint64)]+[(n,C.c_int) for n in 'known saved draft dirty editing pending sendInvite sendInviteValue inboxVisible inboxAction heldCode heldKey heldPointer deferred'.split()]+[('inviteSince',C.c_double),('generation',C.c_uint64),('inboxSerial',C.c_uint64)]
def model(v):return Notes.from_buffer_copy(bytes(u.mem_read(symbols['_NModels']+v*C.sizeof(Notes),C.sizeof(Notes))))
checks=0
def ok(v):
 global checks
 assert v;checks+=1

def recv(v,command,wire):
 msg=message(wire);put(msg+0x30,'<b',command);before=get(get(msg+0x20,'<Q')+0x20,'<i');ok(call('_AGNotesReceive',ENV,msg,v)==1);ok(get(get(msg+0x20,'<Q')+0x20,'<i')==before)
def press(v,code):
 ok(call('_AGNotesInput',v,0,code,0)==1);ok(call('_AGNotesInput',v,1,code,0)==1)
def key(index):u.mem_write(keys+0x14+index,b'\1')
for v,mp in enumerate(notes):
 sent.clear();painted.clear();invoked.clear();now+=100;put(SERVICE+0x10,'<Q',SESSION+v*0x100)
 canvas=alloc(0x200);screen=alloc(0x200);clazz=alloc(0x100);keys=alloc(0x40);releasedKeys=alloc(0x40)
 put(MAIN+mp['canvas'],'<Q',canvas);put(MAIN+mp['room_class'],'<Q',clazz);put(screen,'<Q',clazz);put(canvas+0xb8,'<Q',screen)
 for ptr in [keys,releasedKeys]:put(ptr+0x10,'<i',14)
 put(canvas+0xa0,'<Q',keys);put(canvas+0xa8,'<Q',releasedKeys);put(canvas+0x128,'<i',640);put(canvas+0x130,'<i',480);put(canvas+0x120,'<i',320)
 recv(v,-122,b'\1\0\0\0');ok(model(v).known and model(v).saved==0)
 settings=alloc(0x80);put(settings+0x50,'<i',6);call('_AGNotesSettings',ENV,settings,0,v,0)
 key(6);call('_AGNotesSettings',ENV,settings,0,v,1);ok(model(v).draft==1 and model(v).dirty==1 and not sent)
 call('_AGNotesSettings',ENV,settings,0x1234,v,2);ok(painted[-2:]==[('Chặn lời mời:',190,408,0),('Bật',240,422,2)])
 ok(call('_AGNotesSettings',ENV,settings,0,v,3)==1);call('_AGNotesTick',ENV,v);ok(sent==[(-122,b'\1\1')]);ok(model(v).pending)
 # Repeated OK must exit immediately while the acknowledgement is pending.
 ok(call('_AGNotesSettings',ENV,settings,0,v,3)==1);beforeRepeat=len(sent);call('_AGNotesTick',ENV,v);ok(len(sent)==beforeRepeat and model(v).pending)
 recv(v,-122,b'\1\1\0\0');ok(model(v).saved==1 and not model(v).pending)
 call('_AGNotesSettings',ENV,settings,0,v,0);before=len(sent);call('_AGNotesSettings',ENV,settings,0,v,3);call('_AGNotesTick',ENV,v);ok(len(sent)==before and model(v).draft==1)
 call('_AGNotesSettings',ENV,settings,0,v,0);put(canvas+0x110,'<i',240);put(canvas+0x138,'<i',422);u.mem_write(canvas+0x140,b'\1');call('_AGNotesSettings',ENV,settings,0,v,1);ok(model(v).draft==1 and get(settings+0x50,'<i')==6)
 put(canvas+0x110,'<i',176);u.mem_write(canvas+0x140,b'\1');call('_AGNotesSettings',ENV,settings,0,v,1);ok(model(v).draft==0 and model(v).dirty and len(sent)==before)
 key(8);call('_AGNotesSettings',ENV,settings,0,v,1);ok(get(settings+0x50,'<i')==0)
 key(2);call('_AGNotesSettings',ENV,settings,0,v,1);ok(get(settings+0x50,'<i')==6)
 recv(v,-122,b'\1\1\0\0');ok(model(v).draft==0 and model(v).dirty)
 # Context and viewport may precede the native join-room packet.
 recv(v,-123,b'\2\3\1');otherJoin=alloc(0x40);put(otherJoin,'<Q',clazz+0x100);put(canvas+0xb8,'<Q',otherJoin);before=len(sent)
 recv(v,-123,b'\2\0');call('_AGNotesTick',ENV,v);ok(len(sent)==before and model(v).cap.op==0)
 put(canvas+0xb8,'<Q',screen);call('_AGNotesTick',ENV,v);ok(sent[-1]==(-123,b'\2\0\1\xe0\2\x80'))
 wire=(ROOT.parent/'fixtures/data/sequence-480x640.bin').read_bytes();answer=(ROOT.parent/'fixtures/data/sequence-480x640.answer').read_bytes()
 put(canvas+0xb8,'<Q',otherJoin);recv(v,-123,wire);ok(not model(v).cap.active and model(v).deferred)
 call('_AGNotesTick',ENV,v);ok(not model(v).cap.active);put(canvas+0xb8,'<Q',screen);call('_AGNotesTick',ENV,v);ok(model(v).cap.active and not model(v).deferred)
 for cell in answer:press(v,49+cell)
 press(v,48);call('_AGNotesTick',ENV,v);s=model(v).cap;nonce=bytes(s.packet.nonce[:s.packet.nonceLength]);ok(sent[-1]==(-123,b'\2\1'+struct.pack('>H',len(nonce))+nonce+b'\4'+answer))
 before=len(sent);now+=11;call('_AGNotesTick',ENV,v);ok(len(sent)==before and not model(v).cap.waiting)
 other=alloc(0x40);put(other,'<Q',clazz+0x100);put(canvas+0xb8,'<Q',other);call('_AGNotesTick',ENV,v);ok(not model(v).cap.active)
 recv(v,-123,wire);ok(not model(v).cap.active);ok(call('_AGNotesInput',v,0,49,0)==0)
 put(canvas+0xb8,'<Q',screen);recv(v,-123,b'\2\3\0');recv(v,-123,wire);ok(not model(v).cap.active)
 recv(v,-123,b'\2\3\1');recv(v,-123,wire);ok(model(v).cap.active);press(v,27);call('_AGNotesTick',ENV,v);ok(sent[-1]==(-123,b'\2\3'))
 dialog=alloc(0x50);left=alloc(0x30);right=alloc(0x30);leftcb=alloc(0x20);rightcb=alloc(0x20)
 put(dialog+0x10,'<Q',left);put(dialog+0x20,'<Q',right);put(left+0x18,'<Q',leftcb);put(right+0x18,'<Q',rightcb)
 body=alloc(64);objects[body]='Tổng kết boss\n'+'Nhận thưởng đầy đủ và đọc hết nội dung dài. '*200+'\n✅ kết thúc'
 call('_AGNotesInbox',ENV,dialog,body,v);textp=get(symbols['_NInboxBodies']+v*8,'<Q');ok(objects[textp]==objects[body]);put(canvas+0x108,'<Q',dialog);call('_AGNotesTick',ENV,v);ok(model(v).inboxVisible)
 job=alloc(16);put(job,'<iiQ',v,0,dialog);ok(call('_NCallback',ENV,job)==1);ok(invoked[-1]==leftcb)
 put(job+4,'<i',1);ok(call('_NCallback',ENV,job)==1);ok(invoked[-1]==rightcb)
 put(canvas+0x108,'<Q',0);ok(call('_NCallback',ENV,job)==0);call('_AGNotesTick',ENV,v);ok(not model(v).inboxVisible)
 reason='Tài khoản bị khóa 1h do nhập sai captcha 3 lần. còn 59 phút';raw=reason.encode();recv(v,-123,b'\2\2\2'+struct.pack('>H',len(raw))+raw);alert=get(symbols['_NAlert'],'<Q');ok(objects[alert]==reason)
 put(SERVICE+0x10,'<Q',0);call('_AGNotesTick',ENV,v);ok(objects[get(symbols['_NAlert'],'<Q')]==reason and not model(v).known and not model(v).cap.active)
report={'passed':True,'assertions':checks,'variants':6,'actual_arm64_dylib':str(path),'uikit_and_jvm_primitives':'mocked','live_requests':0,'native_model_size':C.sizeof(Notes)}
(ROOT/'build/notes-device-check.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report)
