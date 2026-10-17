"""Stage92 ROM-free synthetic evidence: screen stability is not camera motion."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_ppu_cross_snapshot_consistency import (
    TOTAL_CELLS, PIXELS, analyze_verified, compare_saved_screen_cells,
)
import test_ppu_capture_session as capture_fixtures
from verify_ppu_capture_session import SessionError


class SameCoordinateCellTests(unittest.TestCase):
    def test_all_pixels_identical_is_still_screen_space_only(self):
        ref = bytes([0x12]) * PIXELS
        counts = compare_saved_screen_cells(ref, ref)
        self.assertEqual(counts['fully_known_identical'], TOTAL_CELLS)
        self.assertEqual(counts['fully_known_changed'], 0)

    def test_one_changed_cell_and_one_unknown_cell(self):
        before = bytes([3]) * PIXELS
        after = bytearray(before)
        after[0] = 4
        after[8] = 254
        counts = compare_saved_screen_cells(before, after)
        self.assertEqual(counts['fully_known_changed'], 1)
        self.assertEqual(counts['partially_unknown'], 1)
        self.assertEqual(counts['fully_known_identical'], TOTAL_CELLS - 2)

    def test_unknown_wins_over_changed_within_same_cell(self):
        before = bytes([3]) * PIXELS
        after = bytearray(before)
        after[0] = 4
        after[1] = 254
        counts = compare_saved_screen_cells(before, after)
        self.assertEqual(counts['partially_unknown'], 1)
        self.assertEqual(counts['fully_known_changed'], 0)

    def test_invalid_length_and_palette_values_rejected(self):
        valid = bytes(PIXELS)
        with self.assertRaises(ValueError):
            compare_saved_screen_cells(valid, valid[:-1])
        with self.assertRaises(ValueError):
            compare_saved_screen_cells(bytes([255]) * PIXELS, valid)


class VerifiedSessionPairTests(unittest.TestCase):
    def setUp(self):
        fixture = capture_fixtures.CaptureSessionTests('test_complete_session')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.f = fixture

    def two_references(self):
        first = self.f.stage89_reference()
        second = self.f.root / 'frame_000003'
        self.f.frames[3]['screen_reference'] = 'yes'
        for suffix, key in (
            ('.screen.rgb.bin', 'screen_rgb_adler32'),
            ('.screen.pal.bin', 'screen_pal_adler32'),
        ):
            path = Path(str(second) + suffix)
            path.write_bytes(Path(str(first) + suffix).read_bytes())
            self.f.frames[3][key] = capture_fixtures.checksum_file(path)
        self.f.finalize()
        return second

    def test_absent_reference_pair_retains_transition_memory_evidence(self):
        result = analyze_verified(self.f.manifest, require_cycle=True)
        self.assertEqual(result['screen_reference_pairs_compared'], 0)
        self.assertEqual(result['snapshot_pairs'], 1)
        pair = result['pairs'][0]
        self.assertEqual(pair['screen_reference_pair_status'], 'both_missing')
        self.assertEqual(pair['screen_cell_counts'][
            'unassessed_missing_reference'], TOTAL_CELLS)
        self.assertEqual(pair['frame_label_distance'], 2)
        self.assertEqual(pair['unobserved_frame_labels_between'], 1)
        self.assertEqual(pair['intervening_verified_cpu_event_window'][
            'ppuscroll_writes'], 1)
        self.assertFalse(pair['camera_offset_inferred'])
        with self.assertRaisesRegex(ValueError, 'No consecutive saved snapshot'):
            analyze_verified(self.f.manifest, require_screen_pair=True)

    def test_only_one_saved_screen_is_not_a_comparable_pair(self):
        self.f.stage89_reference()
        report = analyze_verified(self.f.manifest)
        self.assertEqual(report['screen_reference_pairs_compared'], 0)
        self.assertEqual(report['pairs'][0]['screen_reference_pair_status'],
                         'later_missing')
        self.assertEqual(report['pairs'][0]['evaluated_screen_cells'], 0)

    def test_identical_screen_planes_do_not_prove_level_geometry(self):
        self.two_references()
        report = analyze_verified(self.f.manifest, require_screen_pair=True)
        pair = report['pairs'][0]
        self.assertEqual(report['screen_reference_pairs_compared'], 1)
        self.assertEqual(pair['screen_cell_counts'][
            'fully_known_identical'], TOTAL_CELLS)
        self.assertEqual(pair['level_geometry_reconstruction_ready_cells'], 0)
        self.assertFalse(pair['background_or_world_tile_stability_proven'])
        self.assertFalse(pair['stage91_static_candidate_counts'][
            'spatial_correspondence_between_candidates_proven'])
        self.assertFalse(report['interpretation']['camera_motion_reconstructed'])
        self.assertFalse(report['interpretation']['first_level_geometry_proven'])
        exported = json.dumps(report)
        for forbidden in ('raw_ppu_bytes', 'world_tile_map',
                          'screen_pixel_values', 'original_rom_md5'):
            self.assertNotIn(forbidden, exported)

    def test_verified_second_reference_change_and_unknown(self):
        second = self.two_references()
        path = Path(str(second) + '.screen.pal.bin')
        payload = bytearray(path.read_bytes())
        payload[0] ^= 1
        payload[8] = 254
        path.write_bytes(payload)
        self.f.frames[3]['screen_pal_adler32'] = capture_fixtures.checksum_file(path)
        self.f.finalize()
        pair = analyze_verified(self.f.manifest)['pairs'][0]
        self.assertEqual(pair['screen_cell_counts']['fully_known_changed'], 1)
        self.assertEqual(pair['screen_cell_counts']['partially_unknown'], 1)
        self.assertEqual(pair['screen_cell_counts'][
            'fully_known_identical'], TOTAL_CELLS - 2)

    def test_verify_full_session_before_comparison(self):
        second = self.two_references()
        path = Path(str(second) + '.screen.pal.bin')
        payload = bytearray(path.read_bytes())
        payload[0] ^= 1
        path.write_bytes(payload)
        with self.assertRaisesRegex(SessionError, 'checksum mismatch'):
            analyze_verified(self.f.manifest)

    def test_missing_cycle_log_never_implies_raster_timing(self):
        self.f.props['cycle_trace_available'] = 'no'
        self.f.props['cycle_log_adler32'] = 'not_captured'
        for row in self.f.frames.values():
            row['cycle_trace_available'] = 'no'
            row['cycle_log_prefix_adler32'] = 'not_captured'
        self.f.finalize()
        result = analyze_verified(self.f.manifest)
        self.assertFalse(result['cpu_cycle_trace_verified'])
        self.assertFalse(result['interpretation']['cpu_events_aligned_to_ppu_raster'])
        with self.assertRaisesRegex(SessionError, 'CPU-cycle trace unavailable'):
            analyze_verified(self.f.manifest, require_cycle=True)


if __name__ == '__main__':
    unittest.main()
