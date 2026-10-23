"""ROM-free Stage347 regressions: manufactured values, no game pixels or ROM."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_private_stage347_scroll_discontinuity as stage


def fabricated(*,start_y:int=215,exception:bool=True):
    steps=[-2]*24
    if exception:steps[11]=-18
    y=[start_y]
    for step in steps:y.append((y[-1]+step)%256)
    rows=[{'frame':stage.FIRST+i,'first_y':v,'last_y':80}
          for i,v in enumerate(y)]
    return rows,[2]*24


class Stage347OriginalSourceFree(unittest.TestCase):
    def test_authenticated_discontinuity_counted_not_discarded(self):
        samples,shifts=fabricated()
        report=stage.compare(samples,shifts)
        self.assertEqual(report['first_scroll_inverse_motion_agree_pairs'],23)
        self.assertEqual(report['first_scroll_inverse_motion_disagree_pairs'],1)
        self.assertFalse(report['universal_register_pixel_displacement_law_supported'])
        self.assertFalse(report['camera_vehicle_speed_or_collision_proven'])

    def test_all_real_pixel_shifts_two(self):
        samples,shifts=fabricated()
        self.assertEqual(stage.compare(samples,shifts)['background_pixel_shift_two_pairs'],24)

    def test_wrap_keeps_exception_not_silently_resolved(self):
        samples,shifts=fabricated(start_y=20)
        self.assertEqual(stage.compare(samples,shifts)['register_minus_eighteen_image_plus_two_exceptions'],1)

    def test_no_exception_is_not_original_baseline(self):
        samples,shifts=fabricated(exception=False)
        with self.assertRaisesRegex(ValueError,'baseline'):
            stage.compare(samples,shifts)

    def test_second_exception_rejected(self):
        samples,shifts=fabricated()
        samples[15]['first_y']=(samples[15]['first_y']-16)%256
        with self.assertRaises(ValueError):
            stage.compare(samples,shifts)

    def test_unrecognized_register_discontinuity_rejected(self):
        samples,shifts=fabricated()
        samples[12]['first_y']=(samples[12]['first_y']+1)%256
        with self.assertRaisesRegex(ValueError,'unrecognized'):
            stage.compare(samples,shifts)

    def test_18_pixel_prediction_outside_masked_search_rejected(self):
        samples,shifts=fabricated()
        shifts[11]=18
        with self.assertRaisesRegex(ValueError,'outside measured mask'):
            stage.compare(samples,shifts)

    def test_ambiguous_negative_pixel_shift_not_claimed(self):
        samples,shifts=fabricated()
        shifts[9]=-2
        with self.assertRaisesRegex(ValueError,'unrecognized'):
            stage.compare(samples,shifts)

    def test_missing_one_original_frame_rejected(self):
        samples,shifts=fabricated()
        with self.assertRaisesRegex(ValueError,'complete'):
            stage.compare(samples[:-1],shifts)

    def test_missing_adjacent_pair_rejected(self):
        samples,shifts=fabricated()
        with self.assertRaisesRegex(ValueError,'complete'):
            stage.compare(samples,shifts[:-1])

    def test_duplicated_original_frame_rejected(self):
        samples,shifts=fabricated()
        samples[6]['frame']=samples[5]['frame']
        with self.assertRaisesRegex(ValueError,'not consecutive'):
            stage.compare(samples,shifts)

    def test_later_phase_change_rejected(self):
        samples,shifts=fabricated()
        samples[12]['last_y']=81
        with self.assertRaisesRegex(ValueError,'later'):
            stage.compare(samples,shifts)

    def test_more_than_four_pixel_shift_not_assumed(self):
        samples,shifts=fabricated()
        shifts[0]=5
        with self.assertRaisesRegex(ValueError,'outside'):
            stage.compare(samples,shifts)

if __name__=='__main__':unittest.main()
