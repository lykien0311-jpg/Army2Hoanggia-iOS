"""Execute the actual injected ARM64 and RoboVM guard in Unicorn, all variants."""
from pathlib import Path
import struct,json,re,hashlib
import lief
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
from keystone import Ks,KS_ARCH_ARM64,KS_MODE_LITTLE_ENDIAN
ROOT=Path(__file__).resolve().parent;BASE=0x100000000
B=ROOT.joinpath('build/prepared-native').read_bytes();R=json.loads(ROOT.joinpath('build/hook-report.json').read_text())
lief.logging.disable();M=lief.MachO.parse(str(ROOT/'build/prepared-native')).at(0)
ORIG=(ROOT.parent/'validation/review/patched-native').read_bytes()
OLD=lief.MachO.parse(str(ROOT.parent/'validation/review/patched-native')).at(0)
# Check the file remap and complete preservation of all prior room/clan/data
# fixes outside explicitly reported instruction/header changes.
restored=bytearray(B);rxoff=R['rxoff'];delta=R['linkedit_shift'];del restored[rxoff:rxoff+delta]
for p in R['patches']:
    off=p['offset'];new=bytes.fromhex(p['after']);assert restored[off:off+len(new)]==new
    restored[off:off+len(new)]=bytes.fromhex(p['before'])
restored[:0x8000]=ORIG[:0x8000]
assert restored==ORIG
assert M.segments[-1].name=='__LINKEDIT'
assert [(x.name,x.value)for x in M.symbols]==[(x.name,x.value)for x in OLD.symbols]
assert list(M.function_starts.functions)==list(OLD.function_starts.functions)
def bindings(m):return [(x.address,x.symbol.name if x.has_symbol else None,x.library_ordinal,x.addend)for x in m.dyld_info.bindings]
def rebases(m):return [(x.address,x.size,int(x.type))for x in m.relocations]
assert bindings(M)==bindings(OLD)
assert rebases(M)==rebases(OLD)
assert [x.name for x in M.libraries][:-1]==[x.name for x in OLD.libraries]
assert [(s.name,s.virtual_address,s.offset)for s in M.sections if s.segment_name in ('__TEXT','__DATA')]==[(s.name,s.virtual_address,s.offset)for s in OLD.sections]
for a,b in zip(list(M.segments)[1:],list(M.segments)[2:]):assert a.virtual_address+a.virtual_size<=b.virtual_address and a.file_offset+a.file_size<=b.file_offset
assert all(not(s.init_protection&2 and s.init_protection&4)for s in M.segments)

CALLBACKS={'AGWheelOpen':0x300000000,'AGWheelTick':0x300001000,'AGWheelReceive':0x300002000,'AGRoomReceive':0x300006000,'AGRoomRebuild':0x300007000,'AGTurnReceive':0x300009000,'AGTurnManual':0x30000a000,'AGTurnPulse':0x300010000,'AGViewportKeypad':0x300011000}
STACK=0x700000000;SP=STACK+0x18000;ENV=0x600000000;MSG=ENV+0x1000;OBJECT=ENV+0x2000;STOP=0x300003000;GUARD=0x300004000;BODY=0x300005000
X=[getattr(__import__('unicorn.arm64_const',fromlist=['']),f'UC_ARM64_REG_X{i}')for i in range(31)]
U=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
for s in M.segments:
    if s.name=='__PAGEZERO':continue
    U.mem_map(s.virtual_address,(s.virtual_size+4095)&-4096)
    U.mem_write(s.virtual_address,B[s.file_offset:s.file_offset+s.file_size])
U.mem_map(STACK,0x20000);U.mem_map(ENV,0x10000);U.mem_map(0x300000000,0x20000)
def readq(a):return struct.unpack('<Q',U.mem_read(a,8))[0]
def writeq(a,v):U.mem_write(a,struct.pack('<Q',v))
def string(a):return bytes(U.mem_read(a,100)).split(b'\0')[0].decode()
calls=[];missing=False;speedAddr=0;buildAddr=0;roomHandled=1;continuation=0;stopKind=None;bodyRaises=False
def returned(value=0):U.reg_write(UC_ARM64_REG_X0,value&((1<<64)-1));U.reg_write(UC_ARM64_REG_PC,U.reg_read(UC_ARM64_REG_LR))
def hook(uc,addr,size,data):
    global stopKind
    if addr==BASE+R['dlsym']:
        assert U.reg_read(X[0])==2**64-2
        name=string(U.reg_read(X[1]));calls.append(('dlsym',name))
        for reg in X[1:18]:U.reg_write(reg,0xbeef)
        returned(0 if missing else CALLBACKS[name])
    elif addr in CALLBACKS.values():
        name=next(k for k,v in CALLBACKS.items()if v==addr)
        calls.append((name,tuple(U.reg_read(r)for r in X[:(8 if name.startswith('AGNotes') else 3)])))
        for reg in X[:18]:U.reg_write(reg,0xbeef)
        returned(roomHandled if name in ('AGRoomReceive','AGNotesInput','AGNotesSettings','AGTurnChange') else 0)
    elif addr==speedAddr:
        assert U.reg_read(X[0])==ENV;calls.append(('speed',));returned(7)
    elif addr==buildAddr:
        assert tuple(U.reg_read(r)for r in X[:3])==(ENV,OBJECT,MSG)
        calls.append(('build',))
        for reg in X[:18]:U.reg_write(reg,0xabcd)
        returned(123)
    elif addr in (STOP,continuation):stopKind=addr;U.emu_stop()
    elif addr==BODY:
        assert U.reg_read(X[0])==ENV and U.reg_read(X[1])==OBJECT
        writeq(ENV+0x30,0x1234)
        if bodyRaises:
            writeq(ENV+0x10,OBJECT);U.reg_write(X[0],readq(ENV+0x38));U.reg_write(UC_ARM64_REG_PC,BASE+0x1300d9c)
        else:returned(42)
U.hook_add(UC_HOOK_CODE,hook)
def reset():
    global calls,stopKind
    calls=[];stopKind=None
    for i,r in enumerate(X):U.reg_write(r,0xc000+i)
    U.reg_write(UC_ARM64_REG_SP,SP);U.reg_write(UC_ARM64_REG_LR,STOP)
    U.reg_write(X[0],ENV);U.reg_write(X[1],OBJECT);U.reg_write(X[2],MSG)
    U.mem_write(BASE+R['rwvm'],bytes(512));U.mem_write(MSG,bytes(0x40))
def preserved(original=False):
    assert U.reg_read(UC_ARM64_REG_SP)==SP-(96 if original else 0)
    for i in range(19,30):assert U.reg_read(X[i])==0xc000+i,(i,hex(U.reg_read(X[i])))
    assert U.reg_read(UC_ARM64_REG_LR)==STOP
    if original:assert readq(SP-96)==0xc01c and readq(SP-88)==0xc01b
cases=0
for h in R['hooks']:
    v=h['variant'];speedAddr=BASE+h['speed'];buildAddr=BASE+h['room_build']
    for missing in (False,True):
        continuation=0;reset();U.emu_start(BASE+h['open_hook'],STOP+4,count=1000);preserved()
        cb=[c for c in calls if c[0]=='AGWheelOpen'];assert bool(cb)==(not missing)
        if cb:assert cb[0][1][:2]==(ENV,v)
        cases+=1
        reset();U.emu_start(BASE+h['tick_hook'],STOP+4,count=1000);preserved();assert U.reg_read(X[0])==7
        assert calls[-1]==('speed',);cb=[c for c in calls if c[0]=='AGWheelTick'];assert bool(cb)==(not missing)
        if cb:assert cb[0][1][:2]==(ENV,v)
        # A second tick reuses the pointer cache, then still returns native speed.
        if not missing:
            before=len([c for c in calls if c[0]=='dlsym']);U.reg_write(X[0],ENV);U.emu_start(BASE+h['tick_hook'],STOP+4,count=1000)
            assert len([c for c in calls if c[0]=='dlsym'])==before
        cases+=1
        reset();U.emu_start(BASE+h['room_build_hook'],STOP+4,count=1000);preserved()
        assert calls[0]==('build',) and U.reg_read(X[0])==123
        cb=[c for c in calls if c[0]=='AGRoomRebuild'];assert bool(cb)==(not missing)
        if cb:assert cb[0][1]==(ENV,OBJECT,v)
        cases+=1
        for command,roomHandled in ((-115,1),(-101,1),(-19,1),(-19,0),(-100,1),(0,1),(116,1),(None,1)):
            reset();continuation=BASE+h['controller']+4
            if command is None:U.reg_write(X[2],0)
            else:U.mem_write(MSG+0x30,bytes([command&255]))
            U.emu_start(BASE+h['controller'],STOP+4,count=1000)
            intercept=(command in (-115,-101) or (command==-19 and roomHandled)) and not missing
            assert stopKind==(STOP if intercept else continuation)
            preserved(not intercept)
            cb=[c for c in calls if c[0] in ('AGWheelReceive','AGRoomReceive')];assert bool(cb)==(command in (-101,-19) and not missing)
            if cb:assert cb[0][1]==(ENV,MSG,v)
            if not intercept:assert tuple(U.reg_read(r)for r in X[:3])==(ENV,OBJECT,0 if command is None else MSG)
            cases+=1
# Assemble and execute the exact catch guard with the app's actual enter/jump
# implementation, both normal return and a simulated Java throwable.
text=ROOT.joinpath('NativeGuard.S').read_text();code='\n'.join(l.split('//')[0]for l in text.splitlines() if not l.startswith('.'))
raw=bytes(Ks(KS_ARCH_ARM64,KS_MODE_LITTLE_ENDIAN).asm(code,GUARD)[0]);U.mem_write(GUARD,raw)
continuation=0;speedAddr=0;buildAddr=0
for bodyRaises in (False,True):
    reset();writeq(ENV+0x10,0);writeq(ENV+0x30,0x4444);writeq(ENV+0x38,0x5555)
    U.reg_write(X[1],BODY);U.reg_write(X[2],OBJECT);U.reg_write(X[3],BASE+0x1300d54)
    U.emu_start(GUARD,STOP+4,count=1000);preserved()
    assert readq(ENV+0x10)==0 and readq(ENV+0x30)==0x4444 and readq(ENV+0x38)==0x5555
    assert U.reg_read(UC_ARM64_REG_W0)==(0xffffffff if bodyRaises else 42);cases+=1
assert B[0x5bd128:0x5bd150]==ORIG[0x5bd128:0x5bd150], 'Xem giờ label must be restored'
for h in R['hooks']:assert B[h['clock']+4:h['clock']+0x22c]==ORIG[h['clock']+4:h['clock']+0x22c], 'Original clock body must remain intact after dispatch'
print(f'PASS: {cases} ARM64 hook/exception cases; all 6 variants; clock restored; exact prior-patch preservation; unchanged symbols/function starts, {len(bindings(M))} bindings, {len(rebases(M))} rebases; ordered W^X segments; LINKEDIT last')



