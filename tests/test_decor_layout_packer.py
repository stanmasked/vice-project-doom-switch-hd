"""Validation of ROM-free JSON -> VLAY v1, no extracted NES layout data."""
import copy
import json
import struct
import sys
import unittest
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pack_decor_layout import validate,pack,generate_cpp
DATA=json.loads((Path(__file__).resolve().parents[1]/'assets/demo_decor_layout.json').read_text())

class LayoutPackerTests(unittest.TestCase):
    def test_binary_header_and_first_record(self):
        blob=pack(DATA)
        self.assertEqual(blob[:4],b'VLAY')
        self.assertEqual(struct.unpack_from('<4H',blob,4),(1,12,12,0))
        self.assertEqual(len(blob),16+12*12)
        self.assertEqual(struct.unpack_from('<I',blob,12)[0],
                         zlib.crc32(blob[16:])&0xffffffff)
        self.assertEqual(struct.unpack_from('<hhBBBBHH',blob,16),
                         (80,73,0,0,0,2,24,0))
        self.assertIn('kLayout{kPlacements, 12}',generate_cpp(DATA))
    def test_user_can_change_animation_and_positions(self):
        other=copy.deepcopy(DATA)
        other['objects'][0]['x']=200
        other['objects'][0]['period_ticks']=5
        self.assertNotEqual(pack(DATA),pack(other))
        self.assertEqual(struct.unpack_from('<hhBBBBHH',pack(other),16),
                         (200,73,0,0,0,2,5,0))
    def test_reject_unknown_and_boolean_values(self):
        for edit in (
            lambda d:d['objects'][0].update(x=True),
            lambda d:d['objects'][0].update(kind='bogus'),
            lambda d:d['objects'][0].update(layer='invalid'),
            lambda d:d['objects'][0].update(period_ticks=0),
            lambda d:d['objects'][0].update(phase_frames=-1),
            lambda d:d['objects'][0].update(first_frame=3,frames=2),
            lambda d:d['objects'][0].update(y=1500),
            lambda d:d.update(extra=3),
        ):
            data=copy.deepcopy(DATA)
            edit(data)
            with self.assertRaises(ValueError):
                pack(data)
    def test_bound_and_blank_file(self):
        data={'schema':1,'objects':[]}
        blank=pack(data)
        self.assertEqual(len(blank),16)
        self.assertEqual(struct.unpack_from('<I',blank,12)[0],0)
        with self.assertRaises(ValueError):generate_cpp(data)
        big=copy.deepcopy(DATA)
        big['objects']=big['objects']*6
        with self.assertRaises(ValueError):validate(big)
    def test_max_records(self):
        data=copy.deepcopy(DATA)
        data['objects']=(data['objects']*6)[:64]
        self.assertEqual(len(pack(data)),16+64*12)

if __name__=='__main__':
    unittest.main()
