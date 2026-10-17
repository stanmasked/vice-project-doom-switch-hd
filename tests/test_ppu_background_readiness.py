"""Stage91 ROM-free, private-capture-safe static background readiness tests."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_ppu_background_readiness import (
    CLASSES, PIXELS, TOTAL_CELLS, analyze_verified, classify_cells,
)
import test_ppu_capture_session as capture_fixtures
from verify_ppu_capture_session import SessionError


class CellClassificationTests(unittest.TestCase):
    def test_full_consensus_still_only_candidate(self):
        observed = bytes([7]) * PIXELS
        self.assertEqual(classify_cells(observed, [observed, observed])[
            'unanimous_static_match'], TOTAL_CELLS)

    def test_one_cell_depends_on_static_hypothesis(self):
        observed = bytes([7]) * PIXELS
        altered = bytearray(observed)
        altered[0] = 8
        report = classify_cells(observed, [observed, altered])
        self.assertEqual(report['hypothesis_dependent_static_match'], 1)
        self.assertEqual(report['unanimous_static_match'], TOTAL_CELLS - 1)

    def test_no_exact_candidate_and_unknown_pixel_are_distinct(self):
        reference = bytearray([7] * PIXELS)
        candidate = bytes([8]) * PIXELS
        reference[0] = 254
        result = classify_cells(reference, [candidate])
        self.assertEqual(result['incomplete_reference'], 1)
        self.assertEqual(result['no_exact_static_match'], TOTAL_CELLS - 1)
        self.assertEqual(sum(result.values()), TOTAL_CELLS)

    def test_bad_input_rejected(self):
        with self.assertRaises(ValueError):
            classify_cells(bytes(PIXELS), [])
        with self.assertRaises(ValueError):
            classify_cells(bytes(PIXELS - 1), [bytes(PIXELS)])
        with self.assertRaises(ValueError):
            classify_cells(bytes(PIXELS), [bytes(PIXELS - 1)])
        with self.assertRaises(ValueError):
            classify_cells(bytes([255]) * PIXELS, [bytes(PIXELS)])


class VerifiedReadinessTests(unittest.TestCase):
    def setUp(self):
        # Reuse the existing real session-integrity fixture, not a fake proof.
        fixture = capture_fixtures.CaptureSessionTests('test_complete_session')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.capture = fixture

    def test_no_reference_is_not_interpreted_as_blank_background(self):
        report = analyze_verified(self.capture.manifest, require_cycle=True)
        self.assertEqual(report['screen_reference_frames'], 0)
        self.assertEqual(report['aggregate_cell_counts'][
            'unassessed_no_reference'], TOTAL_CELLS * 2)
        self.assertEqual(report['reconstruction_ready_cells'], 0)
        self.assertFalse(report['evidence_rules'][
            'original_game_identity_authenticated'])
        with self.assertRaisesRegex(ValueError, 'No verified screen references'):
            analyze_verified(self.capture.manifest, require_screen=True)

    def test_verified_static_match_cannot_be_promoted_to_level_geometry(self):
        self.capture.stage89_reference()
        report = analyze_verified(self.capture.manifest, require_screen=True)
        self.assertEqual(report['screen_reference_frames'], 1)
        self.assertEqual(report['total_screen_cells_accounted_for'],
                         2 * TOTAL_CELLS)
        first, second = report['frames']
        self.assertEqual(first['static_hypotheses_tested'], 4)
        self.assertGreater(first['static_exact_match_candidate_cells'], 0)
        self.assertEqual(first['reconstruction_ready_cells'], 0)
        self.assertFalse(first['raster_visible_background_proven'])
        self.assertFalse(first['world_level_coordinates_proven'])
        self.assertEqual(second['screen_cell_counts'][
            'unassessed_no_reference'], TOTAL_CELLS)
        self.assertEqual(first['event_window']['observed_cpu_register_events'], 2)
        self.assertFalse(first['event_window']['scanline_chr_mapping_proven'])
        payload = json.dumps(report)
        for forbidden in ('raw_ppu', 'palette_index_values', 'rom_md5',
                          'world_tile_coordinates'):
            self.assertNotIn(forbidden, payload)

    def test_unknown_reference_pixel_disqualifies_cell(self):
        self.capture.stage89_reference(missing=1)
        report = analyze_verified(self.capture.manifest)
        self.assertEqual(report['frames'][0]['screen_cell_counts'][
            'incomplete_reference'], 1)
        self.assertEqual(sum(report['frames'][0]['screen_cell_counts'].values()),
                         TOTAL_CELLS)

    def test_changed_reference_without_checksum_update_rejected(self):
        prefix = self.capture.stage89_reference()
        path = Path(str(prefix) + '.screen.pal.bin')
        data = bytearray(path.read_bytes())
        data[12] ^= 1
        path.write_bytes(data)
        with self.assertRaises(SessionError):
            analyze_verified(self.capture.manifest)

    def test_unclocked_session_remains_explicitly_unclocked(self):
        f = self.capture
        f.props['cycle_trace_available'] = 'no'
        f.props['cycle_log_adler32'] = 'not_captured'
        for row in f.frames.values():
            row['cycle_trace_available'] = 'no'
            row['cycle_log_prefix_adler32'] = 'not_captured'
        f.finalize()
        self.assertFalse(analyze_verified(f.manifest)['cpu_cycle_trace_verified'])
        with self.assertRaises(SessionError):
            analyze_verified(f.manifest, require_cycle=True)


if __name__ == '__main__':
    unittest.main()
