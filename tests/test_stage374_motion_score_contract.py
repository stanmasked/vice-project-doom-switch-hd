"""Manufactured-only Stage374 tests. No original ROM, FM2, RGB or PPU traces."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import stage374_motion_score_contract as s


def scored(shift=3, weak=(), flat=()):
    return {name:(shift, .1, .01 if name in weak else .07, name in flat)
            for name in s.BANDS}

class Stage374Contract(unittest.TestCase):
    def test_frozen_new_window_and_stage344_masks(self):
        self.assertEqual((s.FIRST,s.LAST),(641,655))
        self.assertEqual(s.BANDS['left_marking'],(93,99,20,175))
        self.assertEqual(s.BANDS['right_marking'],(157,163,20,175))
        self.assertEqual((s.MIN_SHIFT,s.MAX_SHIFT,s.MAX_ERROR,s.MIN_GAP),(-24,24,.16,.045))

    def test_strict_all_four(self):
        self.assertEqual(s.classify(scored()),('strict_four_of_four',3))

    def test_three_qualified_weak_fourth(self):
        self.assertEqual(s.classify(scored(weak=('right_marking',))),('qualified_three_of_four',3))

    def test_fourth_confident_contradiction_not_three(self):
        a=scored();a['right_marking']=(4,.0,.2,False)
        self.assertEqual(s.classify(a),('mask_conflict',None))

    def test_missing_or_extra_mask_rejected(self):
        x=scored();del x['right_environment']
        with self.assertRaises(ValueError):s.classify(x)
        y=scored();y['extra']=(3,.01,.4,False)
        with self.assertRaises(ValueError):s.classify(y)

    def test_tie_is_inconclusive(self):
        self.assertEqual(s.classify(scored(weak=tuple(s.BANDS))),('inconclusive',None))

    def test_flat_is_never_qualified(self):
        self.assertEqual(s.classify(scored(flat=('left_environment',))),('flat',None))

    def test_invalid_confidence_and_boolean_rejected(self):
        x=scored();x['left_marking']=(3,float('nan'),.2,False)
        with self.assertRaises(ValueError):s.classify(x)
        y=scored();y['left_marking']=(3,.1,.2,1)
        with self.assertRaises(ValueError):s.classify(y)

    def test_exact_boundary_is_accepted(self):
        a={key:(-24,.16,.045,False) for key in s.BANDS}
        self.assertEqual(s.classify(a),('strict_four_of_four',-24))

    def test_modulo_240_wrap_matches(self):
        self.assertEqual(s.register_comparison('strict_four_of_four',3,1,238),'match')

    def test_register_contradiction_is_retained(self):
        self.assertEqual(s.register_comparison('qualified_three_of_four',3,100,96),'contradiction')

    def test_ambiguous_120_step_unsupported(self):
        self.assertEqual(s.register_comparison('strict_four_of_four',2,0,120),'unsupported')

    def test_missing_y_is_not_imputed(self):
        self.assertEqual(s.register_comparison('strict_four_of_four',2,None,3),'unsupported')

    def test_image_inconclusive_forbids_source_match_claim(self):
        with self.assertRaises(ValueError):s.register_comparison('inconclusive',3,1,238)
        self.assertEqual(s.register_comparison('inconclusive',None,1,238),'unqualified')

    def test_incomplete_or_duplicate_window_rejected(self):
        p=[(f,'inconclusive',None,'unqualified') for f in range(641,655)]
        with self.assertRaises(ValueError):s.summarize(p[:-1])
        p[4]=p[3]
        with self.assertRaises(ValueError):s.summarize(p)

    def test_negative_holdout_not_promoted_to_success(self):
        p=[(f,'inconclusive',None,'unqualified') for f in range(641,655)]
        x=s.summarize(p)
        self.assertFalse(x['all_14_original_frame_pairs_proven'])
        self.assertEqual(x['inconclusive'],14)
        self.assertEqual(x['source_register_matches'],0)

    def test_fabricated_all_match_not_original_source_proof(self):
        p=[(f,'strict_four_of_four',3,'match') for f in range(641,655)]
        x=s.summarize(p)
        self.assertTrue(x['all_14_original_frame_pairs_proven'])
        self.assertFalse(x['source_original_media_authenticated_here'])
        self.assertFalse(x['camera_vehicle_collision_physics_proven'])

if __name__=='__main__':unittest.main()
