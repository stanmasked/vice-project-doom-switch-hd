"""Invented RGB source only; test private contact sheet composition."""
from pathlib import Path
import sys
import tempfile
import unittest
import struct
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_private_fceux_contact_sheet import make_sheet
from test_audit_private_fceux_storyboard import capture

def unpack_png(path):
    data=path.read_bytes()
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    index=8
    width=height=None
    idat=[]
    while index<len(data):
        n=struct.unpack('>I',data[index:index+4])[0]
        typ=data[index+4:index+8]
        content=data[index+8:index+8+n]
        index+=12+n
        if typ==b'IHDR':
            width,height,depth,color,comp,fil,inter=struct.unpack('>IIBBBBB',content)
            assert (depth,color,comp,fil,inter)==(8,2,0,0,0)
        elif typ==b'IDAT':
            idat.append(content)
        elif typ==b'IEND':
            break
    return width,height,zlib.decompress(b''.join(idat))

class ContactSheetTests(unittest.TestCase):
    def test_complete_two_frames_png_dimensions_and_pixels(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            root=base/'caps';root.mkdir()
            capture(root,8,stop=16)
            capture(root,16,stop=16)
            target=base/'sheet.png'
            result=make_sheet(root,target,columns=2)
            self.assertEqual(result['frame_numbers'],[8,16])
            self.assertTrue(result['complete_window_verified'])
            width,height,raw=unpack_png(target)
            self.assertEqual((width,height),(512,256))
            offset=16*(1+width*3)+1
            self.assertEqual(raw[offset:offset+3],b'\x01\x02\x03')
            self.assertEqual(raw[offset+256*3:offset+256*3+3],b'\x01\x02\x03')

    def test_incomplete_rejected_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);root=base/'caps';root.mkdir()
            capture(root,8,stop=16)
            with self.assertRaisesRegex(ValueError,'window incomplete'):
                make_sheet(root,base/'sheet.png')
            self.assertFalse((base/'sheet.png').exists())

    def test_partial_opt_in(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);root=base/'caps';root.mkdir()
            capture(root,8,stop=16)
            v=make_sheet(root,base/'sheet.png',require_complete=False)
            self.assertEqual(v['sample_count'],1)
            self.assertFalse(v['complete_window_verified'])

    def test_reject_destination_inside_capture_dir(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);capture(root,8)
            with self.assertRaisesRegex(ValueError,'outside strict capture'):
                make_sheet(root,root/'sheet.png',require_complete=False)

    def test_reject_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);root=base/'caps';root.mkdir()
            capture(root,8)
            target=base/'sheet.png';target.write_bytes(b'prior')
            with self.assertRaisesRegex(ValueError,'refusing to overwrite'):
                make_sheet(root,target,require_complete=False)
            self.assertEqual(target.read_bytes(),b'prior')

    def test_reject_invalid_column_count(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);root=base/'caps';root.mkdir()
            capture(root,8)
            with self.assertRaisesRegex(ValueError,'columns'):
                make_sheet(root,base/'sheet.png',columns=9)

if __name__=='__main__':
    unittest.main()
