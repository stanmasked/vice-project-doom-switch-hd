"""Source-free Stage346 image/register regression tests (only manufactured values)."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_private_stage346_original_rgb_scroll as audit


def fake(steps:list[int])->tuple[list[dict],list[int]]:
    assert len(steps)==24
    values=[224]
    for x in steps:values.append((values[-1]-x)%256)
    records=[{'frame':audit.FIRST+i,'first_y':v,'last_y':70}
             for i,v in enumerate(values)]
    return records,steps


class Stage346OriginalPixelsSourceFree(unittest.TestCase):
    def test_expected_new_source_visual_evidence_pattern(self):
        samples,shifts=fake([1]*18+[2]*6)
        report=audit.join(samples,shifts)
        self.assertEqual(report['observed_image_shift_1_pairs'],18)
        self.assertEqual(report['observed_image_shift_2_pairs'],6)
        self.assertEqual(report['pixel_and_inverse_first_scroll_pairs_matched'],24)
        self.assertFalse(report['camera_vehicle_speed_collision_proven'])

    def test_two_pixel_shift_not_always_one(self):
        samples,shifts=fake([2]*24)
        self.assertEqual(audit.join(samples,shifts)['observed_image_shift_2_pairs'],24)

    def test_zero_motion_and_stationary_y(self):
        samples,shifts=fake([0]*24)
        self.assertEqual(audit.join(samples,shifts)['observed_image_shift_0_pairs'],24)

    def test_eight_bit_wrap_is_signed(self):
        samples,shifts=fake([2]*24)
        self.assertEqual(audit.join(samples,shifts)['adjacent_pixel_register_pairs_compared'],24)

    def test_pixel_shift_opposes_first_scroll_rejected(self):
        samples,shifts=fake([1]*24)
        shifts[3]=2
        with self.assertRaisesRegex(ValueError,'disagree'):
            audit.join(samples,shifts)

    def test_changed_first_scroll_without_pixels_rejected(self):
        samples,shifts=fake([1]*24)
        samples[8]['first_y']=(samples[8]['first_y']-1)%256
        with self.assertRaisesRegex(ValueError,'disagree'):
            audit.join(samples,shifts)

    def test_later_2005_phase_must_not_change(self):
        samples,shifts=fake([1]*24)
        samples[11]['last_y']=71
        with self.assertRaisesRegex(ValueError,'later'):
            audit.join(samples,shifts)

    def test_missing_frame_rejected(self):
        samples,shifts=fake([1]*24)
        with self.assertRaisesRegex(ValueError,'25 authentic'):
            audit.join(samples[:-1],shifts)

    def test_missing_adjacent_pair_rejected(self):
        samples,shifts=fake([1]*24)
        with self.assertRaisesRegex(ValueError,'24 adjacent'):
            audit.join(samples,shifts[:-1])

    def test_duplicate_frame_rejected(self):
        samples,shifts=fake([1]*24)
        samples[5]['frame']=samples[4]['frame']
        with self.assertRaisesRegex(ValueError,'duplicates'):
            audit.join(samples,shifts)

    def test_scene_jump_outside_masked_search_rejected(self):
        samples,shifts=fake([1]*24)
        shifts[0]=18
        with self.assertRaisesRegex(ValueError,'unverified'):
            audit.join(samples,shifts)

    def test_negative_image_shift_outside_bound_rejected(self):
        samples,shifts=fake([1]*24)
        shifts[8]=-1
        with self.assertRaisesRegex(ValueError,'unverified'):
            audit.join(samples,shifts)

    def test_invalid_register_value_rejected(self):
        samples,shifts=fake([1]*24)
        samples[7]['first_y']=900
        with self.assertRaisesRegex(ValueError,'invalid'):
            audit.join(samples,shifts)

if __name__=='__main__':unittest.main()
