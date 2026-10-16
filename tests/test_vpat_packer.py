"""All VPAT input sprites are invented in memory; no game art."""
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pack_vpat import cpp_header,pack_image


class VpatPackTests(unittest.TestCase):
    def test_pack_rgba_and_crc(self):
        with tempfile.TemporaryDirectory() as folder:
            png=Path(folder)/'sprite.png'
            image=Image.new('RGBA',(24,12),(100,30,10,0))
            image.putpixel((0,0),(210,190,40,128))
            image.putpixel((13,0),(200,20,50,255))
            image.save(png)
            data=pack_image(png,12,12,2)
            self.assertEqual(data[:4],b'VPAT')
            self.assertEqual(struct.unpack_from('<7H',data,4),(1,24,12,12,12,2,0))
            self.assertEqual(struct.unpack_from('<I',data,18)[0],zlib.crc32(data[22:]))
            self.assertEqual(data[22:26],bytes((210,190,40,128)))
            self.assertEqual(data[22+4*13:22+4*14],bytes((200,20,50,255)))
            self.assertIn('inline constexpr unsigned char kAtlasBlob[]',cpp_header(data))

    def test_rgb_is_converted_to_opaque(self):
        with tempfile.TemporaryDirectory() as folder:
            png=Path(folder)/'rgb.png'
            Image.new('RGB',(8,8),(2,3,4)).save(png)
            data=pack_image(png,8,8,1)
            self.assertEqual(data[22:26],bytes((2,3,4,255)))

    def test_reject_non_tiling_and_invalid_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            png=Path(folder)/'atlas.png'
            Image.new('RGBA',(24,12)).save(png)
            for fw,fh,count in ((7,12,1),(12,5,1),(12,12,3),(12,12,0),(0,12,1)):
                with self.assertRaises(ValueError):pack_image(png,fw,fh,count)

    def test_reject_invalid_identifiers(self):
        for namespace,symbol in (('invalid space','kAtlasBlob'),('vpd','a;evil'),('2bad','okay')):
            with self.assertRaises(ValueError):cpp_header(b'abc',namespace,symbol)

    def test_reject_oversized_image(self):
        with tempfile.TemporaryDirectory() as folder:
            png=Path(folder)/'huge.png'
            Image.new('RGBA',(1025,1)).save(png)
            with self.assertRaises(ValueError):pack_image(png,1,1,1025)

if __name__=='__main__':unittest.main()
