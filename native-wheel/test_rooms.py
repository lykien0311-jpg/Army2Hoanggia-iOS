"""Exercise real C parser/application against the verified RoboVM object layout.

The previous live-only setter loses all custom titles on list replacement.
These cases recreate title-before-list and repeated room-screen rebuilds.
"""
import ctypes as C
import struct,subprocess,tempfile,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class Names(C.Structure):
    _fields_=[('present',C.c_uint8*256),('length',C.c_uint16*256),('text',(C.c_uint16*256)*256)]
Make=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.POINTER(C.c_uint16),C.c_int)
Release=C.CFUNCTYPE(None,C.c_void_p,C.c_void_p)
temp=tempfile.TemporaryDirectory();libpath=Path(temp.name)/'rooms.so'
subprocess.run(['cc','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'RoomNames.c'),'-o',str(libpath)],check=True)
lib=C.CDLL(str(libpath));lib.AGRoomParse.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(Names)];lib.AGRoomParse.restype=C.c_int
lib.AGRoomApply.argtypes=[C.c_void_p,C.POINTER(Names),Make,Release,C.c_void_p];lib.AGRoomApply.restype=C.c_int
def mutf(text):
    result=bytearray()
    for (c,) in struct.iter_unpack('>H',text.encode('utf-16-be','surrogatepass')):
        if 0<c<128:result.append(c)
        elif c<2048:result.extend((0xc0|(c>>6),0x80|(c&63)))
        else:result.extend((0xe0|(c>>12),0x80|((c>>6)&63),0x80|(c&63)))
    return bytes(result)
def packet(rows,marker=255):
    data=bytearray([len(rows)])
    for i,name in rows:
        utf=mutf(name);data.extend(bytes([i])+struct.pack('>H',len(utf))+utf+bytes([marker]))
    return bytes(data)
def parse(data):
    names=Names();return lib.AGRoomParse(data,len(data),C.byref(names)),names
def decoded(names,i):return bytes(names.text[i])[:names.length[i]*2].decode('utf-16-le','surrogatepass')
titles={i:f'Phòng {i}: Trùm {i}' for i in range(3,17)}
titles[3]='Phòng 3: Bom';titles[4]='Phòng 4: Nhện';titles[5]='Phòng 5: Người máy'
wire=packet(list(titles.items()));ok,cache=parse(wire);assert ok
for i in titles:assert decoded(cache,i)==titles[i]
valid=1;invalid=0
for data in [packet([]),packet([(128,'Phòng 128: Có dấu')]),packet([(254,'A\0🙂\ud800')]),packet([(1,'x'*256)])]:
    assert parse(data)[0];valid+=1
for size in range(len(wire)):
    assert not parse(wire[:size])[0];invalid+=1
for data in [wire+b'x',packet([(255,'header')]),packet([(3,'a'),(3,'b')]),packet([(3,'a')],0),packet([(3,'x'*257)]),b'\1\3\0\1\0\xff',b'\1\3\0\2\xc1\x81\xff',b'\1\3\0\3\xe0\x80\x80\xff',b'\1\3\0\4\xf0\x9f\x98\x80\xff']:
    assert not parse(data)[0];invalid+=1

storage=[];strings={};releases=[];allocated=[];fail_after=None
def buf(n):
    b=C.create_string_buffer(n);storage.append(b);return C.addressof(b)
def put(a,fmt,*v):C.memmove(a,struct.pack(fmt,*v),struct.calcsize(fmt))
def get(a,fmt):return struct.unpack(fmt,C.string_at(a,struct.calcsize(fmt)))[0]
def text(s):
    a=buf(24);strings[a]=s;return a
@Make
def make(ctx,chars,n):
    if fail_after is not None and len(allocated)>=fail_after:return None
    a=text(C.string_at(chars,n*2).decode('utf-16-le','surrogatepass'));allocated.append(a);return a
@Release
def release(ctx,a):releases.append(a)
def build(ids,stale=False):
    screen=buf(0x80);vector=buf(0x30);array=buf(0x18+len(ids)*8)
    put(screen+0x48,'<Q',vector);put(vector+0x18,'<Q',array);put(vector+0x24,'<i',len(ids));put(array+0x10,'<i',len(ids))
    rooms=[]
    for j,i in enumerate(ids):
        r=buf(0x20);put(array+0x18+j*8,'<Q',r);put(r+0x10,'<Q',text('HEADER' if i==255 else ('wrong row name' if stale else '')))
        put(r+0x18,'<BBB',i,j&255,j%5);rooms.append(r)
    return screen,rooms,vector,array
def apply(screen,names):
    allocated.clear();releases.clear();answer=lib.AGRoomApply(screen,C.byref(names),make,release,None)
    assert sorted(allocated)==sorted(releases),'temporary JNI references must be released'
    return answer
def check(rooms,expected):
    for r in rooms:
        i=get(r+0x18,'<B');assert strings[get(r+0x10,'<Q')]==('HEADER' if i==255 else expected.get(i,''))

# This fixture has all five reference-video groups; order is the native list
# builder's output. Group headers never receive a custom room title.
ids=[255,0,255,1,255,2,255,*range(3,17),255,17]
sc,rooms,vec,arr=build(ids)
assert apply(sc,cache)==18;check(rooms,titles)
old_titles=[get(r+0x10,'<Q') for r in rooms]
# Negative control: a new list with the previous live-only setter has no titles.
newsc,newrooms,_,_=build(ids)
assert all(strings[get(r+0x10,'<Q')]=='' for r in newrooms if get(r+0x18,'<B')!=255)
assert strings[get(newrooms[7]+0x10,'<Q')]!=titles[3]
# New cache also works when packet precedes room screen construction.
assert apply(None,cache)==0
assert apply(newsc,cache)==18;check(newrooms,titles)
# Reverse order and stale shifted labels must still map by ID, not row index.
rng=random.Random(483);layouts=0
for _ in range(60):
    shuffled=ids.copy();rng.shuffle(shuffled)
    sc,rooms,_,_=build(shuffled,stale=True);unchanged=[C.string_at(r+0x18,8) for r in rooms]
    assert apply(sc,cache)==18;check(rooms,titles)
    assert unchanged==[C.string_at(r+0x18,8) for r in rooms]
    layouts+=1
ok,high=parse(packet([(128,'Phòng 128'),(254,'Phòng 254')]));assert ok
sc,rooms,vec,arr=build([255,128,254,1],stale=True)
assert apply(sc,high)==3;check(rooms,{128:'Phòng 128',254:'Phòng 254'})
# Null entries, corrupt counts, allocation failure, and an empty replacement.
put(arr+0x18+3*8,'<Q',0);assert apply(sc,high)==2
put(vec+0x24,'<i',5);assert apply(sc,high)==0
put(vec+0x24,'<i',-1);assert apply(sc,high)==0
put(vec+0x24,'<i',4);fail_after=0;assert apply(sc,high)==-1
fail_after=1;assert apply(sc,high)==-1
fail_after=None;ok,empty=parse(packet([]));assert ok
sc,rooms,_,_=build(ids,stale=True);assert apply(sc,empty)==18;check(rooms,{})
print(f'PASS: room-name cache; {valid} valid packets, {invalid} malformed/truncated packets; names before/after list; {layouts} shuffled/rebuilt lists; video group IDs 0/1/2/3–16/17; header and room metadata preserved; JNI references released')
