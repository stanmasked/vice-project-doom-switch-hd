"""Stage94 ROM-free timestamp bracketing regression tests."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_ppu_cpu_clock_bracketing import (
    analyze_verified, bracket, summarize_bracket,
)
import test_ppu_capture_session as fixtures
from verify_ppu_capture_session import SessionError


class ClockBracketUnitTests(unittest.TestCase):
    def test_without_anchors_is_unanchored(self):
        self.assertEqual(bracket(100, None, None), 'unanchored')
        self.assertEqual(bracket(None, None, None), 'unanchored')

    def test_interior_and_boundary_equalities_are_exclusive(self):
        self.assertEqual(bracket(20, 20, 100),
                         'at_previous_sample_clock')
        self.assertEqual(bracket(100, 20, 100),
                         'at_current_sample_clock')
        self.assertEqual(bracket(60, 20, 100),
                         'strictly_between_sample_clocks')

    def test_identical_snapshot_clocks_are_explicitly_ambiguous(self):
        self.assertEqual(bracket(100, 100, 100),
                         'indistinguishable_equal_sample_clocks')
        with self.assertRaisesRegex(ValueError, 'outside snapshot clock'):
            bracket(101, 100, 100)

    def test_outside_or_reversed_brackets_fail_closed(self):
        with self.assertRaises(ValueError):
            bracket(9, 10, 30)
        with self.assertRaises(ValueError):
            bracket(31, 10, 30)
        with self.assertRaises(ValueError):
            bracket(10, 30, 10)
        with self.assertRaisesRegex(ValueError, 'Missing event CPU cycle'):
            bracket(None, 20, 40)

    def test_selector_carried_without_output_of_raw_register_values(self):
        summary, selector = summarize_bracket(
            [(1, 0x8000, 5), (1, 0x8001, 0xFA),
             (1, 0x2005, 0x99)], [10, 11, 12],
            previous_clock=10, current_clock=12)
        self.assertEqual(selector, 5)
        self.assertEqual(summary['registered_callbacks'], 3)
        self.assertEqual(summary['cpu_timestamp_group_counts'][
            'at_previous_sample_clock'], 1)
        self.assertEqual(summary['cpu_timestamp_group_counts'][
            'strictly_between_sample_clocks'], 1)
        self.assertEqual(summary['cpu_timestamp_group_counts'][
            'at_current_sample_clock'], 1)
        self.assertEqual(summary['cpu_timestamp_group_family_counts'][
            'at_current_sample_clock']['scroll_address'], 1)
        self.assertNotIn('250', json.dumps(summary))

    def test_equal_adjacent_event_cycles_counted_not_order_proven(self):
        report, _selector = summarize_bracket(
            [(1, 0x8000, 0), (1, 0x2005, 10), (1, 0x2006, 20)],
            [10, 10, 12], previous_clock=10, current_clock=12)
        self.assertEqual(report['equal_adjacent_cpu_cycles_within_pair'], 1)
        self.assertFalse(report['ppu_raster_timing_known'])

    def test_disagreement_and_cycle_regression_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Event/cycle list mismatch'):
            summarize_bracket([(1, 0x8000, 0)], [])
        with self.assertRaisesRegex(ValueError, 'decreased'):
            summarize_bracket([(1, 0x8000, 0), (1, 0x8001, 1)], [12, 11])


class FullSessionBracketingTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.CaptureSessionTests('test_complete_session')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.f = fixture

    def test_unclocked_snapshot_samples_do_not_infer_raster(self):
        report = analyze_verified(self.f.manifest, require_cycle=True)
        self.assertFalse(report['verified_snapshot_clock_anchors'])
        pair = report['pairs'][0]
        self.assertEqual(pair['clock_evidence']['cpu_timestamp_group_counts'][
            'unanchored'], 1)
        self.assertIsNone(pair['snapshot_sample_timestamps_equal'])
        self.assertFalse(pair['ppu_visible_scanline_position_verified'])
        with self.assertRaisesRegex(ValueError, 'No verified registerafter'):
            analyze_verified(self.f.manifest, require_clock_anchors=True)

    def test_verified_sampled_snapshot_clocks_bracket_event(self):
        self.f.enable_callback_clock(first=20, second=120)
        report = analyze_verified(
            self.f.manifest, require_cycle=True, require_clock_anchors=True)
        self.assertTrue(report['verified_snapshot_clock_anchors'])
        pair = report['pairs'][0]
        self.assertEqual(pair['clock_evidence']['cpu_timestamp_group_counts'][
            'strictly_between_sample_clocks'], 1)
        self.assertEqual(pair['clock_evidence']['cpu_timestamp_group_family_counts'][
            'strictly_between_sample_clocks']['scroll_address'], 1)
        self.assertFalse(report['interpretation'][
            'clock_samples_are_ppu_vblank_or_scanline_boundaries'])
        self.assertFalse(pair['camera_displacement_inferred'])
        report_text = json.dumps(report)
        for disallowed in ('cpu_cycle_start', 'bank_register_value',
                           'scanline_number', 'original_rom_md5'):
            self.assertNotIn(disallowed, report_text)

    def test_event_equal_previous_callback_clock(self):
        self.f.enable_callback_clock(first=100, second=120)
        pair = analyze_verified(self.f.manifest)['pairs'][0]
        self.assertEqual(pair['clock_evidence']['cpu_timestamp_group_counts'][
            'at_previous_sample_clock'], 1)

    def test_event_equal_current_callback_clock(self):
        self.f.enable_callback_clock(first=20, second=100)
        pair = analyze_verified(self.f.manifest)['pairs'][0]
        self.assertEqual(pair['clock_evidence']['cpu_timestamp_group_counts'][
            'at_current_sample_clock'], 1)

    def test_equal_callback_clocks_do_not_infer_boundary(self):
        self.f.enable_callback_clock(first=100, second=100)
        pair = analyze_verified(self.f.manifest)['pairs'][0]
        self.assertTrue(pair['snapshot_sample_timestamps_equal'])
        self.assertEqual(pair['clock_evidence']['cpu_timestamp_group_counts'][
            'indistinguishable_equal_sample_clocks'], 1)
        self.assertFalse(pair['events_at_clock_boundary_are_raster_boundary_events'])

    def test_tampered_clock_is_rejected_before_analysis(self):
        self.f.enable_callback_clock(first=20, second=99)
        with self.assertRaisesRegex(SessionError, 'precedes committed event'):
            analyze_verified(self.f.manifest)

    def test_tampered_tsv_checksum_is_rejected_before_analysis(self):
        self.f.enable_callback_clock(first=20, second=120)
        self.f.cyclelog.write_text(self.f.cyclelog.read_text().replace(
            '3\t100\t200D\t22', '3\t101\t200D\t22'))
        with self.assertRaises(SessionError):
            analyze_verified(self.f.manifest)

    def test_without_cpu_log_never_promoted_to_timed_trace(self):
        self.f.props['cycle_trace_available'] = 'no'
        self.f.props['cycle_log_adler32'] = 'not_captured'
        for row in self.f.frames.values():
            row['cycle_trace_available'] = 'no'
            row['cycle_log_prefix_adler32'] = 'not_captured'
        self.f.finalize()
        report = analyze_verified(self.f.manifest)
        self.assertFalse(report['verified_cpu_cycle_log'])
        self.assertEqual(report['pairs'][0]['clock_evidence'][
            'cpu_timestamp_group_counts']['unanchored'], 1)
        with self.assertRaisesRegex(SessionError, 'CPU-cycle trace unavailable'):
            analyze_verified(self.f.manifest, require_cycle=True)


if __name__ == '__main__':
    unittest.main()
