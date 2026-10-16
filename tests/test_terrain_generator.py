"""Invented environmental tiles only; no commercial tile sheets."""
import sys
import tempfile
import unittest
import struct
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_demo_terrain import SIDE,FRAMES,WIDTH,HEIGHT,DATA,VPAT,header_text,main

class TerrainGeneratorTests(unittest.TestCase):
    def test_vpat_layout_and_crc(self):
        self.assertEqual(VPAT[:4],b'VPAT')
        self.assertEqual(struct.unpack_from('<7H',VPAT,4),(1,64,16,16,16,4,0))
        self.assertEqual(struct.unpack_from('<I',VPAT,18)[0],
                         zlib.crc32(DATA)&0xffffffff)
        self.assertEqual(len(VPAT),22+64*16*4)
        self.assertEqual(set(DATA[3::4]),{255})
    def test_four_distinct_original_patterns(self):
        rows=[]
        for frame in range(4):
            texels=bytearray()
            for y in range(16):
                start=(y*64+frame*16)*4
                texels.extend(DATA[start:start+16*4])
            rows.append(bytes(texels))
        self.assertEqual(len(set(rows)),4)
        self.assertEqual(rows[0][:4],bytes((137,215,198,255)))
    def test_generated_header_and_raw_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            import subprocess
            process=subprocess.run([sys.executable,
                str(Path(__file__).resolve().parents[1]/'tools'/'build_demo_terrain.py'),
                str(root/'demo_terrain.hpp'),'--raw',str(root/'terrain.vpat'),
                '--preview',str(root/'terrain.ppm')],capture_output=True,text=True)
            self.assertEqual(process.returncode,0,process.stderr)
            self.assertEqual((root/'terrain.vpat').read_bytes(),VPAT)
            self.assertIn('namespace vpd_terrain', (root/'demo_terrain.hpp').read_text())
            self.assertTrue((root/'terrain.ppm').read_bytes().startswith(b'P6\n384 96\n255\n'))
    def test_header_preserves_payload(self):
        self.assertEqual(header_text(VPAT).count('0x'),len(VPAT))

if __name__=='__main__':unittest.main()
