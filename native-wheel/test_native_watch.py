"""Execute the actual iPhone snapshot adapter with mocked game/JNI primitives.
The original AOT entry addresses are validated separately against attached B280.
No server login, live room, or live packet is sent by this test.
"""
import sys,json,struct,base64
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'deps'))
import lief
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
ROOT=Path(__file__).resolve().parent
NATIVE_ROOT=ROOT/'repo/native-wheel' if (ROOT/'repo/native-wheel').is_dir() else ROOT
path=Path(sys.argv[1]);blob=path.read_bytes();m=lief.MachO.parse(str(path)).at(0)
MAIN=0x100000000;LIB=0x200000000;FAKE=0x400000000;HEAP=0x600000000;STACK=0x700000000;STOP=FAKE+0x30000
u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
for s in m.segments:
    if not s.virtual_size:continue
    u.mem_map(LIB+s.virtual_address,(s.virtual_size+4095)&-4096)
    u.mem_write(LIB+s.virtual_address,blob[s.file_offset:s.file_offset+s.file_size])
u.mem_map(MAIN,0x3000000);u.mem_map(FAKE,0x40000);u.mem_map(HEAP,0x4000000);u.mem_map(STACK,0x40000)
symbols={s.name:LIB+s.value for s in m.symbols if s.value}
def put(a,fmt,*v):u.mem_write(a,struct.pack(fmt,*v))
def get(a,fmt):return struct.unpack(fmt,u.mem_read(a,struct.calcsize(fmt)))[0]
for rel in m.relocations:
    if rel.size==64:put(LIB+rel.address,'<Q',get(LIB+rel.address,'<Q')+LIB)
imports={};names={}
for b in m.dyld_info.bindings:
    name=b.symbol.name
    if name not in names:names[name]=FAKE+len(names)*256;imports[names[name]]=name
    put(LIB+b.address,'<Q',names[name])
def reg(i):return u.reg_read(UC_ARM64_REG_X0+i)
def ret(v=0):u.reg_write(UC_ARM64_REG_X0,v&((1<<64)-1));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
now=100.0
cursor=HEAP+0x10000
def alloc(n):
    global cursor
    p=cursor;cursor+=(n+15)&-16;assert cursor<HEAP+0x4000000;u.mem_write(p,bytes(n));return p
ENV=HEAP;JNI=HEAP+0x1000;put(ENV,'<Q',JNI)
jni={}
for n in (21,22,23,176,208):jni[FAKE+0x20000+n*16]=n;put(JNI+n*8,'<Q',FAKE+0x20000+n*16)
maps=json.loads((NATIVE_ROOT/'spectator-native-map.json').read_text())
arena=[0x2082e30,0x20b23a0,0x20e0090,0x210dd80,0x213ba70,0x2169760]
canvas=[0x207dac0,0x20ad740,0x20db440,0x2109130,0x2136e20,0x2164b10]
mapClass=[0x20799f0,0x20a9910,0x20d7610,0x2105300,0x2132ff0,0x2160ce0]
tileNew=[0x538708,0x624e90,0x709b54,0x7ee818,0x8d34dc,0x9b81a0]
tileInit=[0x539224,0x6257f4,0x70a4b8,0x7ef17c,0x8d3e40,0x9b8b04]
reset=[0x50c264,0x5fa2fc,0x6defc0,0x7c3c84,0x8a8948,0x98d60c]
native={};objects=[];pins={};tileCount=0;started=[];shown=[];restored=[];lock=0
for v,mp in enumerate(maps):
    a=alloc(0x300);c=alloc(0x200);g=alloc(0x100);cam=alloc(0x100);back=alloc(0x100);oldMap=alloc(0x30);oldTiles=alloc(0x50)
    for address,obj in ((arena[v],a),(canvas[v],c),(mapClass[v],g),(mp['cameraClass'],cam)):put(MAIN+address,'<Q',obj)
    put(c+0xb8,'<Q',back);put(c+0x130,'<i',450);put(c+0x128,'<i',650)
    put(a+0xc8,'<Q',oldMap);put(a+0x266,'<B',7);put(g+0xb8,'<Q',oldTiles);put(g+0xd8,'<ii',800,600)
    actors=[0x207f060,0x20aec70,0x20dc970,0x210a660,0x2138350,0x2166040]
    players=alloc(0x100);put(MAIN+actors[v],'<Q',players)
    objects.append((a,c,g,cam,back,oldMap,oldTiles))
    for k in ('arenaNew','arenaInit','mapNew','mapInit','start','show','restore','clockSet','clockReset'):native[MAIN+mp[k]]=(k,v)
    native[MAIN+tileNew[v]]=('tileNew',v);native[MAIN+tileInit[v]]=('tileInit',v);native[MAIN+reset[v]]=('reset',v)
def hook(uc,pc,size,_):
    global lock,tileCount
    if pc==STOP:u.emu_stop();return
    if pc==symbols.get('_AGWheelGuard'):
        fn=reg(1);job=reg(2);u.reg_write(UC_ARM64_REG_X1,job);u.reg_write(UC_ARM64_REG_PC,fn);return
    if pc in imports:
        name=imports[pc]
        if name=='__dyld_get_image_header':ret(MAIN)
        elif name=='_clock_gettime':put(reg(1),'<qq',int(now),round((now-int(now))*1000000000));ret()
        elif name in ('_pthread_mutex_lock','_pthread_mutex_trylock'):lock+=1;assert lock==1;ret()
        elif name=='_pthread_mutex_unlock':lock-=1;assert lock==0;ret()
        elif name=='_malloc':ret(alloc(reg(0)))
        elif name=='_free':ret()
        elif name in ('_bzero','_memset'):u.mem_write(reg(0),bytes([reg(1)&255])*reg(2) if name=='_memset' else bytes(reg(1)));ret(reg(0))
        elif name in ('_memcpy','_memmove','___memcpy_chk'):u.mem_write(reg(0),bytes(u.mem_read(reg(1),reg(2))));ret(reg(0))
        else:raise AssertionError(('unexpected import',name))
    elif pc in jni:
        n=jni[pc]
        if n==21:p=reg(1);pins[p]=pins.get(p,0)+1;ret(p)
        elif n==22:p=reg(1);pins[p]-=1;assert pins[p]>=0;ret()
        elif n==23:ret()
        elif n==176:p=alloc(reg(1)+0x18);put(p+0x10,'<i',reg(1));ret(p)
        elif n==208:u.mem_write(reg(1)+0x14+reg(2),bytes(u.mem_read(reg(4),reg(3))));ret()
    elif pc in native:
        name,v=native[pc];a,c,g,cam,back,oldMap,oldTiles=objects[v];assert reg(0)==ENV
        if name=='arenaNew':ret(alloc(0x100))
        elif name=='arenaInit':ret()
        elif name=='mapNew':ret(alloc(0x30))
        elif name=='mapInit':ret()
        elif name=='tileNew':ret(alloc(0x50))
        elif name=='tileInit':put(reg(1)+0x20,'<ii',reg(3),reg(4));put(reg(1)+0x38,'<B',reg(6));ret()
        elif name=='reset':ret()
        elif name=='start':
            values=[list(struct.unpack('<8q',u.mem_read(reg(i)+0x18,64)))for i in (3,4,5)]
            assert reg(6)==0;assert get(a+0x266,'<B')==next(i for i,x in enumerate(values[0])if x!=-1)
            started.append((v,reg(2),values));clock=alloc(0x30);put(a+0x110,'<Q',clock);camera=alloc(0x30);put(a+0xd8,'<Q',camera)
            players=get(MAIN+actors[v],'<Q');array=alloc(0x18+8*8)
            put(players+0xa0,'<Q',array);put(array+0x10,'<i',8)
            for slot,x in enumerate(values[0]):
                if x==-1:continue
                player=alloc(0x200);put(array+0x18+slot*8,'<Q',player)
                put(player+0x114,'<ii',x,values[1][slot]);put(player+0x68,'<q',values[2][slot])
            ret()
        elif name=='show':put(c+0xb8,'<Q',reg(1));shown.append(v);assert reg(2)==back;ret()
        elif name=='restore':put(c+0xb8,'<Q',reg(1));restored.append(v);assert reg(1)==back;ret()
        elif name=='clockSet':put(reg(1)+0x1c,'<i',reg(2));ret()
        elif name=='clockReset':put(reg(1)+0x18,'<i',get(reg(1)+0x1c,'<i'));ret()
    elif pc==MAIN+0xbe3f1c:ret(alloc(0x30))
    elif pc==MAIN+0xbe6b7c:ret()
    elif pc in (MAIN+0x12e7d28,MAIN+0x12e7d88):n=reg(1);p=alloc(0x18+n*(4 if pc==MAIN+0x12e7d28 else 8));put(p+0x10,'<i',n);ret(p)
    elif pc==MAIN+0xc46e04:ret(alloc(0x20))
    elif pc==MAIN+0x1c61b0:ret(32)
    elif pc==MAIN+0x1c61a0:ret(24)
    elif pc==MAIN+0x1c61a4:assert get(reg(2)+0x10,'<i')==32*24;ret()
    elif pc==MAIN+0x1dfcac:tileCount+=1;ret()
    else:raise AssertionError(('unexpected native PC',hex(pc)))
# Hook only our known mocked address ranges, not every compiled instruction.
u.hook_add(UC_HOOK_CODE,hook,begin=FAKE,end=FAKE+0x40000)
u.hook_add(UC_HOOK_CODE,hook,begin=MAIN,end=MAIN+0x3000000)
u.hook_add(UC_HOOK_CODE,hook,begin=symbols['_AGWheelGuard'],end=symbols['_AGWheelGuard'])
def call(name,*args):
    u.reg_write(UC_ARM64_REG_SP,STACK+0x30000);u.reg_write(UC_ARM64_REG_LR,STOP)
    for i,x in enumerate(args):u.reg_write(UC_ARM64_REG_X0+i,x)
    u.emu_start(symbols[name],STOP+4,count=1000000)
    assert u.reg_read(UC_ARM64_REG_PC)==STOP and lock==0
    return u.reg_read(UC_ARM64_REG_W0)
def packet(v,p):a=alloc(len(p));u.mem_write(a,bytes(p));return call('_AGNativeWatchPacket',ENV,v,a,len(p))
trace=json.loads((NATIVE_ROOT/'testdata/watch-pvp.json').read_text())
def observe(v,cmd,data):
    at=alloc(len(data));u.mem_write(at,data)
    return call('_AGNativeWatchObserve',v,cmd,at,len(data))
sp=[base64.b64decode(p) for c,p in trace if c==-102 and base64.b64decode(p)[3]in(3,4,5,7)]
assert call('_AGNativeWatchAvailable')==1
for v in range(6):
    before=tileCount
    for cmd,encoded in trace:
        p=base64.b64decode(encoded)
        if cmd==-102 and p[3] in (3,4,5,7):assert packet(v,p)==1,(v,p[:5])
        elif cmd in (8,24):observe(v,cmd,p)
    assert tileCount-before==52
    a,c,g,cam,back,oldMap,oldTiles=objects[v]
    assert get(c+0xb8,'<Q')==get(a+0xe8,'<Q')!=0
    assert get(a+0xc8,'<Q')!=oldMap and get(g+0xb8,'<Q')!=oldTiles
    p=next(p for p in sp if p[3]==7);clock=get(a+0x110,'<Q');assert get(clock+0x18,'<i')==p[4]
    assert get(cam+0xa4,'<i')==241 and get(cam+0xbc,'<B')==1
    # Camera can move left and right, then restore follow mode.
    call('_AGNativeWatchCamera',v,0,-7);call('_AGNativeWatchCamera',v,0,-4);call('_AGNativeWatchTick',ENV,v)
    x=get(cam+0xa4,'<i');assert x>0
    now+=.001;call('_AGNativeWatchTick',ENV,v);assert get(cam+0xa4,'<i')==x,'No camera burst before 15ms'
    now+=.02;call('_AGNativeWatchCamera',v,1,-4);call('_AGNativeWatchCamera',v,0,-3);call('_AGNativeWatchTick',ENV,v);assert get(cam+0xa4,'<i')<x
    call('_AGNativeWatchCamera',v,0,-7);call('_AGNativeWatchTick',ENV,v);assert get(cam+0xbc,'<B')==1
    call('_AGNativeWatchEnd',ENV,v);call('_AGNativeWatchEnd',ENV,v)
    assert get(c+0xb8,'<Q')==back and get(a+0xc8,'<Q')==oldMap and get(g+0xb8,'<Q')==oldTiles and get(a+0x266,'<B')==7
    assert packet(v,sp[0])==1
    assert packet(v,next(p for p in sp if p[3]==5))==0,'Incomplete terrain cannot start'
    tile=next(p for p in sp if p[3]==4);bad=bytearray(tile);bad[19:23]=(24000).to_bytes(4,'big');assert packet(v,bad)==0
    assert packet(v,tile)==1;assert packet(v,tile)==0,'Repeated chunk cannot duplicate a tile'
    call('_AGNativeWatchEnd',ENV,v)
assert len(started)==len(shown)==len(restored)==6
assert all(n==0 for n in pins.values()),pins
print('PASS actual iPhone ARM64: six variants, 312 terrain tiles, full-width HP/position arrays, native start/show, snapshot clock, bidirectional camera, native screen/terrain/local-slot restoration, idempotent close, incomplete/duplicate/out-of-order rejection; no live traffic')
