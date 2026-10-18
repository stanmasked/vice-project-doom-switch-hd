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

    def test_mirrored_ppu_status_and_scroll_cycle_events(self):
        events=[(4,500,0x3FFA,0,'R'),(4,510,0x200D,0x17,'W'),
                (4,520,0x3FFD,0x27,'W'),(4,530,0x2008,0x80,'W')]
        result=summarize(events)
        self.assertEqual(result['frames'][0]['ppu_status_reads'],1)
        self.assertEqual(result['frames'][0]['scroll_write_count'],2)
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'mirror.tsv'
            p.write_text(HEADER+'\n4\t500\t3FFA\t00\tR\n'
                              '4\t510\t200D\t17\tW\n',encoding='utf8')
            self.assertEqual(len(list(parse_events(p))),2)
            p.write_text(HEADER+'\n4\t500\t3FFB\t00\tR\n')
            with self.assertRaisesRegex(ValueError,'Unexpected read'):
                list(parse_events(p))
            p.write_text(HEADER+'\n4\t500\t3FFA\tAA\tR\n')
            with self.assertRaisesRegex(ValueError,'Unexpected read'):
                list(parse_events(p))

    def test_counter_reset_creates_new_epoch(self):
        r=summarize([(0,490,0x8000,0,'W'),
                     (0,510,0x8001,7,'W'),
                     (1,5,0x8000,1,'W'),
                     (1,10,0x8001,10,'W')])
        self.assertEqual(r['cpu_clock_resets_or_discontinuities'],1)
        self.assertEqual(r['chr_events'][1]['counter_epoch'],1)
        self.assertFalse(r['out_of_order_frame_numbers'])
        self.assertEqual(r['frames'][1]['chr_events'][0]['cycles_since_first_logged_event_this_frame'],5)

    def test_same_frame_decrease_is_possible_discontinuity_not_proven_reset(self):
        report=summarize([(4,200,0x8000,0,'W'),
                          (4,150,0x8001,5,'W'),
                          (4,170,0x3FFA,0,'R')])
        self.assertEqual(report['cpu_clock_decreases_same_frame'],1)
        self.assertEqual(report['cpu_clock_decreases_between_frames'],0)
        self.assertEqual(report['cpu_clock_resets_or_discontinuities'],1)
        self.assertEqual(report['frames'][0]['cpu_clock_regressions_within_frame'],1)
        self.assertFalse(report['counter_reset_proven'])

    def test_cross_frame_decrease_and_equal_timestamps_diagnostic(self):
        report=summarize([(4,200,0x8000,0,'W'),
                          (4,200,0x8001,5,'W'),
                          (5,90,0x8000,0,'W'),
                          (5,90,0x8001,7,'W')])
        self.assertEqual(report['cpu_clock_decreases_between_frames'],1)
        self.assertEqual(report['cpu_clock_equal_adjacent'],2)
        self.assertEqual(report['frames'][0]['cpu_clock_equal_adjacent'],1)
        self.assertEqual(report['frames'][1]['cpu_clock_equal_adjacent'],1)
        self.assertEqual(report['frames'][1]['cpu_clock_regressions_from_previous_frame'],1)
        self.assertFalse(report['counter_reset_proven'])

    def test_stable_clock_does_not_imply_frame_start_timing(self):
        report=summarize([(12,900,0x8000,0,'W'),
                          (13,29800,0x8001,6,'W')])
        self.assertEqual(report['cpu_clock_decreases_same_frame'],0)
        self.assertEqual(report['cpu_clock_decreases_between_frames'],0)
        self.assertEqual(report['cpu_clock_equal_adjacent'],0)
        self.assertFalse(report['counter_reset_proven'])


    def test_adjacent_frame_label_boundary_is_between_logged_events(self):
        events=[(10,100,0x8000,0,'W'),(10,105,0x8001,3,'W'),
                (11,150,0x200D,10,'W'),(11,160,0x200D,11,'W')]
        r=summarize(events)
        self.assertEqual(r['frame_transition_count'],1)
        b=r['frame_boundary_observations'][0]
        self.assertEqual(b['previous_event_frame'],10)
        self.assertEqual(b['current_event_frame'],11)
        self.assertEqual(b['frame_label_delta'],1)
        self.assertEqual(b['last_logged_cycle_previous_frame'],105)
        self.assertEqual(b['first_logged_cycle_current_frame'],150)
        self.assertEqual(b['cycles_between_adjacent_logged_events'],45)
        self.assertEqual(b['frame_labels_skipped_without_events'],0)
        self.assertIsNone(b['physical_frame_duration_cycles'])
        self.assertIsNone(b['physical_frame_start_cycle'])
        self.assertFalse(r['frame_start_cycle_proven'])
        self.assertFalse(r['ppu_scanline_position_proven'])

    def test_gap_in_event_frame_labels_is_not_missing_emulator_frames(self):
        events=[(3,400,0x8000,1,'W'),(7,650,0x8001,2,'W')]
        r=summarize(events)
        b=r['frame_boundary_observations'][0]
        self.assertEqual(b['frame_label_delta'],4)
        self.assertEqual(b['frame_labels_skipped_without_events'],3)
        self.assertEqual(r['frame_labels_skipped_without_events'],3)
        self.assertEqual(b['cycles_between_adjacent_logged_events'],250)
        self.assertIsNone(b['physical_frame_duration_cycles'])

    def test_equal_cycles_across_frame_labels_produce_zero_event_gap(self):
        r=summarize([(3,400,0x8000,1,'W'),(4,400,0x8001,2,'W')])
        b=r['frame_boundary_observations'][0]
        self.assertEqual(b['cycles_between_adjacent_logged_events'],0)
        self.assertFalse(b['cpu_counter_discontinuity'])

    def test_cycle_regression_does_not_create_negative_boundary_interval(self):
        r=summarize([(3,400,0x8000,1,'W'),(4,10,0x8001,2,'W')])
        b=r['frame_boundary_observations'][0]
        self.assertIsNone(b['cycles_between_adjacent_logged_events'])
        self.assertTrue(b['cpu_counter_discontinuity'])
        self.assertEqual(r['cpu_clock_decreases_between_frames'],1)

    def test_out_of_order_event_frame_labels_have_no_valid_interval(self):
        r=summarize([(7,400,0x8000,1,'W'),(6,420,0x8001,2,'W')])
        b=r['frame_boundary_observations'][0]
        self.assertIsNone(b['cycles_between_adjacent_logged_events'])
        self.assertEqual(b['frame_label_delta'],-1)
        self.assertTrue(r['out_of_order_frame_numbers'])

    def test_single_frame_and_empty_timeline_have_no_boundary(self):
        for events in ([],[(2,100,0x8000,0,'W')]):
            report=summarize(events)
            self.assertEqual(report['frame_boundary_observations'],[])
            self.assertEqual(report['frame_transition_count'],0)

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
            path.write_text('register_log_complete=yes\ncallback_errors=0\nmmc3_write_coverage=full_8000_ffff_even_odd\nppu_register_write_coverage=full_2000_3fff_mod8\nppu_status_read_coverage=full_2000_3fff_mod8\ncycle_trace_available=yes\n')
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
            path.write_text('register_log_complete=yes\ncallback_errors=0\n'
                            'mmc3_write_coverage=full_8000_ffff_even_odd\n'
                            'cycle_trace_available=yes\n')
            with self.assertRaisesRegex(ValueError,'PPU register mirror'):
                check_capture_meta(path)


if __name__=='__main__':
    unittest.main()
