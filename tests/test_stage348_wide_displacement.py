"""Stage348 fabricated-only wide pixel-offset tests; no original game data."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_private_stage348_wide_displacement as stage
import audit_private_stage344_motion as motion


def artificial(shift:int=0,*,period:int=256,flat:bool=False)->bytes:
    rows=[]
    for y in range(motion.HEIGHT):
        t=(y-shift)%period
        rgb=( (81,81,81) if flat else
              ((t*7)%256,(t*11)%256,(t*13)%256) )
        rows.append(bytes(rgb)*motion.WIDTH)
    return b''.join(rows)


class Stage348WideSourceFree(unittest.TestCase):
    def test_unique_two_pixel_shift_in_all_four_regions(self):
        a,b=artificial(),artificial(2)
        for name,band in motion.BANDS.items():
            with self.subTest(name=name):
                result=stage.wider_probe(a,b,band,name=name)
                self.assertEqual(result['best_dy'],2)
                self.assertEqual(result['best_exact_match_fraction'],1.0)
                self.assertGreater(result['wrong_18_shift_mismatch_fraction'],.2)

    def test_wrong_18_shift_has_nonzero_rgb_error(self):
        a,b=artificial(),artificial(2)
        q=stage.wider_probe(a,b,motion.BANDS['right_environment'],
                            name='right_environment')
        self.assertGreater(q['wrong_18_shift_mismatch_fraction'],q['runner_up_gap'])

    def test_real_18_pixel_shift_can_be_seen_when_it_is_real(self):
        a,b=artificial(),artificial(18)
        q=stage.wider_probe(a,b,motion.BANDS['left_environment'],
                            name='left_environment')
        self.assertEqual(q['best_dy'],18)
        self.assertEqual(q['best_exact_match_fraction'],1.0)

    def test_sixteen_pixel_periodic_alias_is_rejected(self):
        a,b=artificial(period=16),artificial(2,period=16)
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            stage.wider_probe(a,b,motion.BANDS['left_environment'],
                              name='left_environment')

    def test_flat_texture_is_not_movement_evidence(self):
        a,b=artificial(flat=True),artificial(2,flat=True)
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            stage.wider_probe(a,b,motion.BANDS['left_marking'],
                              name='left_marking')

    def test_truncated_rgb_input_rejected(self):
        with self.assertRaisesRegex(ValueError,'shape'):
            stage.mismatch(artificial()[:-1],artificial(2),
                           motion.BANDS['left_environment'],2)

    def test_unbounded_shift_rejected(self):
        with self.assertRaisesRegex(ValueError,'unsupported'):
            stage.mismatch(artificial(),artificial(2),
                           motion.BANDS['left_environment'],25)

    def test_invalid_region_rejected(self):
        with self.assertRaisesRegex(ValueError,'unsupported'):
            stage.mismatch(artificial(),artificial(2),
                           (260,270,20,175),2)

    def test_wide_scan_49_offsets_including_18(self):
        self.assertEqual(len(stage.SHIFTS),49)
        self.assertIn(18,stage.SHIFTS)
        self.assertEqual((min(stage.SHIFTS),max(stage.SHIFTS)),(-24,24))

if __name__=='__main__':unittest.main()
