"""Independent wire fixtures and hostile-input checks for the -101 protocol."""
import ctypes as C
import struct, subprocess, sys, tempfile, random
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class Row(C.Structure):
    _fields_=[('name',C.c_char*256),('amount',C.c_int64),('own',C.c_uint8)]
class Snapshot(C.Structure):
    _fields_=[(f,C.c_int)for f in 'version status count tax page rows hasResult resultTax'.split()]+[('message',C.c_char*1024),('winner',C.c_char*256)]+[(f,C.c_int64)for f in 'ack serverTime round starts ends total own balance pending resultRound resultPool resultPrize resultStake'.split()]+[('entries',Row*20)]
def utf(s):
    # Java modified UTF-8 uses UTF-16 code units (including surrogate pairs).
    b=bytearray()
    for u, in struct.iter_unpack('>H',s.encode('utf-16-be')):
        if 0<u<128:b.append(u)
        elif u<2048:b.extend((0xc0|(u>>6),0x80|(u&63)))
        else:b.extend((0xe0|(u>>12),0x80|((u>>6)&63),0x80|(u&63)))
    return struct.pack('>H',len(b))+b
def fixture(version=2,rows=2,result=True,ack=0x123456789abc):
    names=['Kiên 🏆','Hoàng Gia']+['Người chơi '+str(i)for i in range(18)]
    b=struct.pack('>HBB',22354,version,0)+utf('Tham gia thành công')
    b+=struct.pack('>9q',ack,1800000000000,52,1800000000000-10000,1800000000000+60000,rows*1000000,1000000 if rows else 0,8000000000,0)
    b+=struct.pack('>iBiB',rows,5,0,rows)
    for i in range(rows):b+=utf(names[i])+struct.pack('>qB',1000000,i==0)
    b+=bytes([result])
    if result:
        b+=struct.pack('>q',51)+utf('Hoàng Gia')+struct.pack('>qBq',20000000,5,19000000)
        if version>=2:b+=struct.pack('>q',10000000)
    return bytes(b)
def run():
    with tempfile.TemporaryDirectory() as d:
        lib=Path(d)/('protocol.dylib' if sys.platform=='darwin' else 'protocol.so')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fPIC','-dynamiclib' if sys.platform=='darwin' else '-shared',str(ROOT/'WheelProtocol.c'),'-o',str(lib)],check=True)
        c=C.CDLL(str(lib));c.AGParse.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(Snapshot)];c.AGParse.restype=C.c_int
        c.AGValidateBet.argtypes=[C.POINTER(Snapshot),C.c_int64,C.c_int64];c.AGValidateBet.restype=C.c_char_p
        c.AGBet.argtypes=[C.c_void_p,C.c_int64,C.c_int64,C.c_int64];c.AGBet.restype=C.c_size_t
        c.AGPoll.argtypes=[C.c_void_p,C.c_int32];c.AGPoll.restype=C.c_size_t
        count=0
        for v in (1,2):
            for rows in (0,1,2,20):
                for result in (False,True):
                    b=fixture(v,rows,result);s=Snapshot();assert c.AGParse(b,len(b),C.byref(s))
                    assert s.version==v and s.rows==rows and s.balance==8000000000 and s.round==52
                    assert s.ack==0x123456789abc and s.hasResult==result
                    if rows:assert s.entries[0].name.decode()=='Kiên 🏆' and s.entries[0].own
                    if result:assert s.winner.decode()=='Hoàng Gia' and s.resultPrize==19000000 and s.resultStake==(10000000 if v==2 else 0)
                    # Every truncated prefix and a trailing byte must be rejected.
                    for length in range(len(b)):assert not c.AGParse(b,length,C.byref(s));count+=1
                    assert not c.AGParse(b+b'\0',len(b)+1,C.byref(s));count+=1
        good=fixture();s=Snapshot();assert c.AGParse(good,len(good),C.byref(s))
        assert not c.AGValidateBet(C.byref(s),s.serverTime,1000000)
        assert c.AGValidateBet(C.byref(s),s.serverTime,999999)
        assert c.AGValidateBet(C.byref(s),s.ends-10000,1000000)
        assert not c.AGValidateBet(C.byref(s),s.ends-10001,1000000)
        s.own=49000000;assert not c.AGValidateBet(C.byref(s),s.serverTime,1000000)
        assert c.AGValidateBet(C.byref(s),s.serverTime,1000001)
        s.own=0;s.balance=999999;assert c.AGValidateBet(C.byref(s),s.serverTime,1000000)
        buf=C.create_string_buffer(28)
        assert c.AGPoll(buf,17)==8 and buf.raw[:8]==bytes.fromhex('5752020000000011')
        assert c.AGPoll(buf,-1)==0
        assert c.AGBet(buf,52,0x123456789abc,50000000)==28
        assert buf.raw==bytes.fromhex('5752020100000000000000340000123456789abc0000000002faf080')
        for nonce,amount in [(0,1000000),(-1,1000000),(1,999999),(1,50000001)]:assert not c.AGBet(buf,52,nonce,amount)
        # Bounded fuzzer: arbitrary bytes plus mutation of valid frames.
        rng=random.Random(52)
        for i in range(20000):
            if i%2:b=bytearray(rng.randbytes(rng.randrange(0,500)))
            else:
                b=bytearray(good)
                for _ in range(rng.randrange(1,6)):b[rng.randrange(len(b))]=rng.randrange(256)
            out=Snapshot();c.AGParse(bytes(b),len(b),C.byref(out));count+=1
        print(f'PASS: 16 complete v1/v2 snapshots, {count} truncation/tail/fuzz cases, 64-bit funds, Unicode, request golden bytes, lock/amount limits')
if __name__=='__main__':run()
