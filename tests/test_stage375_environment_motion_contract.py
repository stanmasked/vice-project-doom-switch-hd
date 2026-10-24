"""Stage375 synthetic-only regression suite, fixed BEFORE new original replay."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import stage375_environment_motion_contract as s


def score(d=5, weak=(), flat=()):
    return {key: (d, .04, .015 if key in weak else .22, key in flat)
            for key in s.REGIONS}


class Stage375PreExposure(unittest.TestCase):
    def test_window_frames_planes(self):
        self.assertEqual((s.FIRST, s.LAST), (656, 670))
        self.assertEqual(len(s.FRAMES), 15)
        self.assertEqual(s.PALETTE_FRAMES, (656, 663, 670))

    def test_fixed_stage352_stage359_masks(self):
        self.assertEqual(s.REGIONS, {
            'left_env_upper': (0,52,20,98), 'left_env_lower': (0,52,98,175),
            'right_env_upper': (195,255,20,98), 'right_env_lower': (195,255,98,175)})
        self.assertEqual((s.MIN_SHIFT, s.MAX_SHIFT, s.MAX_ERROR, s.MIN_GAP),
                         (-24,24,.16,.045))

    def test_all_four_confident(self):
        self.assertEqual(s.classify(score()), ('strict_four_of_four',5))

    def test_guarded_three(self):
        self.assertEqual(s.classify(score(weak=('right_env_lower',))), ('qualified_three_of_four',5))

    def test_guarded_three_must_not_hide_conflicting_fourth(self):
        data=score(); data['right_env_lower']=(6,0,.4,False)
        self.assertEqual(s.classify(data), ('mask_conflict',None))

    def test_two_qualified_inconclusive(self):
        self.assertEqual(s.classify(score(weak=('right_env_lower','left_env_lower'))), ('inconclusive',None))

    def test_flat_not_motion(self):
        self.assertEqual(s.classify(score(flat=('left_env_upper',))), ('flat',None))

    def test_missing_extra_region(self):
        data=score(); data.pop('right_env_lower')
        with self.assertRaises(ValueError): s.classify(data)
        data=score(); data['extra']=(5,0,.2,False)
        with self.assertRaises(ValueError): s.classify(data)

    def test_invalid_float_nan_infinity(self):
        for v in (float('nan'), float('inf'), -0.1):
            data=score(); data['left_env_upper']=(5,v,.2,False)
            with self.assertRaises(ValueError): s.classify(data)

    def test_invalid_shift_float_bool(self):
        for v in (25,-25,True,4.0):
            data=score(); data['left_env_upper']=(v,0,.2,False)
            with self.assertRaises(ValueError): s.classify(data)

    def test_invalid_flat_type(self):
        data=score(); data['left_env_upper']=(5,0,.2,1)
        with self.assertRaises(ValueError): s.classify(data)

    def test_boundary_exact(self):
        data={key:(-24,.16,.045,False) for key in s.REGIONS}
        self.assertEqual(s.classify(data), ('strict_four_of_four',-24))

    def test_modulo_wrap(self):
        self.assertEqual(s.register_verdict('strict_four_of_four',3,1,238), 'match')

    def test_register_contradiction(self):
        self.assertEqual(s.register_verdict('qualified_three_of_four',5,120,116), 'contradiction')

    def test_unsupported_missing_second_phase(self):
        self.assertEqual(s.register_verdict('strict_four_of_four',3,None,8), 'unsupported')

    def test_unsupported_120_ambiguity(self):
        self.assertEqual(s.register_verdict('strict_four_of_four',2,0,120), 'unsupported')

    def test_out_of_range_source_y_unsupported(self):
        self.assertEqual(s.register_verdict('strict_four_of_four',2,0,255), 'unsupported')

    def test_never_impute_image_shift(self):
        with self.assertRaises(ValueError): s.register_verdict('inconclusive',5,100,95)
        self.assertEqual(s.register_verdict('inconclusive',None,100,95), 'unqualified')

    def test_duplicate_or_missing_pair_fail(self):
        records=[(f,'inconclusive',None,'unqualified') for f in range(656,670)]
        with self.assertRaises(ValueError): s.summarize(records[:-1])
        records[3]=records[2]
        with self.assertRaises(ValueError): s.summarize(records)

    def test_summary_counts_without_promotion(self):
        records=[(f,'inconclusive',None,'unqualified') for f in range(656,670)]
        d=s.summarize(records)
        self.assertEqual((d['inconclusive'],d['register_matches'],d['unqualified']), (14,0,14))
        self.assertFalse(d['original_media_authentication_by_this_module'])

    def test_numerical_perfect_score_not_source_authenticity(self):
        records=[(f,'strict_four_of_four',5,'match') for f in range(656,670)]
        d=s.summarize(records)
        self.assertEqual(d['register_matches'],14)
        self.assertFalse(d['original_media_authentication_by_this_module'])
        self.assertFalse(d['original_game_camera_vehicle_collision_physics_proven'])

    def test_qualified_must_have_verdict(self):
        records=[(f,'strict_four_of_four',5,'match') for f in range(656,670)]
        records[0]=(656,'strict_four_of_four',5,'unqualified')
        with self.assertRaises(ValueError): s.summarize(records)

    def test_source_none_as_int_rejected(self):
        self.assertEqual(s.register_verdict('strict_four_of_four',2,False,3),'unsupported')

if __name__=='__main__': unittest.main()
