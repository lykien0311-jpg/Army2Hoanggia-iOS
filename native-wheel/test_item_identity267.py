"""Verify native item identity in class descriptors and original selection code."""
import json,struct
from pathlib import Path
from patch_ipa import asm
R=Path(__file__).resolve().parent
b=(R.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes();base=0x100000000
proof=json.loads((R/'item-identity267.json').read_text());maps=json.loads((R/'stats-map.json').read_text())
pattern=asm('ldur x9,[x29,#-40];ldr x10,[sp,#56];ldr x9,[x9,#136];ldr w2,[sp,#52];ldr w10,[x10,#176]',0)
for p,m in zip(proof,maps):
    cls=int(p['class_info_offset'],16);name=struct.unpack_from('<Q',b,cls+0x10)[0]-base
    assert b[name:].split(b'\0',1)[0].decode()==p['class']
    fields={}
    for a in range(cls+0x58,cls+0x400,8):
        ptr=struct.unpack_from('<Q',b,a)[0]-base
        if not 0<=ptr<len(b):continue
        name=b[ptr:ptr+50].split(b'\0',1)[0];flags=struct.unpack_from('<I',b,a-4)[0];offset=struct.unpack_from('<I',b,a+8)[0]
        if(name==b'a'and flags==0x5001)or(name==b'b'and flags==0x6001):fields[name.decode()]=(flags,offset)
    assert fields=={'a':(0x5001,0xb0),'b':(0x6001,0x80)},fields
    lo=m['calculate']-0x1000;hi=m['calculate'];at=b.find(pattern,lo,hi)
    assert at>=0 and b.find(pattern,at+4,hi)<0
    p['original_selection_handle_load']=hex(at+16)
report=dict(passed=True,variants=6,descriptors_and_selection_loads=12,proof=proof)
(R/'build/item-identity267-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS 12 native class-descriptor and selection-instruction identity proofs')
