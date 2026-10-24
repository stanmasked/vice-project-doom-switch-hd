"""Stage359: fabricated-only tests for frozen 15-frame early transition protocol."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import audit_private_stage359_transition as s

def confidence(d=3,weak=()):
    return {k:(d,.0,.01 if k in weak else .15) for k in s.REGIONS}

def rgb(c=b'\x00\x00\x00'):
    return c*4

def motion_pairs():
    return ([("strict_four_of_four",3,-3)]*3 +
            [("qualified_three_of_four",0,0)]*4 +
            [("image_inconclusive",None,None)]*6 +
            [("mask_conflict",None,None)])


class Stage359SourceFree(unittest.TestCase):
    def test_window_and_original_roi_preregistration(self):
        self.assertEqual((s.FIRST,s.LAST),(545,559))
        self.assertEqual(len(s.FRAMES),15)
        self.assertEqual(s.PALETTE_FRAMES,(545,552,559))
        self.assertEqual(s.REGIONS,{"left_env_upper":(0,52,20,98),
            "left_env_lower":(0,52,98,175),"right_env_upper":(195,255,20,98),
            "right_env_lower":(195,255,98,175)})
        self.assertEqual((s.OFFSETS[0],s.OFFSETS[-1]),(-24,24))
        self.assertEqual((s.MAX_ERROR,s.MIN_GAP),(.16,.045))

    def test_four_qualify(self):
        self.assertEqual(s.classify_masks(confidence()),("strict_four_of_four",3))

    def test_three_qualify_weak_fourth(self):
        self.assertEqual(s.classify_masks(confidence(3,("right_env_upper",))),
                         ("qualified_three_of_four",3))

    def test_confident_fourth_contradiction(self):
        x=confidence();x["right_env_upper"]=(2,0,.2)
        self.assertEqual(s.classify_masks(x),("mask_conflict",None))

    def test_missing_region_is_failure(self):
        x=confidence();x.pop("right_env_lower")
        with self.assertRaises(ValueError):s.classify_masks(x)

    def test_invalid_nan_confidence_is_failure(self):
        x=confidence();x["left_env_upper"]=(3,float("nan"),.1)
        with self.assertRaises(ValueError):s.classify_masks(x)

    def test_15_flat_identity_is_not_motion(self):
        d=s.rgb_features([rgb()]*15,width=2,height=2)
        self.assertEqual(d["flat_single_color_frames"],15)
        self.assertEqual(d["identical_adjacent_rgb_pairs"],14)
        self.assertEqual(d["pairs_with_both_nonflat_and_nonidentical"],0)

    def test_partial_transition_counts(self):
        original=[rgb()]*7+[rgb(b'\xff\x00\x00')]*8
        d=s.rgb_features(original,width=2,height=2)
        self.assertEqual(d["identical_adjacent_rgb_pairs"],13)
        self.assertEqual(d["unique_whole_rgb_frames"],2)

    def test_missing_rgb_frame_errors(self):
        with self.assertRaises(ValueError):s.rgb_features([rgb()]*14,width=2,height=2)

    def test_missing_source_write_is_not_imputed(self):
        r=s.register_features([(False,True,False)]*5+[(True,False,True)]*10)
        self.assertEqual(r["frames_missing_second_phase_cpu_write"],5)
        self.assertEqual(r["pairs_with_two_verified_first_scroll_y"],9)
        self.assertFalse(r["missing_write_implies_scroll_zero"])
        self.assertFalse(r["retained_ppu_scroll_proven"])

    def test_ninth_mask_with_write_preserved(self):
        r=s.register_features([(False,True,False)]*8+[(True,True,True)]+[(True,False,True)]*6)
        self.assertEqual(r["present_write_and_zero_mask_frames"],1)
        self.assertEqual(r["missing_write_and_zero_mask_frames"],8)

    def test_invalid_registration_flags_errors(self):
        with self.assertRaises(ValueError):s.register_features([(1,False,True)]*15)

    def test_count_tiers_and_provenance_match_only_qualified(self):
        a=s.summarize(s.rgb_features([rgb()]*15,2,2),
                      s.register_features([(True,False,True)]*15),motion_pairs())
        self.assertEqual((a["source_rgb_four_of_four_pairs"],a["source_rgb_three_of_four_pairs"],
                          a["source_rgb_inconclusive_pairs"],a["source_rgb_mask_conflict_pairs"]),(3,4,6,1))
        self.assertEqual(a["qualified_register_matches"],7)
        self.assertFalse(a["prior_stage355_failed_motion_result_changed"])

    def test_different_register_step_is_contradiction_not_hidden(self):
        p=motion_pairs();p[0]=("strict_four_of_four",3,-2)
        a=s.summarize(s.rgb_features([rgb()]*15,2,2),
                      s.register_features([(True,False,True)]*15),p)
        self.assertEqual(a["qualified_register_contradictions"],1)

    def test_unsupported_register_not_a_pixel_register_match(self):
        p=motion_pairs();p[0]=("strict_four_of_four",3,None)
        a=s.summarize(s.rgb_features([rgb()]*15,2,2),
                      s.register_features([(True,False,True)]*15),p)
        self.assertEqual(a["qualified_register_unsupported"],1)
        self.assertEqual(a["qualified_register_matches"],6)

    def test_missing_pair_cannot_be_scored(self):
        with self.assertRaises(ValueError):
            s.summarize(s.rgb_features([rgb()]*15,2,2),
                        s.register_features([(True,False,True)]*15),motion_pairs()[:-1])

    def test_unqualified_forced_shift_rejected(self):
        p=motion_pairs();p[7]=("image_inconclusive",3,-3)
        with self.assertRaises(ValueError):
            s.summarize(s.rgb_features([rgb()]*15,2,2),
                        s.register_features([(True,False,True)]*15),p)


if __name__=="__main__":unittest.main()
