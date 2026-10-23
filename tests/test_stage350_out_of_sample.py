"""Fabricated-only Stage350 fast-scroll original-source contract tests."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_private_stage350_out_of_sample as stage


def synthetic_pairs():
    return [(-3,-3,3)]*7+[(-4,-4,4)]*17


class Stage350SourceFree(unittest.TestCase):
    def test_out_of_sample_four_pixel_fast_scroll(self):
        x=stage.summarize(synthetic_pairs())
        self.assertEqual(x['first_vertical_scroll_modulo240_matches'],24)
        self.assertEqual(x['first_vertical_scroll_signed8_matches'],24)
        self.assertEqual(x['original_display_shift_plus_three_pairs'],7)
        self.assertEqual(x['original_display_shift_plus_four_pairs'],17)

    def test_four_windows_aggregate_without_physics_claim(self):
        r=stage.summarize(synthetic_pairs())
        self.assertEqual(r['four_window_combined_pairs_with_modulo240_agreement'],96)
        self.assertFalse(r['camera_vehicle_speed_road_geometry_or_collision_proven'])
        self.assertFalse(r['hardware_ppu_dot_proven'])

    def test_source_pixel_shift_wrong_direction_rejected(self):
        sample=synthetic_pairs();sample[8]=(-4,-4,-4)
        with self.assertRaisesRegex(ValueError,'outside verified'):
            stage.summarize(sample)

    def test_register_does_not_match_original_pixels(self):
        sample=synthetic_pairs();sample[7]=(-3,-3,4)
        with self.assertRaisesRegex(ValueError,'fails'):
            stage.summarize(sample)

    def test_missing_adjacent_transition_rejected(self):
        with self.assertRaisesRegex(ValueError,'missing adjacent'):
            stage.summarize(synthetic_pairs()[:-1])

    def test_duplicated_transition_rejected(self):
        with self.assertRaisesRegex(ValueError,'missing adjacent'):
            stage.summarize(synthetic_pairs()+[(-4,-4,4)])

    def test_one_pixel_texture_in_fast_window_rejected(self):
        sample=synthetic_pairs();sample[9]=(-1,-1,1)
        with self.assertRaisesRegex(ValueError,'outside verified'):
            stage.summarize(sample)

    def test_five_pixel_motion_outside_validated_range(self):
        sample=synthetic_pairs();sample[1]=(-5,-5,5)
        with self.assertRaisesRegex(ValueError,'outside verified'):
            stage.summarize(sample)

    def test_modified_3_4_distribution_rejected(self):
        sample=synthetic_pairs();sample[0]=(-4,-4,4)
        with self.assertRaisesRegex(ValueError,'baseline'):
            stage.summarize(sample)

    def test_altered_signed8_consistency_rejected(self):
        sample=synthetic_pairs();sample[5]=(-3,1,3)
        with self.assertRaisesRegex(ValueError,'baseline'):
            stage.summarize(sample)

    def test_input_sha_and_original_paths_are_not_in_output(self):
        result=stage.summarize(synthetic_pairs())
        self.assertFalse(result['original_game_pixels_raw_registers_or_private_sha_exposed'])
        self.assertNotIn('sha256',str(result).lower())

    def test_every_record_count_matches(self):
        result=stage.summarize(synthetic_pairs())
        self.assertEqual(result['adjacent_pixel_register_pairs'],24)
        self.assertEqual(result['consecutive_original_rgb_frames'],25)

    def test_source_bands_must_agree_not_auto_inferred(self):
        self.assertTrue(stage.summarize(synthetic_pairs())['four_masked_texture_bands_agree_for_each_pair'])

if __name__=='__main__':unittest.main()
