"""GEM1 preview arithmetic and GEM2 selection guards, optionally against Sua12 JAR."""
import argparse,ctypes as C,json,os,random,struct,subprocess,sys,tempfile
from pathlib import Path
from test_stats import Rules,Arr,fixture,wire,ROOT
class Snapshot(C.Structure):
    _fields_=[('hero',C.c_uint8),('count',C.c_uint8),('valid',C.c_uint8),
              ('points',C.c_int32*5),('handles',C.c_int32*6),
              ('flat',C.c_int64*5),('percent',C.c_int64*5),('values',C.c_int64*5)]
def gemwire(rows,gems):return wire(rows)+struct.pack('>I10iI',0x47454d31,*[200+c for c in range(10)],len(gems))+bytes(x for row in gems for x in row)
def snapwire(c,p,handles,f,pct,values):
    return struct.pack('>IB5iB',0x47454d32,c,*p,len(handles))+b''.join(struct.pack('>i',h)for h in handles)+struct.pack('>15q',*f,*pct,*values)
def run(jar=None):
    with tempfile.TemporaryDirectory()as temp:
        d=Path(temp);lib=d/('stats.dylib'if sys.platform=='darwin'else'stats.so')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-DAG_STATS_HOST','-fPIC','-dynamiclib'if sys.platform=='darwin'else'-shared',str(ROOT/'Stats.c'),'-o',str(lib)],check=True)
        c=C.CDLL(str(lib));c.AGStatsParse.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(Rules)]
        c.AGStatsGemHeader.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(C.c_int32),C.POINTER(C.c_uint32)]
        c.AGStatsExtended.argtypes=[C.POINTER(Rules),C.c_int,*[C.POINTER(C.c_int64)]*4,C.c_int32,C.POINTER(C.c_int64)]
        c.AGStatsSnapshotParse.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(Snapshot)]
        c.AGStatsExact.argtypes=[C.POINTER(Snapshot),C.c_int,*[C.POINTER(C.c_int64)]*3,C.POINTER(C.c_int32),C.c_int,C.POINTER(C.c_int64)]
        cases=[];actual=[];rng=random.Random(265)
        for enabled in [False,True]:
            for hero in range(10):
                for family in range(5):
                    for count in [0,1,3,15]:
                        rows=fixture(hero,disabled=not enabled);p=[1400,900,800,700,600];f=[500,300,200,100,50];pct=[10,11,12,13,14];g=[0]*5;g[family]=count*2;pct[family]+=g[family]
                        cases.append((rows,hero,p,f,pct,g))
        for i in range(600):
            hero=i%10;rows=fixture(i,disabled=i%2==0);p=[rng.randrange(32000)for _ in range(5)];f=[rng.randrange(180000)for _ in range(5)];g=[rng.randrange(0,31)*2 for _ in range(5)];pct=[x+rng.randrange(1800)for x in g]
            cases.append((rows,hero,p,f,pct,g))
        for rows,hero,p,f,pct,g in cases:
            b=gemwire(rows,[g]);rules=Rules();assert c.AGStatsParse(b[:455],455,C.byref(rules))
            bases=(C.c_int32*10)();n=C.c_uint32();assert c.AGStatsGemHeader(b[455:],len(b)-455,bases,C.byref(n))and n.value==1
            out=Arr();assert c.AGStatsExtended(C.byref(rules),hero,Arr(*p),Arr(*f),Arr(*pct),Arr(*g),bases[hero],out)
            actual.append(list(out))
        malformed=0;b=gemwire(fixture(),[[2]*5])[455:];bases=(C.c_int32*10)(*[99]*10);n=C.c_uint32(99)
        for bad in [b[:i]for i in range(len(b))]+[b+b'\0',b'bad!'+b[4:],b[:4]+struct.pack('>i',0)+b[8:],b[:44]+struct.pack('>I',65537)+b[48:]]:
            assert not c.AGStatsGemHeader(bad,len(bad),bases,C.byref(n));assert list(bases)==[99]*10 and n.value==99;malformed+=1
        p=[100,90,80,70,60];f=[10,20,30,40,50];pct=[2,4,6,8,10];handles=[65536,65539,65540];values=[123456,654321,5000,6000,7000];s=Snapshot()
        b=snapwire(4,p,handles,f,pct,values);assert c.AGStatsSnapshotParse(b,len(b),C.byref(s));before=bytes(s)
        for bad in [b[:i]for i in range(len(b))]+[b+b'\0',b'bad!'+b[4:],b[:4]+b'\x0a'+b[5:],b[:25]+b'\x07'+b[26:],b[:-8]+struct.pack('>q',2147483648)]:
            assert not c.AGStatsSnapshotParse(bad,len(bad),C.byref(s));assert bytes(s)==before;malformed+=1
        def exact(hero=4,points=p,flat=f,percent=pct,gear=handles):
            out=Arr(*[17]*5);ok=c.AGStatsExact(C.byref(s),hero,Arr(*points),Arr(*flat),Arr(*percent),(C.c_int32*len(gear))(*gear),len(gear),out)
            assert list(out)==(values if ok else [17]*5);return ok
        assert exact()and exact(gear=handles[::-1]);assert not exact(hero=3)
        for j in range(5):
            for field,v in [('points',p),('flat',f),('percent',pct)]:
                changed=v[:];changed[j]+=1;assert not exact(**{field:changed})
        assert not exact(gear=handles[:-1]);assert not exact(gear=[65536,65536,65540]);assert not exact(gear=[65536,65539,65541])
        jvm=0
        if jar:
            source='''import java.io.*;import game.BalanceClient494;
public class StatsOracle265 {public static void main(String[] args)throws Exception {
DataInputStream in=new DataInputStream(System.in);DataOutputStream out=new DataOutputStream(System.out);int n=in.readInt();
for(int i=0;i<n;i++){byte[] b=new byte[in.readInt()];in.readFully(b);BalanceClient494.receive(new DataInputStream(new ByteArrayInputStream(b)));int hero=in.readInt();long[] p=new long[5],f=new long[10],pct=new long[5],v=new long[5];for(int j=0;j<5;j++)p[j]=in.readLong();for(int j=0;j<10;j++)f[j]=in.readLong();for(int j=0;j<5;j++)pct[j]=in.readLong();BalanceClient494.apply(hero,p,f,pct,v);for(long x:v)out.writeLong(x);}out.flush();}}'''
            (d/'StatsOracle265.java').write_text(source);cp=os.pathsep.join([str(Path(jar).resolve()),str(d)])
            subprocess.run(['java','com.sun.tools.javac.Main','-cp',cp,'-d',str(d),str(d/'StatsOracle265.java')],check=True)
            payload=struct.pack('>i',len(cases))
            for rows,hero,p,f,pct,g in cases:
                b=gemwire(rows,[g]);payload+=struct.pack('>i',len(b))+b+struct.pack('>i20q',hero,*p,*f,*g,*pct)
            result=subprocess.run(['java','-cp',cp,'StatsOracle265'],input=payload,stdout=subprocess.PIPE,check=True)
            expected=[list(x)for x in struct.iter_unpack('>5q',result.stdout)]
            assert expected==actual,next((i,a,b)for i,(a,b)in enumerate(zip(actual,expected))if a!=b);jvm=len(cases)
        report=dict(passed=True,gem_formula_cases=len(cases),Sua12_JAR_oracle_cases=jvm,malformed_packets=malformed,exact_selection_guards=21,physical_device_tested=False)
        (ROOT/'build').mkdir(exist_ok=True);(ROOT/'build/stats265-check.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--jar');run(p.parse_args().jar)
