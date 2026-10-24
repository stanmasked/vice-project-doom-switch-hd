"""Stage354 preregistration guardrails, fabricated scores only (no ROM/FM2)."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_private_stage354_gap_holdout as s


def scores(d:int,weak:tuple[str,...]=())->dict:
    return {key:(d,0.0,.01 if key in weak else .2) for key in s.REGIONS}


def pairs():
    return ([('strict_four_of_four',0,0)]*10+
            [('independent_three_of_four',3,-3)]*8+
            [('inconclusive_insufficient_masks',None,None)]*4+
            [('qualified_mask_conflict',None,-5)]*2)


class Stage354SourceFree(unittest.TestCase):
    def test_exact_preregistered_holdout_geometry(self):
        self.assertEqual((s.FIRST,s.LAST),(495,519))
        self.assertEqual(s.REGIONS,{
           'left_env_upper': (0,52,20,98),
           'left_env_lower': (0,52,98,175),
           'right_env_upper': (195,255,20,98),
           'right_env_lower': (195,255,98,175)})
        self.assertEqual(s.OFFSETS,tuple(range(-24,25)))
        self.assertEqual((s.MAX_ERROR,s.MIN_GAP),(.16,.045))

    def test_strict_4_regions(self):
        self.assertEqual(s.determine(scores(5)),('strict_four_of_four',5))

    def test_one_low_confidence_region_allows_3_consensus(self):
        self.assertEqual(s.determine(scores(5,('right_env_upper',))),
                         ('independent_three_of_four',5))

    def test_two_weak_regions_are_inconclusive(self):
        self.assertEqual(s.determine(scores(5,('right_env_upper','left_env_lower'))),
                         ('inconclusive_insufficient_masks',None))

    def test_confident_fourth_disagreement_is_never_ignored(self):
        v=scores(5);v['right_env_upper']=(8,0.,.2)
        self.assertEqual(s.determine(v),('qualified_mask_conflict',None))

    def test_three_contradictory_confident_regions_are_conflict(self):
        v=scores(5,('right_env_upper',));v['left_env_lower']=(8,0.,.2)
        self.assertEqual(s.determine(v),('qualified_mask_conflict',None))

    def test_fourth_strong_but_higher_error_is_inconclusive(self):
        v=scores(5);v['right_env_upper']=(8,.17,.2)
        self.assertEqual(s.determine(v),('independent_three_of_four',5))

    def test_nan_numeric_score_rejected(self):
        v=scores(5);v['left_env_lower']=(5,float('nan'),.2)
        with self.assertRaisesRegex(ValueError,'malformed'):
            s.determine(v)

    def test_missing_source_region_rejected(self):
        v=scores(5);v.pop('right_env_lower')
        with self.assertRaisesRegex(ValueError,'four preregistered'):
            s.determine(v)

    def test_wrong_pixel_shift_outside_range_rejected(self):
        v=scores(5);v['left_env_upper']=(25,0.,.2)
        with self.assertRaisesRegex(ValueError,'malformed'):
            s.determine(v)

    def test_fake_output_coverage_distinguishes_conflicts(self):
        r=s.summarize(pairs())
        self.assertEqual(r['strict_four_of_four_pairs'],10)
        self.assertEqual(r['qualified_three_of_four_pairs'],8)
        self.assertEqual(r['inconclusive_insufficient_confident_masks'],4)
        self.assertEqual(r['conflicting_confident_mask_pairs'],2)
        self.assertEqual(r['qualified_modulo240_matches'],18)

    def test_three_of_four_register_contradiction_not_relabelled_match(self):
        v=pairs();v[12]=('independent_three_of_four',3,-4)
        r=s.summarize(v)
        self.assertEqual(r['qualified_modulo240_register_contradictions'],1)

    def test_qualified_unrepresentable_vertical_ppu_not_falsely_matched(self):
        v=pairs();v[3]=('strict_four_of_four',0,None)
        r=s.summarize(v)
        self.assertEqual(r['qualified_unsupported_register_pairs'],1)

    def test_insufficient_region_has_no_assigned_shift(self):
        v=pairs();v[18]=('inconclusive_insufficient_masks',3,-3)
        with self.assertRaisesRegex(ValueError,'nonqualified'):
            s.summarize(v)

    def test_missing_pair_rejected(self):
        with self.assertRaisesRegex(ValueError,'24 adjacent'):
            s.summarize(pairs()[:-1])

    def test_false_camera_physics_claim_prohibited(self):
        self.assertFalse(s.summarize(pairs())['general_vehicle_road_physics_or_hardware_ppu_dot_proven'])

    def test_unexpected_boolean_shift_rejected(self):
        v=scores(3);v['left_env_upper']=(True,0,.2)
        with self.assertRaisesRegex(ValueError,'malformed'):
            s.determine(v)


if __name__=='__main__':unittest.main()
