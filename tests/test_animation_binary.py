"""ROM-free VANM v1 serializer tests using independently authored metadata."""
import json
import struct
import sys
import unittest
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pack_animation_binary import pack

ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/'assets/demo_animation.json').read_text(encoding='utf8'))

class AnimationBinaryTests(unittest.TestCase):
    def test_header_descriptor_crc_and_timing(self):
        data=pack(SOURCE)
        self.assertEqual(data[:4],b'VANM')
        self.assertEqual(struct.unpack_from('<5H',data,4),(1,4,4,5,0))
        self.assertEqual(struct.unpack_from('<I',data,14)[0],
                         zlib.crc32(data[18:])&0xffffffff)
        self.assertEqual(len(data),34+5*4)
        self.assertEqual(struct.unpack_from('<HBB',data,18),(0,1,1))
        self.assertEqual(struct.unpack_from('<HBB',data,22),(1,2,1))
        self.assertEqual(struct.unpack_from('<HBB',data,26),(3,1,0))
        self.assertEqual(struct.unpack_from('<HBB',data,30),(4,1,0))
        self.assertEqual(struct.unpack_from('<HH',data,38),(1,6))
        self.assertEqual(struct.unpack_from('<HH',data,42),(2,8))
    def test_modifiable_animation_durations(self):
        import copy
        custom=copy.deepcopy(SOURCE)
        custom['states']['run']['frames'][0]['ticks']=2
        self.assertNotEqual(pack(custom),pack(SOURCE))
        self.assertEqual(struct.unpack_from('<HH',pack(custom),38),(1,2))
    def test_schema_is_enforced(self):
        import copy
        custom=copy.deepcopy(SOURCE)
        custom['states']['fall']['frames'][0]['ticks']=0
        with self.assertRaises(ValueError):pack(custom)
    def test_total_frame_bound(self):
        import copy
        custom=copy.deepcopy(SOURCE)
        # Validator accepts <=64 per state: 4x64=256 exactly.
        for state in ('idle','run','rise','fall'):
            custom['states'][state]['frames']=[{'frame':0,'ticks':1}]*64
        self.assertEqual(len(pack(custom)),34+256*4)
    def test_reject_other_frame_count(self):
        import copy
        custom=copy.deepcopy(SOURCE)
        custom['atlas_frame_count']=0
        with self.assertRaises(ValueError):pack(custom)

if __name__=='__main__':unittest.main()
