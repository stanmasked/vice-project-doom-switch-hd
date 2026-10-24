"""Stage361 finite scroll envelope: fabricated negative tests + public-safe archive contract.

No ROM, FM2, raster, palette plane, CPU/PPU TSV or original private SHA is read.
"""
from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import stage361_scroll_mode_envelope as m


def witness(start=20,shift=3,tier="strict_four_of_four",reg=-3,
            origin="fabricated_test",source=True,flat=False):
    return m.PairEvidence(start,shift,tier,reg,origin,source,flat)


def safe_archives():
    return (json.loads((ROOT/"docs"/"stage360_public_aggregate.json").read_text(encoding="utf8")),
            json.loads((ROOT/"docs"/"stage359_public_aggregate.json").read_text(encoding="utf8")))


class Stage361FiniteStateTests(unittest.TestCase):
    def test_only_observed_magnitudes_in_scope(self):
        self.assertEqual(m.SUPPORTED_SHIFTS,{3,4,5})
        self.assertNotIn(0,m.SUPPORTED_SHIFTS)

    def test_confirmed_strict_four(self):
        self.assertEqual(m.classify_pair(witness()),("confirmed_finite_mode",3))

    def test_confirmed_three_of_four(self):
        self.assertEqual(m.classify_pair(witness(tier="qualified_three_of_four")),
                         ("confirmed_finite_mode",3))

    def test_image_inconclusive_not_a_camera_shift(self):
        self.assertEqual(m.classify_pair(witness(shift=None,tier="image_inconclusive")),
                         ("image_inconclusive",None))

    def test_conflicting_masks_never_pass(self):
        self.assertEqual(m.classify_pair(witness(shift=None,tier="mask_conflict")),
                         ("confident_mask_conflict",None))

    def test_source_missing_no_inference(self):
        self.assertEqual(m.classify_pair(witness(source=False)),("source_unverified",None))

    def test_unverified_source_does_not_create_segment(self):
        d=m.scan_contiguous([witness(20),witness(21,source=False),witness(22)])
        self.assertEqual([x["observed_pair_count"] for x in d["observed_mode_segments"]],[1,1])
        self.assertEqual(d["adjacent_observed_mode_transitions"],[])

    def test_missing_register_cannot_be_forward_filled(self):
        self.assertEqual(m.classify_pair(witness(reg=None)),("register_unsupported",None))

    def test_contradiction_is_not_clipped_into_agreement(self):
        self.assertEqual(m.classify_pair(witness(reg=-4)),("image_register_contradiction",None))

    def test_zero_shift_is_valid_prior_evidence_but_outside_361_envelope(self):
        self.assertEqual(m.classify_pair(witness(shift=0,reg=0)),
                         ("verified_out_of_scope_shift",None))

    def test_another_numeric_shift_does_not_expand_model(self):
        self.assertEqual(m.classify_pair(witness(shift=6,reg=-6)),
                         ("verified_out_of_scope_shift",None))

    def test_flat_image_is_not_verified_motion(self):
        self.assertEqual(m.classify_pair(witness(flat=True)),("image_inconclusive",None))

    def test_negative_source_original_no_fabricated_qualified_tier(self):
        with self.assertRaises(ValueError):
            m.classify_pair(witness(tier="archived_qualified_unpartitioned"))

    def test_preexisting_aggregate_tier_can_only_be_appropriately_sourced(self):
        row=witness(tier="archived_qualified_unpartitioned",origin="stage350_aggregate")
        self.assertEqual(m.classify_pair(row),("confirmed_finite_mode",3))

    def test_qualified_pixel_without_shift_fails_closed(self):
        with self.assertRaises(ValueError):
            m.classify_pair(witness(shift=None))

    def test_unqualified_nonzero_pixel_forced_fails_closed(self):
        with self.assertRaises(ValueError):
            m.classify_pair(witness(shift=3,tier="image_inconclusive"))

    def test_frame_number_float_rejected(self):
        with self.assertRaises(ValueError):
            m.classify_pair(witness(start=20.5))

    def test_invalid_camera_distance_gt_original_search_fails(self):
        with self.assertRaises(ValueError):
            m.classify_pair(witness(shift=25))

    def test_invalid_signed_mod240_register_fails(self):
        with self.assertRaises(ValueError):
            m.classify_pair(witness(reg=-120))

    def test_empty_frame_interval_rejected(self):
        with self.assertRaises(ValueError):
            m.scan_contiguous([])

    def test_gap_refuses_interpolation(self):
        with self.assertRaises(ValueError):
            m.scan_contiguous([witness(20),witness(22)])

    def test_duplicate_refuses_interpolation(self):
        with self.assertRaises(ValueError):
            m.scan_contiguous([witness(20),witness(20)])

    def test_order_swap_refuses_interpolation(self):
        with self.assertRaises(ValueError):
            m.scan_contiguous([witness(21),witness(20)])

    def test_transition_only_between_adjacent_confirmed_pairs(self):
        d=m.scan_contiguous([witness(20,3,reg=-3),
            witness(21,4,reg=-4),witness(22,5,reg=-5)])
        self.assertEqual([(t["at_pair_start_frame"],t["from_shift_px"],t["to_shift_px"])
                          for t in d["adjacent_observed_mode_transitions"]],
                         [(21,3,4),(22,4,5)])
        self.assertFalse(d["predicts_missing_or_future_frames"])

    def test_unknown_between_modes_breaks_transition(self):
        d=m.scan_contiguous([witness(20,3,reg=-3),
            witness(21,None,tier="image_inconclusive",reg=None),
            witness(22,5,reg=-5)])
        self.assertEqual(len(d["observed_mode_segments"]),2)
        self.assertEqual(d["adjacent_observed_mode_transitions"],[])

    def test_out_of_scope_shift_breaks_transition(self):
        d=m.scan_contiguous([witness(20,3,reg=-3),witness(21,0,reg=0),
                             witness(22,5,reg=-5)])
        self.assertEqual(d["confirmed_pair_count"],2)
        self.assertEqual(d["adjacent_observed_mode_transitions"],[])

    def test_contradiction_breaks_transition(self):
        d=m.scan_contiguous([witness(20,3,reg=-3),witness(21,4,reg=-5),
                             witness(22,5,reg=-5)])
        self.assertEqual(d["pair_classification_counts"]["image_register_contradiction"],1)
        self.assertEqual(d["adjacent_observed_mode_transitions"],[])

    def test_reconstruct_expected_archived_finite_41_pairs(self):
        a,b=safe_archives()
        pairs=m.reconstruct_prior_aggregate_witness(a,b)
        self.assertEqual((len(pairs),pairs[0].start_frame,pairs[-1].start_frame),
                         (41,519,559))
        self.assertEqual(sum(p.tier=="strict_four_of_four" for p in pairs),3)
        self.assertEqual(sum(p.tier=="archived_qualified_unpartitioned" for p in pairs),38)
        self.assertEqual(m.scan_contiguous(pairs)["confirmed_pair_count"],41)

    def test_archived_public_provenance_unchanged_and_exact_runs(self):
        a,b=safe_archives()
        d=m.bounded_model(a,b)
        self.assertEqual(d["observed_mode_segments"],[
            {"shift_px":3,"pair_start_first":519,"pair_start_last":526,"observed_pair_count":8},
            {"shift_px":4,"pair_start_first":527,"pair_start_last":558,"observed_pair_count":32},
            {"shift_px":5,"pair_start_first":559,"pair_start_last":559,"observed_pair_count":1}])
        self.assertEqual([x["at_pair_start_frame"] for x in d["adjacent_observed_mode_transitions"]],
                         [527,559])
        self.assertFalse(d["fixed_stage355_failed_source_gate_preserved"] is False)
        self.assertTrue(d["fixed_stage357_five_inconclusive_pairs_preserved"])
        self.assertFalse(d["predicts_missing_or_future_frames"])

    def test_mutated_stage350_transition_order_fails_before_projection(self):
        a,b=safe_archives()
        a["stage350_pairs_first_shift_three"]["count"]=8
        with self.assertRaises(ValueError):m.bounded_model(a,b)

    def test_stage350_positive_counts_do_not_mask_conflict(self):
        a,b=safe_archives()
        a["stage350_confident_conflicts"]=1
        with self.assertRaises(ValueError):m.bounded_model(a,b)

    def test_stage359_ambiguous_pairs_cannot_be_silently_reclassified(self):
        a,b=safe_archives()
        b["image_inconclusive_pairs"]=1
        with self.assertRaises(ValueError):m.bounded_model(a,b)

    def test_stage359_missing_first_y_anchor_breaks_source_eligibility(self):
        a,b=safe_archives()
        b["qualified_without_authenticated_source_register_pair"]=1
        with self.assertRaises(ValueError):m.bounded_model(a,b)

    def test_stage359_source_register_contradiction_cannot_be_hidden(self):
        a,b=safe_archives()
        b["qualified_image_source_register_contradictions"]=1
        with self.assertRaises(ValueError):m.bounded_model(a,b)

    def test_stage359_scroll_shift_changed_rejected(self):
        a,b=safe_archives()
        b["all_qualified_image_source_vertical_shift_pixels"]=5
        with self.assertRaises(ValueError):m.bounded_model(a,b)

    def test_cross_boundary_559_560_not_invented_from_stage359(self):
        a,b=safe_archives()
        a["boundary_pairs"][2]["first_original_ppu_scroll_step_mod240"]=-4
        with self.assertRaises(ValueError):m.bounded_model(a,b)

    def test_zero_publication_of_private_source_digests(self):
        a,b=safe_archives()
        d=json.dumps(m.bounded_model(a,b))
        self.assertNotIn("sha256",d.lower())
        self.assertNotIn("stage335_ppu_latch",d)
        self.assertNotIn("stage341_classic",d)


    def test_published_source_safe_summary_matches_bounded_model_exactly(self):
        source360,source359=safe_archives()
        published=json.loads((ROOT/"docs"/"stage361_public_bounded_envelope.json").read_text(encoding="utf8"))
        self.assertEqual(published,m.bounded_model(source360,source359))

if __name__=="__main__":
    unittest.main()
