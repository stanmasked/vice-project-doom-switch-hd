"""Stage93 synthetic CPU callback order / screen evidence tests, ROM-free."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_ppu_temporal_evidence import (
    analyze_verified, event_family, screen_activity_relation,
    summarize_callback_window,
)
import test_ppu_capture_session as capture_fixtures
from verify_ppu_capture_session import SessionError


class CallbackSignatureTests(unittest.TestCase):
    def test_mirrored_scroll_status_and_chr_selector(self):
        events = [
            (1, 0x8002, 0x80), (1, 0x9FFF, 0x10),
            (1, 0x3FFD, 0x05), (1, 0x3FFA, 0),
            (1, 0x2006, 0x20),
        ]
        summary, selector = summarize_callback_window(events)
        self.assertEqual(selector, 0)
        self.assertEqual(summary['counts_by_family']['chr_context'], 2)
        self.assertEqual(summary['counts_by_family']['scroll_address'], 2)
        self.assertEqual(summary['counts_by_family']['status_latch'], 1)
        self.assertEqual(summary['collapsed_background_family_transitions'], 1)
        self.assertEqual(summary['ordered_family_signature'],
                         'multiple_families_without_return')

    def test_unknown_selector_conservatively_retained(self):
        summary, selector = summarize_callback_window([(1, 0x8001, 9)])
        self.assertIsNone(selector)
        self.assertEqual(summary['counts_by_family']['chr_context'], 1)

    def test_prg_register_data_is_not_chr_data(self):
        summary, selector = summarize_callback_window(
            [(1, 0x8000, 6), (1, 0x8001, 15)])
        self.assertEqual(selector, 6)
        self.assertEqual(summary['counts_by_family']['other'], 1)
        self.assertEqual(summary['counts_by_family']['chr_context'], 1)

    def test_interleaved_and_ordered_signatures(self):
        mixed, _ = summarize_callback_window([
            (2, 0x8000, 0), (2, 0x2005, 1), (3, 0x8001, 2)])
        self.assertEqual(mixed['ordered_family_signature'],
                         'interleaved_callback_families')
        self.assertEqual(mixed['collapsed_background_family_transitions'], 2)

    def test_ppu_video_memory_mask_and_mirroring_categories(self):
        summary, _ = summarize_callback_window([
            (1, 0x3FFF, 5), (1, 0x2001, 0x1e),
            (1, 0xA000, 1), (1, 0xC000, 4)])
        self.assertEqual(summary['counts_by_family']['ppu_data'], 1)
        self.assertEqual(summary['counts_by_family']['display_control'], 2)
        self.assertEqual(summary['counts_by_family']['other'], 1)

    def test_selector_carries_between_intervals_without_exporting_value(self):
        _first, selector = summarize_callback_window([(1, 0x8000, 5)])
        second, selector = summarize_callback_window(
            [(2, 0x8001, 1)], starting_selector=selector)
        self.assertEqual(second['counts_by_family']['chr_context'], 1)
        self.assertEqual(second['counts_by_family']['other'], 0)
        self.assertEqual(selector, 5)

    def test_unknown_and_same_frame_label_not_raster_proof(self):
        s, _ = summarize_callback_window(
            [(1, 0x2005, 12), (2, 0x2006, 32)],
            previous_snapshot_frame=1, ending_snapshot_frame=2)
        self.assertEqual(s['events_labeled_at_or_before_previous_snapshot'], 1)
        self.assertEqual(s['distinct_registered_callback_frame_labels'], 2)
        self.assertFalse(s['ppu_visible_order_known'])
        with self.assertRaises(ValueError):
            summarize_callback_window(
                [(3, 0x2005, 12)], ending_snapshot_frame=2)
        with self.assertRaises(ValueError):
            summarize_callback_window([], starting_selector=8)

    def test_relation_has_no_causal_claim(self):
        p = {'screen_reference_pair_status': 'both_verified',
             'screen_cell_counts': {'fully_known_identical': 959,
                                    'fully_known_changed': 1}}
        c, _ = summarize_callback_window([(2, 0x2005, 6)])
        self.assertEqual(screen_activity_relation(p, c),
                         'screen_change_and_registered_activity_cooccur')
        none, _ = summarize_callback_window([])
        self.assertEqual(screen_activity_relation(p, none),
                         'screen_change_without_selected_registered_activity')
        p['screen_reference_pair_status'] = 'later_missing'
        self.assertEqual(screen_activity_relation(p, c),
                         'screen_reference_pair_unavailable')


class VerifiedTemporalReportTests(unittest.TestCase):
    def setUp(self):
        fixture = capture_fixtures.CaptureSessionTests('test_complete_session')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.f = fixture

    def add_pair(self):
        first = self.f.stage89_reference()
        second = self.f.root / 'frame_000003'
        self.f.frames[3]['screen_reference'] = 'yes'
        for suffix, key in (
            ('.screen.rgb.bin', 'screen_rgb_adler32'),
            ('.screen.pal.bin', 'screen_pal_adler32')):
            path = Path(str(second) + suffix)
            path.write_bytes(Path(str(first) + suffix).read_bytes())
            self.f.frames[3][key] = capture_fixtures.checksum_file(path)
        self.f.finalize()
        return second

    def test_baseline_window_from_verified_session(self):
        report = analyze_verified(self.f.manifest, require_cycle=True)
        self.assertEqual(report['snapshot_pairs'], 1)
        p = report['pairs'][0]
        self.assertEqual(p['from_snapshot_frame'], 1)
        self.assertEqual(p['to_snapshot_frame'], 3)
        self.assertEqual(p['intervening_frames_without_saved_screen_snapshot'], 1)
        self.assertEqual(p['callback_window']['registered_callbacks'], 1)
        self.assertEqual(p['callback_window']['counts_by_family']['scroll_address'], 1)
        self.assertEqual(p['screen_and_callback_relation'],
                         'screen_reference_pair_unavailable')
        self.assertTrue(p['incomplete_scroll_pair_at_checkpoint'])
        self.assertFalse(p['camera_displacement_inferred'])

    def test_saved_images_identical_with_scroll_still_not_camera(self):
        self.add_pair()
        report = analyze_verified(self.f.manifest, require_screen_pair=True)
        p = report['pairs'][0]
        self.assertEqual(p['known_changed_screen_cells'], 0)
        self.assertGreater(p['known_identical_screen_cells'], 0)
        self.assertEqual(p['screen_and_callback_relation'],
                         'no_known_screen_change_despite_registered_activity')
        self.assertEqual(p['level_geometry_reconstruction_ready_cells'], 0)
        self.assertFalse(report['interpretation']['display_changes_causally_attributed'])
        out = json.dumps(report)
        for item in ('original_rom_md5', 'raw_ppu_bytes',
                     'bank_register_values', 'world_tile_coordinates'):
            self.assertNotIn(item, out)

    def test_changed_screen_cooccurrence_is_not_attribution(self):
        second = self.add_pair()
        path = Path(str(second) + '.screen.pal.bin')
        data = bytearray(path.read_bytes())
        data[10] ^= 1
        path.write_bytes(data)
        self.f.frames[3]['screen_pal_adler32'] = capture_fixtures.checksum_file(path)
        self.f.finalize()
        p = analyze_verified(self.f.manifest)['pairs'][0]
        self.assertEqual(p['known_changed_screen_cells'], 1)
        self.assertEqual(p['screen_and_callback_relation'],
                         'screen_change_and_registered_activity_cooccur')
        self.assertFalse(p['background_or_sprite_causality_proven'])

    def test_manifest_or_event_tampering_rejected(self):
        self.f.log.write_text(self.f.log.read_text().replace('3\t200D\t22',
                                                           '3\t200D\t23'))
        with self.assertRaises(SessionError):
            analyze_verified(self.f.manifest)

    def test_no_cycles_never_proves_scanlines(self):
        self.f.props['cycle_trace_available'] = 'no'
        self.f.props['cycle_log_adler32'] = 'not_captured'
        for row in self.f.frames.values():
            row['cycle_trace_available'] = 'no'
            row['cycle_log_prefix_adler32'] = 'not_captured'
        self.f.finalize()
        report = analyze_verified(self.f.manifest)
        self.assertFalse(report['verified_cpu_cycle_trace_available'])
        self.assertFalse(report['interpretation']['cpu_cycles_are_ppu_scanlines'])
        with self.assertRaisesRegex(SessionError, 'CPU-cycle trace unavailable'):
            analyze_verified(self.f.manifest, require_cycle=True)

    def test_no_verified_pair_with_require_screen_pair_rejected(self):
        with self.assertRaisesRegex(ValueError, 'No consecutive saved snapshot'):
            analyze_verified(self.f.manifest, require_screen_pair=True)


if __name__ == '__main__':
    unittest.main()
