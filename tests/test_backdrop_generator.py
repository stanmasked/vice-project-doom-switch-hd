"""Invented background silhouettes only; no NES references."""
import sys
import subprocess
import tempfile
import unittest
import struct
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_demo_backdrop import W,H,COUNT,TOTAL_WIDTH,PAYLOAD,ATLAS,make_header

class DemoBackdropTests(unittest.TestCase):
    def test_vpat_structure(self):
        self.assertEqual(ATLAS[:4],b'VPAT')
        self.assertEqual(struct.unpack_from('<7H',ATLAS,4),
                         (1,256,96,128,96,2,0))
        self.assertEqual(len(ATLAS),22+256*96*4)
        self.assertEqual(zlib.crc32(PAYLOAD)&0xffffffff,
                         struct.unpack_from('<I',ATLAS,18)[0])
    def test_transparent_sky_and_opaque_city(self):
        self.assertEqual(PAYLOAD[(3*256+2)*4+3],0)
        self.assertEqual(PAYLOAD[(93*256+2)*4+3],255)
        self.assertEqual(PAYLOAD[(93*256+130)*4+3],255)
        self.assertNotEqual(PAYLOAD[(93*256+2)*4:(93*256+2)*4+3],
                            PAYLOAD[(93*256+130)*4:(93*256+130)*4+3])
    def test_output_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            gen=Path(__file__).resolve().parents[1]/'tools/build_demo_backdrop.py'
            result=subprocess.run([sys.executable,str(gen),
                                   str(root/'demo.hpp'),'--raw',str(root/'demo.vpat'),
                                   '--preview',str(root/'preview.ppm')],
                                   capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((root/'demo.vpat').read_bytes(),ATLAS)
            self.assertIn('namespace vpd_backdrop',(root/'demo.hpp').read_text())
            self.assertTrue((root/'preview.ppm').read_bytes().startswith(b'P6\n512 192\n255\n'))
    def test_header_matches_payload(self):
        self.assertEqual(make_header().count('0x'),len(ATLAS))

if __name__=='__main__':unittest.main()
