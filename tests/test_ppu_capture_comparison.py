"""Invented PPU memory and RAM snapshots; no commercial game contents."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from compare_ppu_captures import compare

class CaptureDiffTests(unittest.TestCase):
    def test_nametable_changes_and_bounds(self):
        a=bytearray(16384);b=bytearray(16384)
        b[0x2000+32*3+4]=1
        b[0x2000+32*9+18]=2
        b[0x23c4]=0x82
        diff=compare((a,None,{'frame':'1'}),(b,None,{'frame':'2'}))
        self.assertEqual(diff['frame_before'],'1')
        self.assertEqual(diff['nametables'][0]['changed_tile_cells'],2)
        self.assertEqual(diff['nametables'][0]['changed_attribute_bytes'],1)
        self.assertEqual(diff['nametables'][0]['tile_bbox'],
            {'left':4,'top':3,'right':18,'bottom':9})
        self.assertEqual(diff['nametables'][1]['changed_tile_cells'],0)

    def test_mirrored_palette_does_not_double_count(self):
        a=bytearray(16384);b=bytearray(16384)
        b[0x3f01]=0x23
        b[0x3f10]=0x13
        diff=compare((a,None,{}),(b,None,{}))
        self.assertEqual(diff['palette_entries_changed'],
                         [{'entry':1,'old':0,'new':0x23}])

    def test_chr_ram_queue_and_oam_deltas(self):
        a=bytearray(16384);b=bytearray(16384)
        ra=bytearray(2048);rb=bytearray(2048)
        b[1025]=7
        rb[0x3d]=3
        rb[0x601]=4
        rb[0x701]=9
        diff=compare((a,ra,{}),(b,rb,{}))
        self.assertEqual(diff['mapped_chr_1k_changed_bytes'],[0,1,0,0,0,0,0,0])
        self.assertEqual(diff['chr_register_ram_changes'],
                         [{'register':0,'before':0,'after':3}])
        self.assertEqual(diff['queue_changed_bytes'],1)
        self.assertEqual(diff['oam_dma_0700_changed_slots'],1)

    def test_validation_and_missing_ram(self):
        a=bytearray(16384);b=bytearray(16384)
        self.assertNotIn('queue_changed_bytes',compare((a,None,{}),(b,bytes(2048),{})))
        with self.assertRaises(ValueError):
            compare((bytes(10),None,{}),(b,None,{}))
        with self.assertRaises(ValueError):
            compare((a,bytes(10),{}),(b,bytes(2048),{}))

if __name__=='__main__':unittest.main()
