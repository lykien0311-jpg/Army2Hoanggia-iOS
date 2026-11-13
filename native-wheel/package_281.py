"""Apply the six shared native leaderboard hooks to the exact supplied B280."""
from hashlib import sha256
from pathlib import Path
from struct import pack_into,unpack_from
from patch_menu_269 import branch,address,add,mov

BASE_NATIVE='917c6479a14187d4deb5538b58cdfc245dfba92f34fb85a79a71d23dce41e63c'
SITES=[0x54b838,0x637034,0x71bcf8,0x8009bc,0x8e5680,0x9ca344]
RENDER=[0x5931e8,0x67c754,0x761418,0x8460dc,0x92ada0,0xa0fa64]
SCENE=0x2508000
FILE=0x24c8000

def patch(native):
    assert sha256(native).hexdigest()==BASE_NATIVE,'Use the attached Build280 executable'
    data=bytearray(native)
    for v,(site,target)in enumerate(zip(SITES,RENDER)):
        assert unpack_from('<I',data,site)[0]==branch(site,target,True)
        # Every leaderboard uses the actual row User in x24, never the viewer.
        assert pack(0x39c36702) in data[site-80:site],hex(site)
        at=SCENE+0x1000+v*32
        words=[mov(8,v*16+4),address(at+4,target,9,page=True),add(9,target&4095),0xaa1803ea,branch(at+16,SCENE)]
        offset=FILE+at-SCENE
        assert data[offset:offset+len(words)*4]==bytes(len(words)*4)
        pack_into('<5I',data,offset,*words)
        pack_into('<I',data,site,branch(site,at,True))
    return bytes(data)

def pack(word):return word.to_bytes(4,'little')

if __name__=='__main__':
    import sys
    source,target=map(Path,sys.argv[1:]);target.write_bytes(patch(source.read_bytes()))
    print('B281 native rank hooks',sha256(target.read_bytes()).hexdigest())
