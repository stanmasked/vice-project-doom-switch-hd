"""Only invented PPU frames. No original Vice: Project Doom graphics."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from stitch_stage_captures import sampled_tile,reconstruct,validate_manifest

MD5='f'*32

def fabricated_ppu(change=False):
    p=bytearray(0x4000)
    for nt in range(4):
        b=0x2000+nt*1024
        for y in range(30):
            for x in range(32):p[b+y*32+x]=(1+x+y*3+nt*32)&255
        for y in range(8):
            for x in range(8):p[b+960+y*8+x]=0b11100100
    if change:p[0x2001]=191
    return bytes(p)

def setup_capture(folder,prefix,frame,change=False,complete=True):
    path=folder/prefix
    Path(str(path)+'.ppu.bin').write_bytes(fabricated_ppu(change))
    Path(str(path)+'.meta.txt').write_text(
        f'format=fceux_ppu_snapshot_v4\nframe={frame}\nrom_md5={MD5}\n'
        f'register_log_complete={"yes" if complete else "no"}\n'
        f'dropped_register_writes={0 if complete else 1}\n',encoding='utf8')

def entry(prefix,frame,camera=0,scroll=0):
    return {
        'prefix':prefix,'frame':frame,'camera_x':camera,'camera_y':0,
        'scroll_x':scroll,'scroll_y':0,'nametable':0,
        'screen_y_start':0,'screen_y_end':16,
        'camera_source':'Debugger verified world camera RAM',
        'scroll_source':'Verified first and second PPUSCROLL writes'}

class StitchTests(unittest.TestCase):
    def test_tile_and_palette_across_nametable_boundaries(self):
        p=fabricated_ppu()
        self.assertEqual(sampled_tile(p,0,4,4,0,0),(1,0,0))
        self.assertEqual(sampled_tile(p,0,255,4,1,0),(33,0,1))
        self.assertEqual(sampled_tile(p,0,4,239,0,1),(65,0,2))
        self.assertEqual(sampled_tile(p,0,12,4,0,0),(2,0,0))
        self.assertEqual(sampled_tile(p,0,20,4,0,0)[1],1)
        with self.assertRaises(ValueError):
            sampled_tile(p,0,4,4,0,240)

    def test_two_frames_overlap_without_guessing(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            setup_capture(root,'a',120)
            setup_capture(root,'b',240)
            manifest={'schema':1,'rom_md5':MD5,
                      'captures':[entry('a',120),entry('b',240,8,8)]}
            report=reconstruct(manifest,root/'manifest.json')
            self.assertEqual(report['capture_count'],2)
            self.assertEqual(report['sampled_world_tiles'],66)
            self.assertEqual(report['repeated_world_tiles'],62)
            self.assertEqual(report['conflicting_world_tiles'],0)
            sample=next(p for p in report['tile_observations']
                        if p['world_tile_x']==1 and p['world_tile_y']==0)
            self.assertEqual(sample['agreed_tile_id'],2)
            self.assertEqual(sample['observations'],2)

    def test_conflicts_report_all_candidates_without_majority(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,frame,change in [('a',120,False),('b',240,True),
                                      ('c',360,False)]:
                setup_capture(root,name,frame,change)
            data={'schema':1,'rom_md5':MD5,
                  'captures':[entry('a',120),entry('b',240),entry('c',360)]}
            report=reconstruct(data,root/'manifest.json')
            self.assertEqual(report['conflicting_world_tiles'],1)
            sample=next(x for x in report['tile_observations']
                        if x['world_tile_x']==1 and x['world_tile_y']==0)
            self.assertTrue(sample['conflict'])
            self.assertIsNone(sample['agreed_tile_id'])
            self.assertEqual(sorted(v['count'] for v in sample['candidates']),[1,2])

    def test_fail_closed_evidence(self):
        data={'schema':1,'rom_md5':MD5,'captures':[entry('a',120)]}
        for key,value in [('camera_x',1),('scroll_y',240),
                          ('frame',True),('camera_source','no')]:
            modified=copy.deepcopy(data)
            modified['captures'][0][key]=value
            with self.assertRaises(ValueError,msg=key):
                validate_manifest(modified)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            setup_capture(root,'a',120,complete=False)
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                reconstruct(data,root/'manifest.json')
            report=reconstruct(data,root/'manifest.json',allow_incomplete=True)
            self.assertFalse(report['captures'][0]['log_complete'])
            setup_capture(root,'a',120)
            wrong=copy.deepcopy(data)
            wrong['rom_md5']='a'*32
            with self.assertRaisesRegex(ValueError,'ROM MD5'):
                reconstruct(wrong,root/'manifest.json')
            Path(str(root/'a')+'.ppu.bin').write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'16384'):
                reconstruct(data,root/'manifest.json')

    def test_invalid_manifest(self):
        with self.assertRaisesRegex(ValueError,'1..128'):
            validate_manifest({'schema':1,'rom_md5':MD5,'captures':[]})
        with self.assertRaises(ValueError):
            validate_manifest({'schema':True,'rom_md5':MD5,'captures':[entry('a',120)]})

if __name__=='__main__':
    unittest.main()
