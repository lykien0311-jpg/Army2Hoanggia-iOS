"""User flows through the actual rebuilt C controller, without a server."""
import ctypes as C
from pathlib import Path
import subprocess, tempfile, sys

ROOT = Path(__file__).resolve().parent
class Plan(C.Structure):
    _fields_ = [(n,C.c_int) for n in 'turn owner angle force release x y'.split()] + [('ticket',C.c_uint64)]
class Auto(C.Structure):
    _fields_ = [('connection',C.c_size_t),('arena',C.c_size_t),('revision',C.c_uint64),('ticket',C.c_uint64)] + \
        [(n,C.c_int) for n in 'enabled valid turn owner sent claimed powerSent hasPlan hasEarlyPlan stable'.split()] + \
        [('stableSince',C.c_double),('retryAfter',C.c_double),('plan',Plan),('earlyPlan',Plan)]
class Frame(C.Structure):
    _fields_ = [('connection',C.c_size_t),('arena',C.c_size_t)] + \
        [(n,C.c_int) for n in 'active ufo local owner alive state blocked x y'.split()] + [('now',C.c_double)]

def run():
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'auto.so'
        subprocess.run(['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-fPIC',
            '-dynamiclib' if sys.platform=='darwin' else '-shared',str(ROOT/'UfoAuto.c'),'-o',str(path)],check=True)
        lib=C.CDLL(str(path))
        lib.AGUfoReset.argtypes=[C.POINTER(Auto),C.c_size_t]
        lib.AGUfoStart.argtypes=[C.POINTER(Auto)]
        lib.AGUfoMode.argtypes=[C.POINTER(Auto),C.c_int]
        lib.AGUfoTurn.argtypes=[C.POINTER(Auto),C.c_int,C.c_int,C.c_uint64]
        lib.AGUfoAim.argtypes=[C.POINTER(Auto),C.POINTER(Plan)]
        lib.AGUfoManual.argtypes=[C.POINTER(Auto)]
        lib.AGUfoAcquire.argtypes=[C.POINTER(Auto),C.POINTER(Frame),C.POINTER(Plan)]
        lib.AGUfoComplete.argtypes=[C.POINTER(Auto),C.c_uint64,C.c_int,C.c_double]
        def fresh():
            a=Auto();lib.AGUfoReset(a,1);lib.AGUfoMode(a,1)
            return a,Frame(1,2,1,1,2,2,1,0,0,240,350,100.)
        def plan(n=1,**kw):
            d=dict(turn=n,owner=2,angle=173,force=28,release=0,x=240,y=350,ticket=9000+n);d.update(kw)
            return Plan(**d)
        def queue(a,n=1,**kw):
            p=plan(n,**kw);lib.AGUfoTurn(a,p.owner,p.turn,p.ticket);lib.AGUfoAim(a,p);return p
        def acquire(a,f):
            out=Plan();ok=lib.AGUfoAcquire(a,f,out)
            return ok,out
        def settled(a,f):
            acquire(a,f);f.now+=.061
            return acquire(a,f)
        cases=0
        # First turn may arrive before the native battle screen is active.
        for early in (False,True):
            a,f=fresh();lib.AGUfoStart(a);p=plan()
            if early:lib.AGUfoAim(a,p)
            lib.AGUfoTurn(a,p.owner,p.turn,p.ticket)
            if not early:lib.AGUfoAim(a,p)
            f.active=0;assert not settled(a,f)[0]
            f.active=1;ok,out=settled(a,f);assert ok and out.ticket==p.ticket
            revision=a.revision;lib.AGUfoComplete(a,revision,1,f.now)
            for _ in range(10):
                lib.AGUfoTurn(a,p.owner,p.turn,p.ticket);lib.AGUfoAim(a,p)
                assert not settled(a,f)[0]
            cases+=1
        # Successive turns with the same owner, including retransmitted plans.
        a,f=fresh()
        for n in range(1,101):
            p=queue(a,n);assert not acquire(a,f)[0]
            lib.AGUfoAim(a,p);f.now+=.061;ok,out=acquire(a,f);assert ok and out.turn==n
            assert not acquire(a,f)[0]
            lib.AGUfoComplete(a,a.revision,1,f.now);assert not acquire(a,f)[0];cases+=1
        for field,value in [('active',0),('ufo',0),('local',3),('owner',8),('alive',0),('state',3),('blocked',1),('x',241),('y',351)]:
            a,f=fresh();queue(a);old=getattr(f,field);setattr(f,field,value)
            assert not settled(a,f)[0],field
            setattr(f,field,old);assert settled(a,f)[0],field;cases+=1
        # Changed connection, arena, disabled mode and manual shot cancel work.
        for action in ('connection','arena','off','manual','start'):
            a,f=fresh();queue(a);assert settled(a,f)[0];lib.AGUfoComplete(a,a.revision,0,f.now)
            f.now+=1
            if action=='connection':f.connection=9
            elif action=='arena':f.arena=9
            elif action=='off':lib.AGUfoMode(a,0)
            elif action=='manual':lib.AGUfoManual(a)
            else:lib.AGUfoStart(a)
            assert not settled(a,f)[0],action;cases+=1
        # A failed Java send releases its claim; a later tick retries this turn.
        a,f=fresh();queue(a);assert settled(a,f)[0];rev=a.revision
        lib.AGUfoComplete(a,rev,0,f.now);assert not a.sent
        assert not settled(a,f)[0];f.now+=.3
        assert settled(a,f)[0];lib.AGUfoComplete(a,rev,1,f.now);assert a.sent;cases+=1
        # A completion from an earlier turn cannot consume a newer turn.
        a,f=fresh();queue(a);assert settled(a,f)[0];rev=a.revision
        queue(a,2);lib.AGUfoComplete(a,rev,1,f.now);assert not a.sent
        assert settled(a,f)[0];cases+=1
        # Invalid and stale plans never replace the current aim.
        for kw in [dict(owner=8),dict(ticket=0),dict(angle=360),dict(force=0),dict(force=31),dict(release=31)]:
            a,f=fresh();lib.AGUfoTurn(a,2,1,9001);lib.AGUfoAim(a,plan(**kw))
            assert not settled(a,f)[0];cases+=1
        a,f=fresh();queue(a,2);lib.AGUfoAim(a,plan(1));ok,out=settled(a,f)
        assert ok and out.turn==2;cases+=1
        print(f'PASS: {cases} rebuilt UFO controller scenarios; first/repeated turns, no duplicate shots, retry and cancellation')
if __name__=='__main__':run()
