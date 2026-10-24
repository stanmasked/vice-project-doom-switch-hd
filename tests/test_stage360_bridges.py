"""Stage360: fully source-free fabricated tests; never import original game assets."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import audit_private_stage360_bridges as s


def marks(shifts=(3,3,3,3),weak=()):
    return {name:(shifts[i],0.0,.02 if name in weak else .2,
                  name not in weak)
            for i,name in enumerate(s.ROIS)}


def result(tier="strict_four_of_four",shift=3,comp="matched"):
    return {"tier":tier,"shift":shift,"comparison":comp}


class Stage360BridgeSyntheticTests(unittest.TestCase):
    def test_precise_cross_archive_edges(self):
        self.assertEqual(s.BOUNDARIES,((519,520),(544,545),(559,560)))
        self.assertEqual(s.WINDOWS[354],(495,519))
        self.assertEqual(s.WINDOWS[350],(520,544))
        self.assertEqual(s.WINDOWS[359],(545,559))
        self.assertEqual(s.WINDOWS[351],(560,584))

    def test_four_source_environment_rois_frozen(self):
        self.assertEqual(s.ROIS,{"left_env_upper":(0,52,20,98),
            "left_env_lower":(0,52,98,175),
            "right_env_upper":(195,255,20,98),
            "right_env_lower":(195,255,98,175)})
        self.assertEqual((min(s.OFFSETS),max(s.OFFSETS)),(-24,24))
        self.assertEqual((s.MAX_ERROR,s.MIN_GAP),(.16,.045))

    def test_strict_four_consensus(self):
        self.assertEqual(s.classify_bands(marks()),("strict_four_of_four",3))

    def test_exactly_three_confident_fourth_weak(self):
        self.assertEqual(s.classify_bands(marks(weak=("right_env_lower",))),
                         ("qualified_three_of_four",3))

    def test_confident_disagreement_is_negative(self):
        self.assertEqual(s.classify_bands(marks((3,4,3,3))),("mask_conflict",None))

    def test_too_few_confident_is_inconclusive(self):
        self.assertEqual(s.classify_bands(marks(weak=("left_env_upper","right_env_lower"))),
                         ("image_inconclusive",None))

    def test_missing_one_environment_mask_is_error(self):
        x=marks();x.pop("left_env_upper")
        with self.assertRaises(ValueError):s.classify_bands(x)

    def test_untrusted_confidence_marker_is_error(self):
        x=marks();x["left_env_upper"]=(3,0,.2,False)
        with self.assertRaises(ValueError):s.classify_bands(x)

    def test_nan_rgb_gap_does_not_pass(self):
        x=marks();x["left_env_upper"]=(3,0,float("nan"),False)
        with self.assertRaises(ValueError):s.classify_bands(x)

    def test_signed_mod240_decrement_matches_native_positive(self):
        self.assertEqual(s.signed_mod240_step(110,106),-4)

    def test_mod240_rollover_is_not_signed256(self):
        self.assertEqual(s.signed_mod240_step(1,239),-2)

    def test_half_turn_ambiguous_register_unsupported(self):
        self.assertIsNone(s.signed_mod240_step(0,120))

    def test_missing_register_is_not_imputed(self):
        self.assertIsNone(s.signed_mod240_step(None,12))
        self.assertIsNone(s.signed_mod240_step(12,None))

    def test_out_of_range_ppu_register_unsupported(self):
        self.assertIsNone(s.signed_mod240_step(240,0))

    def test_exact_source_pair_counts(self):
        joins=[result(),result("qualified_three_of_four",4),result("image_inconclusive",None,"not_qualified")]
        within=[result()]*7+[result("qualified_three_of_four",4)]*17
        d=s.summarize(joins,within,verified_original_members=118)
        self.assertEqual(d["boundary_strict_four_of_four"],1)
        self.assertEqual(d["boundary_qualified_three_of_four"],1)
        self.assertEqual(d["boundary_image_inconclusive"],1)
        self.assertEqual(d["boundary_register_not_qualified"],1)
        self.assertEqual(d["stage350_within_qualified_image_shift_histogram"],{"3":7,"4":17})
        self.assertEqual(d["source_original_members_sha256_checked_across_all_archives"],118)

    def test_qualified_original_register_contradiction_cannot_be_dropped(self):
        joins=[result(comp="contradiction"),result(),result()]
        d=s.summarize(joins,[result()]*24,verified_original_members=118)
        self.assertEqual(d["boundary_register_contradiction"],1)
        self.assertEqual(d["boundary_register_matched"],2)

    def test_unsupported_qualified_register_stays_unsupported(self):
        joins=[result(comp="register_unsupported"),result(),result()]
        d=s.summarize(joins,[result()]*24,verified_original_members=118)
        self.assertEqual(d["boundary_register_register_unsupported"],1)

    def test_must_not_convert_conflicted_pixel_pair_into_match(self):
        joins=[result(tier="mask_conflict",shift=None,comp="matched")]*3
        with self.assertRaises(ValueError):
            s.summarize(joins,[result()]*24,verified_original_members=118)

    def test_exact_three_joins_required(self):
        with self.assertRaises(ValueError):s.summarize([result()]*2,[result()]*24,verified_original_members=118)

    def test_exact_24_within_stage350_pairs_required(self):
        with self.assertRaises(ValueError):s.summarize([result()]*3,[result()]*23,verified_original_members=118)

    def test_absent_owner_original_archive_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with self.assertRaises(ValueError):
                s.source_manifest_check(p/"private.zip",p/"private.json","0"*64,350,"1"*64,"2"*64)

    def test_public_summary_preserves_prior_negative_gates(self):
        d=s.summarize([result()]*3,[result()]*24,verified_original_members=118)
        self.assertFalse(d["stage355_inconclusive_failed_gate_changed"])
        self.assertFalse(d["stage357_five_inconclusive_image_pairs_changed"])
        self.assertFalse(d["camera_vehicle_speed_law_physics_collision_hardware_ppu_dot_verified"])
        self.assertFalse(d["original_rom_fm2_pixels_full_source_traces_or_private_hashes_on_public_github"])


if __name__=="__main__":unittest.main()
