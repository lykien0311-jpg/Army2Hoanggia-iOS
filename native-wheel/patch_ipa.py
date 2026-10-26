"""Static ARM64 hooks, with separate RX/RW segments and __LINKEDIT kept last.

This edits ONLY the exact, previously repaired native executable. No runtime
code patching/JIT, new network socket, embedded account, or server connection.
Use --prepare for inspectable native hooks without creating an installable IPA.
"""
from pathlib import Path
import struct, hashlib, json, argparse, zipfile
from keystone import Ks, KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN
BASE=0x100000000
ROOT=Path(__file__).resolve().parent
APP='Payload/Army2Hoanggia.app/'
EXPECTED_IPA='8c4779afad7981f4bf8cf5e756bdf03450437cc4e56cf949c805e2d2affc636d'
EXPECTED_ORIGINAL='34778a89dac9103a1fd62a6e712dce1bedd012da3bbb47c7ce908724b1d4c7d6'
PAGE=0x4000
KS=Ks(KS_ARCH_ARM64,KS_MODE_LITTLE_ENDIAN)
def asm(text,address):return bytes(KS.asm(text,address)[0])
def align(n,a=8):return (n+a-1)&-a
def cstr(b,offset):return bytes(b[offset:]).split(b'\0',1)[0].decode()
def commands(b):
    p=32
    for _ in range(struct.unpack_from('<I',b,16)[0]):
        cmd,size=struct.unpack_from('<II',b,p);yield p,cmd,size;p+=size
def segment(name,vm,off,size,prot,sections=()):
    data=struct.pack('<II16sQQQQiiII',25,72+80*len(sections),name.encode(),BASE+vm,size,off,size,prot,prot,len(sections),0)
    for sname,svm,soff,ssize,flags,alignment in sections:
        data+=struct.pack('<16s16sQQIIIIIIII',sname.encode(),name.encode(),BASE+svm,ssize,soff,alignment,0,0,flags,0,0,0)
    return data
def find_dlsym(b):
    for p,cmd,size in commands(b):
        if cmd==2:symoff,nsyms,stroff,strsize=struct.unpack_from('<4I',b,p+8)
        elif cmd==11:indoff,nind=struct.unpack_from('<2I',b,p+56)
        elif cmd==25:
            for i in range(struct.unpack_from('<I',b,p+64)[0]):
                q=p+72+80*i
                if cstr(b,q)=='__stubs':
                    va,sz,off=struct.unpack_from('<QQI',b,q+32);indstart,stride=struct.unpack_from('<II',b,q+68)
    for i in range(sz//stride):
        idx=struct.unpack_from('<I',b,indoff+(indstart+i)*4)[0]
        if idx&0xc0000000:continue
        name=struct.unpack_from('<I',b,symoff+16*idx)[0]
        if cstr(b,stroff+name)=='_dlsym':return va-BASE+i*stride
    raise ValueError('dlsym import not found')

def build_native(old,original,maps):
    assert hashlib.sha256(original).hexdigest()==EXPECTED_ORIGINAL
    assert len(old)==len(original)
    cmds=list(commands(old));segments=[(p,struct.unpack_from('<16sQQQQiiII',old,p+8))for p,c,s in cmds if c==25]
    assert segments[-1][1][0].rstrip(b'\0')==b'__LINKEDIT'
    link_p,link=segments[-1];rxvm=link[1]-BASE;rxoff=link[3];rwvm=rxvm+PAGE;rwoff=rxoff+PAGE;delta=2*PAGE
    assert rxvm%PAGE==rxoff%PAGE==0
    assert link[3]+link[4]==len(old)
    assert not any(c in (0x1d,0x80000034,0x80000033)for p,c,s in cmds), 'Unexpected signature/chained fixups/export trie'
    dlsym=find_dlsym(old);b=bytearray(old[:rxoff]+bytes(delta)+old[rxoff:]);rx=bytearray(PAGE);records=[];cursor=0
    symbols={};strcursor=0x3000
    for name in ('AGWheelOpen','AGWheelTick','AGWheelReceive','AGRoomReceive','AGRoomRebuild','Vòng xoay may mắn'):
        raw=name.encode('utf-8')+b'\0';symbols[name]=rxvm+strcursor;rx[strcursor:strcursor+len(raw)]=raw;strcursor+=len(raw)
    def lookup(symbol,slot):
        # Aligned 64-bit function pointer cache. All racing resolvers write the
        # same address. Cache pages are RW, never executable.
        ptr=rwvm+slot*8;string=symbols[symbol]
        return f'''
            adrp x9, {ptr&-4096}
            ldr x10, [x9, #{ptr&4095}]
            cbnz x10, resolved{slot}
            mov x0, #-2
            adrp x1, {string&-4096}
            add x1, x1, #{string&4095}
            bl {dlsym}
            adrp x9, {ptr&-4096}
            str x0, [x9, #{ptr&4095}]
            mov x10, x0
          resolved{slot}:
        '''
    def emit(code):
        nonlocal cursor
        addr=rxvm+cursor;raw=asm(code,addr);assert cursor+len(raw)<=0x3000
        rx[cursor:cursor+len(raw)]=raw;cursor=align(cursor+len(raw),16);return addr,raw
    def patch(at,raw,label):
        assert old[at:at+len(raw)]==original[at:at+len(raw)],(hex(at),label)
        records.append(dict(offset=at,label=label,before=b[at:at+len(raw)].hex(),after=raw.hex()))
        b[at:at+len(raw)]=raw
    hooks=[]
    for i,m in enumerate(maps):
        open_addr,raw=emit(f'''
            stp x29, x30, [sp, #-32]!
            mov x29, sp
            str x0, [sp, #16]
            {lookup('AGWheelOpen',0)}
            cbz x10, done
            ldr x0, [sp, #16]
            mov w1, #{i}
            blr x10
          done:
            ldp x29, x30, [sp], #32
            ret
        ''')
        patch(m['clock'],asm(f'b {open_addr}',m['clock']),f'V{i+1} clock action opens native wheel')
        receive_addr,raw=emit(f'''
            cbz x2, original
            ldrsb w9, [x2, #48]
            cmn w9, #101
            b.eq wheel
            cmn w9, #19
            b.ne original
            stp x29, x30, [sp, #-48]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            str x2, [sp, #32]
            {lookup('AGRoomReceive',3)}
            cbz x10, fallback
            ldr x0, [sp, #16]
            ldr x1, [sp, #32]
            mov w2, #{i}
            blr x10
            cbz w0, fallback
            ldp x29, x30, [sp], #48
            ret
          wheel:
            stp x29, x30, [sp, #-48]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            str x2, [sp, #32]
            {lookup('AGWheelReceive',2)}
            cbz x10, fallback
            ldr x0, [sp, #16]
            ldr x1, [sp, #32]
            mov w2, #{i}
            blr x10
            ldp x29, x30, [sp], #48
            ret
          fallback:
            ldp x0, x1, [sp, #16]
            ldr x2, [sp, #32]
            ldp x29, x30, [sp], #48
          original:
            stp x28, x27, [sp, #-96]!
            b {m['controller']+4}
        ''')
        assert original[m['controller']:m['controller']+4]==asm('stp x28, x27, [sp, #-96]!',0)
        patch(m['controller'],asm(f'b {receive_addr}',m['controller']),f'V{i+1} receive wheel -101 and cache room names -19')
        build_addr,raw=emit(f'''
            stp x29, x30, [sp, #-48]!
            mov x29, sp
            stp x0, x1, [sp, #16]
            bl {m['room_build']}
            str x0, [sp, #32]
            {lookup('AGRoomRebuild',4)}
            cbz x10, done
            ldp x0, x1, [sp, #16]
            mov w2, #{i}
            blr x10
          done:
            ldr x0, [sp, #32]
            ldp x29, x30, [sp], #48
            ret
        ''')
        assert original[m['room_build_call']:m['room_build_call']+4]==asm(f"bl {m['room_build']}",m['room_build_call'])
        patch(m['room_build_call'],asm(f'bl {build_addr}',m['room_build_call']),f'V{i+1} replay names after room list rebuild')
        tick_addr,raw=emit(f'''
            stp x29, x30, [sp, #-32]!
            mov x29, sp
            str x0, [sp, #16]
            {lookup('AGWheelTick',1)}
            cbz x10, original
            ldr x0, [sp, #16]
            mov w1, #{i}
            blr x10
          original:
            ldr x0, [sp, #16]
            bl {m['speed']}
            ldp x29, x30, [sp], #32
            ret
        ''')
        assert original[m['tick']:m['tick']+4]==asm(f"bl {m['speed']}",m['tick'])
        patch(m['tick'],asm(f'bl {tick_addr}',m['tick']),f'V{i+1} poll/send on original game thread')
        hooks.append(dict(variant=i,open_hook=open_addr,receive_hook=receive_addr,tick_hook=tick_addr,room_build_hook=build_addr,**m))
    label=symbols['Vòng xoay may mắn']
    patch(0x5bd138,asm(f'adrp x2, {label&-4096}; add x2, x2, #{label&4095}; mov w3, #{len("Vòng xoay may mắn")}',0x5bd138),'Shared V9 menu label')
    b[rxoff:rxoff+PAGE]=rx
    # Relocate only link-edit FILE offsets; no original text/data VM address
    # changes. Existing rebases/bindings target segment 1/2, never LINKEDIT.
    load=[]
    file_fields={2:[8,16],11:[32,40,48,56,64,72],0x22:[8,16,24,32,40],0x80000022:[8,16,24,32,40],0x26:[8],0x29:[8],0x2e:[8],0x1e:[8]}
    for p,cmd,size in cmds:
        c=bytearray(old[p:p+size])
        if p==link_p:
            load.append(segment('__AGWHEEL',rxvm,rxoff,PAGE,5,[('__text',rxvm,rxoff,0x3000,0x80000400,2),('__cstring',rxvm+0x3000,rxoff+0x3000,strcursor-0x3000,2,0)]))
            load.append(segment('__AGDATA',rwvm,rwoff,PAGE,3,[('__data',rwvm,rwoff,40,0,3)]))
            struct.pack_into('<Q',c,24,link[1]+delta);struct.pack_into('<Q',c,40,rxoff+delta)
        for field in file_fields.get(cmd,[]):
            value=struct.unpack_from('<I',c,field)[0]
            if value:
                assert value>=rxoff,(hex(cmd),field,hex(value));struct.pack_into('<I',c,field,value+delta)
        if cmd==25:
            for j in range(struct.unpack_from('<I',c,64)[0]):
                q=72+80*j;reloc=struct.unpack_from('<I',c,q+56)[0]
                if reloc:assert reloc>=rxoff;struct.pack_into('<I',c,q+56,reloc+delta)
        load.append(bytes(c))
    dylib=b'@executable_path/Frameworks/AGWheel.dylib\0';sz=align(24+len(dylib))
    # clang's default LC_ID_DYLIB version is 0.0.0. Do not demand 1.0.0
    # here: dyld would reject the correctly built module as incompatible.
    load.append(struct.pack('<6I',12,sz,24,0,0,0)+dylib+bytes(sz-24-len(dylib)))
    header=b''.join(load);assert 32+len(header)<0x8000
    b[32:32+len(header)]=header;struct.pack_into('<II',b,16,len(load),len(header))
    return bytes(b),dict(hooks=hooks,patches=records,rxvm=rxvm,rxoff=rxoff,rwvm=rwvm,rwoff=rwoff,code_size=cursor,dlsym=dlsym,linkedit_shift=delta)

def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--dylib',type=Path,default=ROOT/'build/AGWheel.dylib');p.add_argument('--output',type=Path,default=Path('deliverables/Army2Hoanggia-LuckyWheel-Test.ipa'));args=p.parse_args()
    source=Path('deliverables/Army2Hoanggia-Room-Clan-Fix.ipa');assert hashlib.sha256(source.read_bytes()).hexdigest()==EXPECTED_IPA
    with zipfile.ZipFile(source)as z:old=z.read(APP+'Army2Hoanggia')
    original=Path('inspect-ipa/Army2Hoanggia').read_bytes();maps=json.loads((ROOT/'native-map.json').read_text())
    native,report=build_native(old,original,maps);(ROOT/'build').mkdir(exist_ok=True)
    (ROOT/'build/prepared-native').write_bytes(native);(ROOT/'build/hook-report.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.prepare:print('Prepared native hooks only. No IPA has been created.');return
    lib=args.dylib.read_bytes();assert lib[:4]==bytes.fromhex('cffaedfe')
    assert struct.unpack_from('<I',lib,4)[0]==0x100000c
    assert struct.unpack_from('<I',lib,12)[0]==6 # MH_DYLIB
    versions=[struct.unpack_from('<II',lib,p+8)for p,c,s in commands(lib)if c==0x32]
    assert versions and all(platform==2 and minimum<=0xc0000 for platform,minimum in versions),'Require device iOS dylib supporting iOS 12'
    for name in (b'_AGWheelOpen\0',b'_AGWheelReceive\0',b'_AGWheelTick\0',b'_AGRoomReceive\0',b'_AGRoomRebuild\0'):assert name in lib
    assert b'_AGWheelPreview'not in lib,'Simulator fixture must not enter IPA'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(source)as src,zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as dst:
        for info in src.infolist():
            if '/_CodeSignature/'in info.filename or info.filename.endswith('embedded.mobileprovision'):continue
            dst.writestr(info,native if info.filename==APP+'Army2Hoanggia'else src.read(info.filename))
        info=zipfile.ZipInfo(APP+'Frameworks/AGWheel.dylib');info.create_system=3;info.external_attr=0o100755<<16;info.compress_type=zipfile.ZIP_DEFLATED;dst.writestr(info,lib)
    print(args.output,hashlib.sha256(args.output.read_bytes()).hexdigest())
if __name__=='__main__':main()
