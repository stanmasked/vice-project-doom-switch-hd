"""Synthetic FCEUX cycle trace tests; zero commercial game data."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_ppu_cycle_trace import (HEADER,parse_events,summarize,
                                     check_capture_meta)


class CycleTraceTests(unittest.TestCase):
    def test_mmc3_writes_and_offsets(self):
        events=[(12,100,0x8000,0x80,'W'),(12,108,0x8001,0x12,'W'),
                (12,119,0x2002,0,'R'),(12,130,0x2005,0x25,'W'),
                (13,29900,0x8000,0x81,'W'),(13,29912,0x8001,0x26,'W')]
        r=summarize(events)
        self.assertEqual(r['total_events'],6)
        self.assertEqual([x['register'] for x in r['chr_events']],[0,1])
        self.assertEqual(r['frames'][0]['chr_events'][0]['cycles_since_first_logged_event_this_frame'],8)
        self.assertEqual(r['frames'][1]['chr_events'][0]['cycles_since_first_logged_event_this_frame'],12)
        self.assertEqual(r['frames'][0]['ppu_status_reads'],1)
        self.assertEqual(r['frames'][0]['scroll_write_count'],1)
        self.assertEqual(r['frames_with_all_six_chr_values'],0)

    def test_mmc3_mirrored_select_and_data_order(self):
        events=[(2,100,0x8002,0x80,'W'),(2,110,0x8003,8,'W'),
                (2,120,0x9FFE,0x85,'W'),(2,130,0x9FFF,12,'W'),
                (2,140,0xA003,1,'W'),(2,150,0xC002,2,'W'),
                (2,160,0xEFFF,3,'W')]
        r=summarize(events)
        self.assertEqual([e['register'] for e in r['chr_events']],[0,5])
        self.assertEqual(r['frames'][0]['mapper_writes'],4)
        self.assertEqual(r['chr_events'][1]['cpu_cycle'],130)

    def test_counter_reset_creates_new_epoch(self):
        r=summarize([(0,490,0x8000,0,'W'),
                     (0,510,0x8001,7,'W'),
                     (1,5,0x8000,1,'W'),
                     (1,10,0x8001,10,'W')])
        self.assertEqual(r['cpu_clock_resets_or_discontinuities'],1)
        self.assertEqual(r['chr_events'][1]['counter_epoch'],1)
        self.assertFalse(r['out_of_order_frame_numbers'])
        self.assertEqual(r['frames'][1]['chr_events'][0]['cycles_since_first_logged_event_this_frame'],5)

    def test_unobserved_registers_never_guessed(self):
        r=summarize([(0,10,0x8001,3,'W')])
        self.assertEqual(r['unpaired_mmc3_data_writes'],1)
        self.assertEqual(r['frames_with_all_six_chr_values'],0)
        self.assertEqual(r['frames'][0]['observed_chr_registers'],[None]*6)

    def test_all_register_values_available(self):
        events=[]
        for n in range(6):
            events.extend([(0,10+10*n,0x8000,n,'W'),
                           (0,14+10*n,0x8001,2*n,'W')])
        self.assertEqual(summarize(events)['frames_with_all_six_chr_values'],1)

    def test_parse_format_and_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'timed.tsv'
            path.write_text(HEADER+'\n0\t1200\t8000\t80\tW\n'
                                       '0\t1205\t2002\t00\tR\n',encoding='utf8')
            self.assertEqual(list(parse_events(path)),
                             [(0,1200,0x8000,0x80,'W'),(0,1205,0x2002,0,'R')])
            path.write_text(HEADER+'\n0\t1205\t2001\t00\tR\n',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'Unexpected read'):
                list(parse_events(path))
            path.write_text(HEADER+'\n1\t1205\tGG\t00\tW\n',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'Invalid numeric'):
                list(parse_events(path))
            path.write_text('frame\taddress\tvalue\n',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'header'):
                list(parse_events(path))

    def test_capture_metadata_safety(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'capture.meta.txt'
            path.write_text('register_log_complete=no\ncycle_trace_available=yes\n')
            with self.assertRaisesRegex(ValueError,'dropped'):
                check_capture_meta(path)
            path.write_text('register_log_complete=yes\ncycle_trace_available=no\n')
            with self.assertRaisesRegex(ValueError,'No FCEUX'):
                check_capture_meta(path)
            path.write_text('register_log_complete=yes\ncallback_errors=0\nmmc3_write_coverage=full_8000_ffff_even_odd\ncycle_trace_available=yes\n')
            self.assertEqual(check_capture_meta(path)['cycle_trace_available'],'yes')
            path.write_text('register_log_complete=yes\ncallback_errors=0\n'
                            'cycle_trace_available=yes\n')
            with self.assertRaisesRegex(ValueError,'MMC3 mirrored'):
                check_capture_meta(path)
            path.write_text('register_log_complete=yes\ncallback_errors=2\n'
                            'mmc3_write_coverage=full_8000_ffff_even_odd\n'
                            'cycle_trace_available=yes\n')
            with self.assertRaisesRegex(ValueError,'callback integrity'):
                check_capture_meta(path)


if __name__=='__main__':
    unittest.main()
