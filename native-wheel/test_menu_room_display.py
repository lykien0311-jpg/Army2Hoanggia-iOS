"""Run the patched ARM64 menu and room-label paths, including the video-1 bug.

Java allocation/string primitives are mocked. Native menu construction, row
dispatch, width selection and room title dispatch execute the packaged code.
The assertions use an independent transcription of reference video 2.
"""
import struct,json
import test_hooks as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.U;B=t.BASE;R=t.R;X=t.X;ENV=t.ENV;SP=t.SP;STOP=t.STOP
D=0x610000000;U.mem_map(D,0x100000)
expected={3:'Phòng 3: Bom',4:'Phòng 4: Bom 2',5:'Phòng 5: Nhện máy',
          6:'Phòng 6: Người máy',7:'Phòng 7: T-rex máy',8:'Phòng 8: UFO',
          9:'Phòng 9: UFO',10:'Phòng 10: Khí cầu',11:'Phòng 11: Nhện độc',
          12:'Phòng 12: Ma',13:'Phòng 13: Ma 2',14:'Phòng 14: Trùm liên hoàn',
          15:'Phòng 15: Trùm liên hoàn',16:'Phòng 16: Super Boss'}
faulty={1:expected[3],2:expected[5],**{i:expected[i+4] for i in range(3,13)}}
heap=D+0x1000;strings={0:''};arrays={};primitives={};endpoints=set();stopped=0;literal_calls=0
def r(i):return U.reg_read(X[i])
def q(a,v):U.mem_write(a,struct.pack('<Q',v))
def w(a,v):U.mem_write(a,struct.pack('<I',v&0xffffffff))
def rq(a):return struct.unpack('<Q',U.mem_read(a,8))[0]
def alloc(n=0x80):
    global heap
    p=heap;heap+=(n+15)&-16;U.mem_write(p,bytes(n));return p
def text(s):p=alloc();strings[p]=s;return p
def ret(v=0):
    for reg in X[:18]:U.reg_write(reg,0xbeef)
    U.reg_write(UC_ARM64_REG_NZCV,0x60000000)
    t.returned(v)
def branch(a):
    ins=struct.unpack_from('<I',t.ORIG,a)[0];assert ins&0xfc000000==0x94000000
    n=ins&0x3ffffff;return a+4*(n-(1<<26)if n&(1<<25)else n)
def literal():
    global literal_calls
    assert r(0)==ENV
    cache=r(1);assert B+R['rwvm']+40<=cache<B+R['rwvm']+160 and cache%8==0
    s=t.string(r(2));assert r(3)==len(s.encode('utf-16-le'))//2
    p=rq(cache)
    if not p:p=text(s);q(cache,p);literal_calls+=1
    else:assert strings[p]==s
    ret(p)
def array_alloc():
    assert r(0)==ENV;n=r(1);p=alloc(0x18+n*8);w(p+0x10,n);arrays[p]=[0]*n;ret(p)
def array_set():
    assert r(0)==ENV
    p,i,value=r(1),r(2),r(3);assert i<len(arrays[p]);arrays[p][i]=value;q(p+0x18+i*8,value);ret()
def hook(uc,pc,size,_):
    global stopped
    if pc in endpoints:stopped=pc;U.emu_stop()
    elif pc-B in primitives:primitives[pc-B]()
U.hook_add(UC_HOOK_CODE,hook)
def reset():
    global stopped
    t.missing=False;t.continuation=0;t.speedAddr=0;t.buildAddr=0
    t.reset();stopped=0;U.reg_write(UC_ARM64_REG_NZCV,0xa0000000)
def run(a):
    try:U.emu_start(B+a,STOP+4,count=10000)
    except Exception:
        print('Native failure:',hex(a),'PC',hex(U.reg_read(UC_ARM64_REG_PC)),'row',globals().get('row'),'variant',globals().get('h',{}).get('variant'))
        raise
menu_cases=0;width_cases=0;room_cases=0;draw_cases=0
for h in R['hooks']:
    # Execute the actual constructor's array allocation and all seven stores.
    reset();primitives={0x1fcf38:array_alloc,0x12e7f74:array_set,0x12e8038:literal}
    parent=alloc();arrays[parent]=[0]*3;w(parent+0x10,3)
    U.reg_write(X[19],ENV);U.reg_write(X[20],parent)
    labels=['entry0','entry1','entry2','entry3','entry4','QUAY SỐ']
    for i,s in enumerate(labels):U.reg_write(X[21+i],text(s))
    end=B+h['home_append_call']+40;endpoints={end}
    run(h['home_count']);assert stopped==end
    submenu=arrays[parent][0]
    assert [strings[s]for s in arrays[submenu]]==labels+['VÒNG XOAY MAY MẮN']
    assert arrays[parent][1:]==[0,0];menu_cases+=1
    # Dispatch only the new row. Original 0/1..5 branches keep their entry PCs.
    primitives={}
    for row in range(8):
        reset();U.reg_write(X[9],row);U.reg_write(X[19],ENV)
        selected_home=alloc(0x200);pair=alloc(16);q(pair,selected_home)
        U.mem_write(selected_home+0x9f,b'\1');U.reg_write(X[24],pair)
        endpoints={B+h['home_select_zero'],B+h['home_select']+4,B+h['home_after_action']}
        run(h['home_select'])
        want=h['home_after_action']if row==6 else h['home_select_zero']if row==0 else h['home_select']+4
        assert stopped==B+want
        calls=[c for c in t.calls if c[0]=='AGWheelOpen'];assert bool(calls)==(row==6)
        if calls:assert calls[0][1][:2]==(ENV,h['variant'])
        assert bytes(U.mem_read(selected_home+0x9f,1))==(b'\0' if row==6 else b'\1')
        assert U.reg_read(UC_ARM64_REG_SP)==SP;menu_cases+=1
    # Exercise every patched width instruction; preserve live registers/flags.
    home=alloc(0x200);screen=alloc(0x200)
    q(B+h['home_class'],home);q(B+h['width_class'],screen)
    for stage,category in [(0,0),(1,0),(1,1),(1,2),(2,0)]:
        for logical_width in (176,200,224,256,320,800):
            w(home+216,stage);w(home+220,category);w(screen+304,logical_width)
            cols=max(3,min(5,(logical_width-64)//32))if(stage,category)==(1,0)else 3
            for site in h['width_hooks']:
                reset();primitives={};endpoints={B+site['site']+4}
                before=[r(i)for i in range(30)];run(site['site'])
                value=cols if site['kind']=='columns'else (56+32*cols)*(-1 if site['kind']=='negative'else 1)
                assert stopped==B+site['site']+4 and r(site['reg'])==value&0xffffffff
                for i in range(30):
                    if i!=site['reg']:assert r(i)==before[i],(i,site)
                assert U.reg_read(UC_ARM64_REG_NZCV)==0xa0000000 and U.reg_read(UC_ARM64_REG_SP)==SP
                width_cases+=1
    # Execute room title dispatch with absent, video-1-shifted and overwritten
    # server names. Known IDs always match the reference; unknown IDs survive.
    start=h['room_title_site']-8;default=start+0x44;custom=start+0x34
    empty=text('');font=alloc()
    for incoming in ({},faulty,{i:f'wrong after refresh {i}'for i in range(18)}):
        reset();primitives={0x12e8038:literal,0x1f64a4:lambda:ret(empty)}
        endpoints={B+default,B+custom}
        for room_id in [*range(18),18,128,254,255]:
            room=alloc();old=text(incoming.get(room_id,'server extra'if room_id>=18 else ''))
            q(room+16,old);U.mem_write(room+24,bytes([room_id,2,3]));saved=bytes(U.mem_read(room,0x20))
            q(SP+0x128,room);U.reg_write(X[29],SP+0x400);U.reg_write(X[19],ENV)
            run(start)
            title=rq(SP+0x400-0xf8)
            assert stopped==B+(default if room_id in (0,1,2,17)else custom)
            assert strings[title]==(expected.get(room_id,incoming.get(room_id,'server extra'))if room_id not in (0,1,2,17)else '')
            assert bytes(U.mem_read(room,0x20))==saved,'display must never rewrite room IDs, groups or routing'
            room_cases+=1
    # Follow the original fallback StringBuilder and both branches all the way
    # to the real native font draw call. This checks the visible text itself.
    builders={}
    def builder_new():p=alloc();builders[p]='';ret(p)
    def append_string():p=r(1);builders[p]+=strings[r(2)];ret(p)
    def append_int():p=r(1);builders[p]+=str(r(2));ret(p)
    for incoming in ({},faulty,{i:'wrong refresh title'for i in range(18)}):
        reset();primitives={0x12e8038:literal,0x1f64a4:lambda:ret(empty),
            branch(start+0x38):lambda:ret(font),branch(start+0x54):builder_new,
            branch(start+0x64):lambda:ret(),branch(start+0x6c):lambda:ret(text('Phòng')),
            branch(start+0x80):append_string,branch(start+0x90):lambda:ret(text(' ')),
            branch(start+0xa0):append_string,branch(start+0xc0):append_int,
            branch(start+0xd0):lambda:ret(text(builders[r(1)]))}
        endpoints={B+start+0x118}
        for room_id in range(18):
            room=alloc();q(room+16,text(incoming.get(room_id,'')));U.mem_write(room+24,bytes([room_id]))
            q(SP+0x128,room);U.reg_write(X[29],SP+0x400);U.reg_write(X[19],ENV)
            q(SP+0x400-0x30,alloc());run(start)
            assert stopped==B+start+0x118
            assert strings[r(3)]==expected.get(room_id,f'Phòng {room_id}')
            draw_cases+=1
    # Cache fast path and the native literal factory's volatile clobbering both
    # preserve every live register except the replaced load's destination x8.
    for room_id in range(18):
        reset();room=alloc();q(room+16,text('old'));U.mem_write(room+24,bytes([room_id]))
        U.reg_write(X[8],room);U.reg_write(X[19],ENV);primitives={0x12e8038:literal};endpoints=set()
        before=[r(i)for i in range(30)];run(R['room_title_hook'])
        for i in range(30):
            if i!=8:assert r(i)==before[i],i
        assert U.reg_read(UC_ARM64_REG_NZCV)==0xa0000000 and U.reg_read(UC_ARM64_REG_SP)==SP
        assert strings[r(8)]==expected.get(room_id,'')
        before_count=literal_calls;U.reg_write(X[8],room);run(R['room_title_hook']);assert literal_calls==before_count
        room_cases+=2
print(f'PASS: {menu_cases} native menu/selection cases, {width_cases} live-register width cases, {room_cases} reference-video room cases, {draw_cases} complete native title-to-font-draw paths across all six variants; original Quay số and Xem giờ preserved')
