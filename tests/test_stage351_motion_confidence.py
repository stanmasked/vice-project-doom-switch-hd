"""Stage351 synthetic-only confidence and adaptive mask provenance tests."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import classify_stage351_motion_confidence as aud

PATTERN=[0]*5+[2]*2+[3]+[5]*15+[8]


def band_result(shift:int, *, gap:float=.3):
    return {'best_shift':shift,'best_error_fraction':0.0,
            'runner_gap_fraction':gap}


def samples():
    original=[];followup=[]
    for d in PATTERN:
        original.append({name:band_result(d) for name in aud.PRIMARY})
        followup.append({name:band_result(d) for name in aud.FOLLOWUP})
    original[-1]['left_marking']['runner_gap_fraction']=.0003
    original[-1]['right_marking']['runner_gap_fraction']=.0
    return original,followup,[-d for d in PATTERN]


class Stage351Synthetic(unittest.TestCase):
    def test_observed_stage351_two_gate_pattern(self):
        primary,alternate,steps=samples()
        report=aud.classify(primary,alternate,mod240_steps=steps)
        self.assertEqual(report['preregistered_four_band_qualified_pairs'],23)
        self.assertEqual(report['adaptive_environment_submask_only_pairs'],1)
        self.assertFalse(report['fully_independent_four_band_confirmation_24_of_24'])

    def test_posthoc_evidence_not_promoted(self):
        x,y,s=samples()
        r=aud.classify(x,y,mod240_steps=s)
        self.assertTrue(r['adaptive_submask_evidence_requires_out_of_sample_retest'])

    def test_exclusive_mod240_regression(self):
        x,y,s=samples()
        s[0]-=1
        with self.assertRaisesRegex(ValueError,'contradiction'):
            aud.classify(x,y,mod240_steps=s)

    def test_adaptive_submask_mismatch_rejected(self):
        x,y,s=samples()
        for name in y[-1]:y[-1][name]['best_shift']=4
        with self.assertRaisesRegex(ValueError,'contradiction'):
            aud.classify(x,y,mod240_steps=s)

    def test_flat_marking_rejects_strict(self):
        x,y,s=samples()
        self.assertIsNone(aud.decision(x[-1]))

    def test_flat_followup_rejected(self):
        x,y,s=samples()
        y[-1]['left_env_upper']['runner_gap_fraction']=0.0
        with self.assertRaisesRegex(ValueError,'baseline'):
            aud.classify(x,y,mod240_steps=s)

    def test_wrong_source_window_length_rejected(self):
        x,y,s=samples()
        with self.assertRaisesRegex(ValueError,'complete'):
            aud.classify(x[:-1],y,mod240_steps=s)

    def test_missing_region_rejected(self):
        x,y,s=samples()
        x[0].pop('right_marking')
        with self.assertRaisesRegex(ValueError,'candidate RGB'):
            aud.classify(x,y,mod240_steps=s)

    def test_corrupt_error_value_rejected(self):
        x,y,s=samples()
        x[0]['left_environment']['best_error_fraction']=-1
        with self.assertRaisesRegex(ValueError,'invalid RGB'):
            aud.classify(x,y,mod240_steps=s)

    def test_only_primary_24_out_of_24_is_wrong_evidence_baseline(self):
        x,y,s=samples()
        for name in aud.PRIMARY:x[-1][name]['runner_gap_fraction']=.3
        with self.assertRaisesRegex(ValueError,'baseline'):
            aud.classify(x,y,mod240_steps=s)

    def test_shift_outside_inspected_rgb_search_rejected(self):
        x,y,s=samples()
        x[0]['left_environment']['best_shift']=50
        with self.assertRaisesRegex(ValueError,'invalid RGB'):
            aud.classify(x,y,mod240_steps=s)

    def test_conservative_disclaimer_in_report(self):
        x,y,s=samples()
        self.assertFalse(aud.classify(x,y,mod240_steps=s)['general_game_camera_speed_or_vehicle_physics_proven'])

if __name__=='__main__':unittest.main()
