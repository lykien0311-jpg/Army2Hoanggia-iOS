"""Balance494 wire, five stats, equipment percentages and legacy fallback.

Pass --jar REF.jar to also execute the unmodified JAR's BalanceClient494 as
an independent JVM oracle. No account or network connection is used.
"""
import argparse,ctypes as C,json,os,random,shutil,struct,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class Rules(C.Structure):
    _fields_=[('enabled',C.c_uint8*10),('base',(C.c_int32*5)*10),('point',(C.c_int32*5)*10),('attackGain',C.c_int32*10)]
Arr=C.c_int64*5
def fixture(seed=0,disabled=False):
    r=random.Random(seed);rows=[]
    for c in range(10):
        rows.append((not disabled,[r.randrange(0,40000)for _ in range(5)],
                     [r.randrange(1,41)for _ in range(5)],r.randrange(0,51)))
    rows[0]=(not disabled,[14008,200,10,20,30],[5,3,10,10,10],1)
    return rows
def wire(rows):
    return struct.pack('>IB',1379154228,10)+b''.join(struct.pack('>B11i',on,*base,*point,gain)for on,base,point,gain in rows)
def expected(rows,c,points,flat,percent):
    if not 0<=c<10 or not rows[c][0]:return [17]*5
    on,base,step,gain=rows[c];out=[]
    for j in range(5):
        n=points[j]+flat[j]
        value=base[j]*(100+n*gain//step[j]+percent[j])//100 if j==1 else (base[j]+n*step[j])*(100+percent[j])//100
        out.append(min(2147483647,max(0,value)))
    return out
def run(jar=None):
    with tempfile.TemporaryDirectory()as tmp:
        d=Path(tmp);lib=d/('stats.dylib'if sys.platform=='darwin'else'stats.so')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-DAG_STATS_HOST','-fPIC',
                        '-dynamiclib'if sys.platform=='darwin'else'-shared',str(ROOT/'Stats.c'),'-o',str(lib)],check=True)
        c=C.CDLL(str(lib));c.AGStatsParse.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(Rules)]
        c.AGStatsCalculate.argtypes=[C.POINTER(Rules),C.c_int,C.POINTER(C.c_int64),C.POINTER(C.c_int64),C.POINTER(C.c_int64),C.POINTER(C.c_int64)]
        rows=fixture();good=wire(rows);r=Rules();assert len(good)==455 and c.AGStatsParse(good,len(good),C.byref(r))
        before=bytes(r);bad=[good[:n]for n in range(len(good))]+[good+b'\0',b'bad!'+good[4:],good[:4]+b'\x09'+good[5:]]
        for at,value in [(6,-1),(26,0),(46,-1),(454,-1)]:
            q=bytearray(good)
            if at==454:q[at]=255;q[451]=255
            else:struct.pack_into('>i',q,at,value)
            bad.append(bytes(q))
        for q in bad:
            assert not c.AGStatsParse(q,len(q),C.byref(r));assert bytes(r)==before,'partial invalid rule update'
        rng=random.Random(264);cases=[];native=[]
        for i in range(1000):
            rows=fixture(i//10,disabled=i%31==0);ch=i%12-1
            p=[rng.randrange(0,32000)for _ in range(5)];f=[rng.randrange(0,180000)for _ in range(5)];pct=[rng.randrange(0,1800)for _ in range(5)]
            if i==1:ch=0;p=[1000]*5;f=[1800]*5;pct=[500]*5
            q=wire(rows);assert c.AGStatsParse(q,len(q),C.byref(r))
            out=Arr(*([17]*5));changed=c.AGStatsCalculate(C.byref(r),ch,Arr(*p),Arr(*f),Arr(*pct),out)
            want=expected(rows,ch,p,f,pct);assert list(out)==want,(i,list(out),want)
            assert bool(changed)==(0<=ch<10 and rows[ch][0])
            if i==1:assert out[0]==168048
            cases.append((q,ch,p,f,pct));native.append(list(out))
        jvm_cases=0
        if jar:
            java=shutil.which('java')or'/usr/lib/jvm/java-17-openjdk-amd64/bin/java'
            source='''import java.io.*;import game.BalanceClient494;
public class StatsOracle264 {public static void main(String[] args)throws Exception {
DataInputStream in=new DataInputStream(System.in);DataOutputStream out=new DataOutputStream(System.out);
int count=in.readInt();for(int i=0;i<count;i++){
byte[] b=new byte[455];in.readFully(b);BalanceClient494.receive(new DataInputStream(new ByteArrayInputStream(b)));
int ch=in.readInt();long[] p=new long[5],f=new long[5],pct=new long[5],v={17,17,17,17,17};
for(int j=0;j<5;j++)p[j]=in.readLong();for(int j=0;j<5;j++)f[j]=in.readLong();for(int j=0;j<5;j++)pct[j]=in.readLong();
BalanceClient494.apply(ch,p,f,pct,v);for(long x:v)out.writeLong(x);}out.flush();}}
'''
            (d/'StatsOracle264.java').write_text(source)
            jar=str(Path(jar).resolve());cp=os.pathsep.join([jar,str(d)])
            subprocess.run([java,'com.sun.tools.javac.Main','-cp',jar,'-d',str(d),str(d/'StatsOracle264.java')],check=True)
            data=struct.pack('>i',len(cases))+b''.join(q+struct.pack('>i15q',ch,*p,*f,*pct)for q,ch,p,f,pct in cases)
            result=subprocess.run([java,'-cp',cp,'StatsOracle264'],input=data,stdout=subprocess.PIPE,check=True)
            actual=[list(x)for x in struct.iter_unpack('>5q',result.stdout)]
            assert actual==native,'C differs from original JAR';jvm_cases=len(cases)
        report=dict(passed=True,formula_cases=len(cases),malformed_packets=len(bad),unmodified_JAR_oracle_cases=jvm_cases,
                    five_attributes=True,disabled_rules_keep_legacy=True,no_partial_packet_updates=True,no_combat_writes=True)
        (ROOT/'build').mkdir(exist_ok=True);(ROOT/'build/stats-check.json').write_text(json.dumps(report,indent=2)+'\n')
        print('PASS',report)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--jar');run(p.parse_args().jar)
