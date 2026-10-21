"""ROM-free synthetic tests: never load the owner's original pixel data."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_private_ppumask_ab import audit, PIXELS, PPM_HEADER


def make_fixture(root, target=600, change_at=None, y=202, x=100,
                 invalid_witness=None, palette_mutation=False):
    original = root / 'original'
    probe = root / 'probe'
    original.mkdir()
    probe.mkdir()
    for path, mode in ((original, 'original'), (probe, 'probe_bg_off')):
        fields = {'format': 'private_ppumask_one_write_ab_v1', 'mode': mode,
                  'frame': str(target), 'first_observed_frame': '1',
                  'last_observed_frame': str(target + 2), 'frame_gaps': '0',
                  'target_instruction_hits': '1',
                  'source_rom_unchanged': 'yes', 'fm2_readonly': 'yes'}
        fields['accumulator_restored_before_rts'] = (
            'yes' if path == probe else 'not_needed')
        if invalid_witness and path == probe:
            fields[invalid_witness] = 'no' if fields[invalid_witness] == 'yes' else '-1'
        (path / 'COMPLETE.txt').write_text(''.join(f'{k}={v}\n'
                      for k, v in fields.items()), 'ascii')
        for frame in range(target - 1, target + 3):
            rgb = bytearray(b'\x24' * PIXELS * 3)
            pal = bytearray(b'\x09' * PIXELS)
            if mode == 'probe_bg_off' and frame == change_at:
                rgb[(y * 256 + x) * 3] = 0x88
                if palette_mutation: pal[y * 256 + x] = 0x1f
            (path / f'frame_{frame:06d}.ppm').write_bytes(PPM_HEADER + rgb)
            (path / f'frame_{frame:06d}.pal.bin').write_bytes(pal)
    return original, probe


class RasterABTests(unittest.TestCase):
    def test_one_controlled_lower_screen_change(self):
        with tempfile.TemporaryDirectory() as d:
            original, probe = make_fixture(Path(d), change_at=601, palette_mutation=True)
            report = audit(original, probe, target_frame=600)
            self.assertEqual(report['changed_capture_frames'], [601])
            self.assertEqual(report['rgb_affected_row_min'], 202)
            self.assertEqual(report['rgb_affected_row_max'], 202)
            self.assertEqual(report['pixel_differences'][2]['rgb_changed']['pixels'], 1)
            self.assertEqual(report['pixel_differences'][2]['palette_changed']['pixels'], 1)
            self.assertTrue(report['pre_intervention_images_match'])
            self.assertFalse(report['exact_ppu_scanline_of_cpu_write_proven'])

    def test_strict_accumulator_restore_witness_is_verified(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_fixture(Path(d), change_at=601)
            report = audit(a, b, target_frame=600)
            self.assertTrue(report['diagnostic_accumulator_restored_before_rts_verified'])
            self.assertTrue(report['baseline_explicit_accumulator_witness'])

    def test_reject_false_accumulator_restoration_claim(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_fixture(Path(d),
                                invalid_witness='accumulator_restored_before_rts')
            with self.assertRaisesRegex(ValueError, 'restore witness'):
                audit(a, b, target_frame=600)

    def test_legacy_capture_does_not_claim_cpu_restore(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_fixture(Path(d), change_at=601)
            for root in (a, b):
                marker = root / 'COMPLETE.txt'
                data = marker.read_text('ascii')
                marker.write_text(''.join(line for line in data.splitlines(True)
                    if not line.startswith('accumulator_restored_before_rts=')))
            result = audit(a, b, target_frame=600)
            self.assertFalse(result['diagnostic_accumulator_restored_before_rts_verified'])

    def test_no_effect_must_not_be_called_proof(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_fixture(Path(d))
            report = audit(a, b, target_frame=600)
            self.assertEqual(report['changed_capture_frames'], [])
            self.assertIsNone(report['first_changed_capture_frame'])
            self.assertIsNone(report['rgb_affected_row_min'])

    def test_refuse_pre_intervention_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_fixture(Path(d), change_at=599)
            with self.assertRaisesRegex(ValueError, 'before'):
                audit(a, b, target_frame=600)

    def test_reject_wrong_mode(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_fixture(Path(d))
            marker = b / 'COMPLETE.txt'
            marker.write_text(marker.read_text('ascii').replace('probe_bg_off', 'original'))
            with self.assertRaisesRegex(ValueError, 'identity'):
                audit(a, b, target_frame=600)

    def test_reject_unverified_readonly_movie(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_fixture(Path(d), invalid_witness='fm2_readonly')
            with self.assertRaisesRegex(ValueError, 'identity'):
                audit(a, b, target_frame=600)

    def test_reject_missing_ppm(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_fixture(Path(d))
            (b / 'frame_000600.ppm').unlink()
            with self.assertRaisesRegex(ValueError, 'missing'):
                audit(a, b, target_frame=600)

    def test_reject_different_image_dimensions(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_fixture(Path(d))
            p = b / 'frame_000601.ppm'
            p.write_bytes(p.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, 'P6'):
                audit(a, b, target_frame=600)

    def test_reject_shared_capture_directory(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_fixture(Path(d))
            with self.assertRaisesRegex(ValueError, 'same directory'):
                audit(a, a, target_frame=600)

    def test_reject_symlinked_private_capture(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = make_fixture(Path(d))
            link = Path(d) / 'alias'
            try: link.symlink_to(b, target_is_directory=True)
            except OSError: self.skipTest('symlink not supported')
            with self.assertRaisesRegex(ValueError, 'symlinked'):
                audit(a, link, target_frame=600)


if __name__ == '__main__':
    unittest.main()
