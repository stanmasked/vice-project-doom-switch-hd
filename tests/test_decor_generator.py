"""Pure synthetic animation atlas, never original game files."""
import struct
import sys
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from build_demo_decor import FW,FH,COUNT,WIDTH,BODY,VPAT,make_header

class DecorGeneratorTests(unittest.TestCase):
    def test_format(self):
        self.assertEqual(VPAT[:4],b"VPAT")
        self.assertEqual(struct.unpack_from("<7H",VPAT,4),(1,96,32,24,32,4,0))
        self.assertEqual(len(VPAT),22+96*32*4)
        self.assertEqual(struct.unpack_from("<I",VPAT,18)[0],
                         zlib.crc32(BODY)&0xffffffff)
    def test_transparency_and_distinct_animation_poses(self):
        self.assertEqual(BODY[3],0)
        self.assertIn(255,BODY[3::4])
        self.assertIn(130,BODY[3::4])
        frames=[]
        for frame in range(COUNT):
            raw=bytearray()
            for y in range(FH):
                off=(y*WIDTH+frame*FW)*4
                raw.extend(BODY[off:off+FW*4])
            frames.append(bytes(raw))
        self.assertEqual(len(set(frames)),4)
    def test_generation_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/
                "tools/build_demo_decor.py"),str(root/"decor.hpp"),
                "--raw",str(root/"decor.vpat"),
                "--preview",str(root/"decor.ppm")],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((root/"decor.vpat").read_bytes(),VPAT)
            self.assertTrue((root/"decor.ppm").read_bytes().startswith(b"P6\n384 128\n255\n"))
    def test_cpp_blob_matches(self):
        self.assertEqual(make_header().count("0x"),len(VPAT))

if __name__=="__main__":
    unittest.main()
