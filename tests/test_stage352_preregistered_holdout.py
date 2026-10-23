"""Stage352 synthetic-only precommitted mask and holdout confidence tests."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_private_stage352_preregistered_holdout as hold


def valid_pairs():
    return [(0,'qualified',0)]*4+[(2,'qualified',-2)]*10+[
        (None,'ambiguous_or_changed_scene',-5)]*9+[
        (None,'independent_environment_masks_disagree',-8)]


class Stage352PreregisteredSourceFree(unittest.TestCase):
    def test_locked_mask_coordinates_exact(self):
        self.assertEqual(hold.LOCKED_REGIONS,{
           'left_env_upper': (0,52,20,98),
           'left_env_lower': (0,52,98,175),
           'right_env_upper': (195,255,20,98),
           'right_env_lower': (195,255,98,175)})
        self.assertEqual(hold.SIGNED_OFFSETS,tuple(range(-24,25)))
        self.assertEqual(hold.MIN_RUNNER_GAP,.045)
        self.assertEqual(hold.MAX_RGB_MISMATCH,.16)

    def test_new_source_window_not_stage351_training_data(self):
        self.assertEqual((hold.FIRST,hold.LAST),(585,609))

    def test_explicit_unresolved_in_results(self):
        r=hold.summarize(valid_pairs())
        self.assertEqual(r['adjacent_pixel_pairs_total'],24)
        self.assertEqual(r['unambiguously_qualified_pairs'],14)
        self.assertEqual(r['inconclusive_pixel_pairs'],10)
        self.assertFalse(r['masks_changed_after_source_observation'])

    def test_qualified_contradictions_must_be_counted(self):
        v=valid_pairs();v[0]=(2,'qualified',-3)
        r=hold.summarize(v)
        self.assertEqual(r['qualified_mod240_scroll_contradictions'],1)

    def test_bad_ppu_step_is_not_a_match(self):
        v=valid_pairs();v[0]=(0,'qualified',None)
        r=hold.summarize(v)
        self.assertEqual(r['qualified_but_unsupported_ppu_y_pairs'],1)

    def test_inconclusive_with_shift_is_invalid(self):
        v=valid_pairs();v[0]=(2,'ambiguous_or_changed_scene',-2)
        with self.assertRaisesRegex(ValueError,'unknown'):
            hold.summarize(v)

    def test_missing_frame_transition_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):
            hold.summarize(valid_pairs()[:-1])

    def test_outside_offset_search_rejected(self):
        v=valid_pairs();v[0]=(25,'qualified',-25)
        with self.assertRaisesRegex(ValueError,'invalid'):
            hold.summarize(v)

    def test_float_shift_not_a_valid_observation(self):
        v=valid_pairs();v[0]=(2.0,'qualified',-2)
        with self.assertRaisesRegex(ValueError,'invalid'):
            hold.summarize(v)

    def test_fabricated_flat_rgb_remains_inconclusive(self):
        a=bytes([90,90,90])* (256*240)
        shift,why=hold.qualify(a,a)
        self.assertIsNone(shift)
        self.assertEqual(why,'ambiguous_or_changed_scene')

    def test_missing_original_rgb_channels_rejected(self):
        with self.assertRaisesRegex(ValueError,'RGB'):
            hold.qualify(b'\0'*90,b'\0'*90)

    def test_generic_camera_and_physics_never_claimed(self):
        r=hold.summarize(valid_pairs())
        self.assertFalse(r['general_vehicle_speed_camera_speed_road_collision_proven'])
        self.assertFalse(r['original_pixels_register_values_or_private_hashes_exposed'])


if __name__=='__main__':unittest.main()
