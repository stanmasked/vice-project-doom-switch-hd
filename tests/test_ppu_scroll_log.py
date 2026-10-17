"""Invented PPU register events; no original commercial game traces."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_ppu_scroll_log import analyze


class ScrollEventTests(unittest.TestCase):
    def test_status_read_resets_write_toggle(self):
        events=[(10,0x2005,17),(10,0x2002,0),(10,0x2000,3),
                (10,0x2005,250),(10,0x2005,40)]
        r=analyze(events)
        self.assertEqual(r['total_complete_scroll_pairs'],1)
        self.assertEqual(r['frames'][0]['unresolved_scroll_writes'],1)
        self.assertEqual(r['frames'][0]['last_observed_nametable'],3)
        self.assertEqual(r['frames'][0]['last_complete_scroll_pair'],
                         {'x':250,'y':40,'normal_vertical_range':True})

    def test_mirrored_ppustatus_scroll_ctrl_and_addr(self):
        # $3FFA mirrors $2002; $200D mirrors $2005; $3456 mirrors $2006.
        events=[(0,0x200D,9),(0,0x3FFA,0),(0,0x3FF8,2),
                (0,0x200D,21),(0,0x3FFD,41),
                (1,0x3456,0x23),(1,0x200D,90),
                (1,0x200D,100)]
        result=analyze(events)
        self.assertEqual(result['frames'][0]['status_reads'],1)
        self.assertEqual(result['frames'][0]['last_observed_nametable'],2)
        self.assertEqual(result['frames'][0]['last_complete_scroll_pair']['x'],21)
        self.assertEqual(result['frames'][0]['last_complete_scroll_pair']['y'],41)
        self.assertEqual(result['frames'][1]['address_writes'],1)
        self.assertEqual(result['frames'][1]['completed_scroll_pairs'],1)
        self.assertEqual(result['frames'][1]['last_complete_scroll_pair']['y'],100)

    def test_ppuaddr_interferes_with_scroll_pair(self):
        events=[(0,0x2002,0),(0,0x2005,50),(0,0x2006,0x23),
                (0,0x2005,70),(0,0x2005,80),(0,0x2005,90)]
        r=analyze(events)
        self.assertEqual(r['total_complete_scroll_pairs'],1)
        self.assertEqual(r['frames'][0]['last_complete_scroll_pair']['x'],70)
        self.assertEqual(r['frames'][0]['last_complete_scroll_pair']['y'],80)

    def test_y_240_is_unmodeled_by_static_renderer(self):
        r=analyze([(0,0x2002,0),(0,0x2005,10),(0,0x2005,240)])
        self.assertFalse(r['frames'][0]['last_complete_scroll_pair']['normal_vertical_range'])

    def test_carry_forward_last_observation(self):
        r=analyze([(10,0x2002,0),(10,0x2005,4),(10,0x2005,5),
                   (11,0x8000,7)])
        self.assertEqual(r['frames'][1]['last_complete_scroll_pair']['x'],4)
        self.assertEqual(r['frames'][1]['completed_scroll_pairs'],0)

    def test_out_of_order_frame_log(self):
        self.assertTrue(analyze([(15,0x2002,0),(14,0x2005,3)])
                        ['out_of_order_frame_numbers'])


if __name__=='__main__':
    unittest.main()
