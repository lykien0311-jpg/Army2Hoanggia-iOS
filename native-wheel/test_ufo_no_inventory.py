"""All standard weapons; only full-rage POW, never inventory selections."""
from ufo_native_encounter import *
weapons=(0,1,2,9,10,11,19,21,17,49);cases=0
for v in range(6):
    for character,bullet in enumerate(weapons):
        for rage in (0,99,100):
            s=w.setup(v,8+(character%2),capacity=100,local=0);init_native(s,v)
            p=s['p'];t.put(p+0x16c,'<B',character)
            owner(v,8,1);assert t.get(s['ag']+0xd0,'<B')==8
            owner(v,0,2)
            w.receive(v,-115,struct.pack('>iBQHBBhh',2,0,900002,173,28,13,240,350))
            settle_local(s,v)
            # A previous inventory-selection/animation state cannot change
            # the normal weapon mapper or issue any inventory use request.
            t.put(p+0x134,'<i',30);t.put(p+0x16a,'<B',1);t.put(p+0x172,'<B',rage)
            w.packets.clear();w.settle(v)
            expected=([(26,b'\x64')]if rage==100 else[])+[w.expected(bullet)]
            assert w.packets==expected,(v,character,rage,w.packets,expected)
            w.settle(v);assert w.packets==expected,'No repeat skill or shot'
            assert all(cmd==22 or (cmd==26 and payload==b'\x64')for cmd,payload in w.packets)
            assert t.get(p+0x172,'<B')==(0 if rage==100 else rage)
            assert t.get(p+0x134,'<i')==(100 if rage==100 else 30)
            cases+=1
print('PASS:',cases,'compiled ARM64 normal weapon/skill cases across6 variants and10 characters; rage0/99/100, POW token100 only, no inventory-use packets')
