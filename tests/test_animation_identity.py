"""Synthetic atlas identity binding tests; no extracted game graphics."""
import copy
import json
import struct
import sys
import unittest
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pack_animation_binary import pack,atlas_identity

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'assets/demo_animation.json').read_text(encoding='utf8'))

def fake_atlas(frames=4,alter=False):
    w,h=frames,1
    pixels=bytearray(w*h*4)
    for x in range(w):
        pixels[4*x:4*x+4]=bytes([17+x,24+x,50+x,255])
    if alter:pixels[0]^=0x11
    crc=zlib.crc32(pixels)&0xffffffff
    return b'VPAT'+struct.pack('<7H',1,w,h,1,1,frames,0)+struct.pack('<I',crc)+pixels

class AtlasBoundAnimationTests(unittest.TestCase):
    def test_v2_binding_is_exact_to_payload_crc(self):
        atlas=fake_atlas()
        raw=pack(MANIFEST,atlas)
        self.assertEqual(raw[:4],b'VANM')
        self.assertEqual(struct.unpack_from('<5H',raw,4),(2,4,4,5,0))
        self.assertEqual(struct.unpack_from('<I',raw,14)[0],
                         zlib.crc32(raw[18:])&0xffffffff)
        self.assertEqual(struct.unpack_from('<I',raw,18)[0],
                         struct.unpack_from('<I',atlas,18)[0])
        self.assertEqual(len(raw),58)
        self.assertEqual(struct.unpack_from('<HBB',raw,22),(0,1,1))
        self.assertEqual(struct.unpack_from('<HBB',raw,26),(1,2,1))
        self.assertEqual(struct.unpack_from('<HH',raw,42),(1,6))
    def test_legacy_v1_remains_unchanged(self):
        v1=pack(MANIFEST)
        self.assertEqual(struct.unpack_from('<H',v1,4)[0],1)
        self.assertEqual(len(v1),54)
        self.assertEqual(struct.unpack_from('<HBB',v1,18),(0,1,1))
    def test_different_same_frame_count_has_different_identity(self):
        a,b=fake_atlas(),fake_atlas(alter=True)
        self.assertNotEqual(atlas_identity(a)[1],atlas_identity(b)[1])
        self.assertNotEqual(pack(MANIFEST,a),pack(MANIFEST,b))
    def test_corrupt_and_wrong_frame_atlases_refused(self):
        bad=bytearray(fake_atlas());bad[-1]^=1
        with self.assertRaisesRegex(ValueError,'checksum'):pack(MANIFEST,bytes(bad))
        with self.assertRaisesRegex(ValueError,'frame-count'):
            pack(MANIFEST,fake_atlas(frames=3))
        bad=bytearray(fake_atlas());bad[0]=ord('X')
        with self.assertRaisesRegex(ValueError,'Invalid VPAT'):
            pack(MANIFEST,bytes(bad))
    def test_authored_frame_times_change_but_identity_persists(self):
        atlas=fake_atlas()
        data=copy.deepcopy(MANIFEST)
        data['states']['run']['frames'][0]['ticks']=2
        a,b=pack(MANIFEST,atlas),pack(data,atlas)
        self.assertNotEqual(a,b)
        self.assertEqual(a[18:22],b[18:22])
        self.assertEqual(struct.unpack_from('<HH',b,42),(1,2))

if __name__=='__main__':unittest.main()
