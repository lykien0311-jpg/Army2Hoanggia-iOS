"""Replay native home selection, cleanup and paint gate; reproduce Build254."""
import json,re,struct
from pathlib import Path
import lief
import test_hooks as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *

U=t.U;B=t.BASE;X=t.X
def w(a,v):U.mem_write(a,struct.pack('<I',v))
def branch(data,a):
    word=struct.unpack_from('<I',data,a)[0];assert word&0xfc000000==0x94000000
    n=word&0x3ffffff;return a+4*(n-(1<<26) if n&(1<<25) else n)
def load(path):
    data=path.read_bytes();m=lief.MachO.parse(str(path)).at(0)
    for s in m.segments:
        if s.name!='__PAGEZERO':
            U.mem_write(s.virtual_address,data[s.file_offset:s.file_offset+s.file_size])
            U.ctl_remove_cache(s.virtual_address,s.virtual_address+s.virtual_size)
    return data
paints=[m.start()-0x70 for m in re.finditer(re.escape(t.ORIG[0x53cb7c:0x53cb84]),t.ORIG)]
assert len(paints)==6
redirects={};primitives={};ends=set();reached=None
def hook(uc,pc,size,_):
    global reached
    if pc in redirects:U.reg_write(UC_ARM64_REG_PC,redirects[pc])
    elif pc in primitives:t.returned(primitives[pc])
    elif pc in ends:reached=pc;U.emu_stop()
U.hook_add(UC_HOOK_CODE,hook)
results=[]
for baseline in (True,False):
    root=t.ROOT/('build254-baseline' if baseline else 'build')
    data=load(root/'prepared-native');report=json.loads((root/'hook-report.json').read_text())
    for h,paint in zip(report['hooks'],paints):
        s=h['home_select'];entry=s-0x3ec;after=h['home_after_action'];layout=branch(data,after+8)
        # Keep the original prologue, one native pending-action store, the
        # selector prefix, and the entire original cleanup/layout method.
        assert t.ORIG[entry:entry+4]==t.ORIG[0x53d86c:0x53d870]
        assert t.ORIG[s-0x14:s-0xc]==t.ORIG[0x53dc44:0x53dc4c]
        redirects={B+entry+0x2c:B+s-0x260,B+s-0x258:B+s-0x1f8,B+s-0x1ec:B+s-0x14}
        primitives={B+branch(data,layout+0x24):0,B+branch(data,layout+0x58):480,
                    B+branch(data,layout+0x80):320}
        t.missing=False;t.continuation=t.speedAddr=t.buildAddr=0;t.reset()
        home=t.ENV+0x4000;homeclass=t.ENV+0x5000;array=t.ENV+0x6000
        for a in (home,homeclass,array):U.mem_write(a,bytes(0x300))
        t.writeq(B+h['home_class'],homeclass);t.writeq(homeclass+0xb0,array)
        w(array+0x10,7);w(home+0x60,6);w(home+0x70,1)
        U.mem_write(home+0x9c,b'\1\0\0\0');U.reg_write(X[1],home)
        ends=set();U.emu_start(B+entry,t.STOP+4,count=10000);t.preserved()
        callbacks=[c for c in t.calls if c[0]=='AGWheelOpen']
        assert len(callbacks)==1 and callbacks[0][1][:2]==(t.ENV,h['variant'])
        flags=bytes(U.mem_read(home+0x9c,4))
        assert flags==(b'\0\0\0\1' if baseline else b'\0\1\0\0'),flags
        # Execute native painter background calls and its 0x9f menu gate.
        t.reset();U.reg_write(X[1],home);redirects={};primitives={}
        for off in (0x40,0x4c,0x58,0x68):primitives[B+branch(data,paint+off)]=0
        foreground=B+paint+0x78;hidden=B+paint+0xce0
        ends={foreground,hidden};reached=None
        U.emu_start(B+paint,t.STOP+4,count=10000)
        assert reached==(hidden if baseline else foreground),(hex(reached or 0),hex(paint))
        results.append(dict(build=254 if baseline else 255,variant=h['variant'],menu_visible=not baseline))
report=dict(passed=True,original_native_home_transitions=12,
    build254_empty_home_reproduced=True,build255_menu_paint_restored=True,
    original_layout_and_cleanup_executed=True,server_ack_required=False,cases=results)
(t.ROOT/'build/wheel-home-return-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS', {k:v for k,v in report.items() if k!='cases'})
