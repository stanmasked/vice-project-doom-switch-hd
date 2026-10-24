#!/usr/bin/env python3
"""Stage361: finite, source-free scroll evidence envelope, NOT game camera physics.

Consumes only previously published privacy-safe Stage359 and Stage360 aggregate
records; authentic ROM, movie, pixel data, private hashes and CPU/PPU raw rows
are deliberately not available to this module or its tests. A finite record
must never predict an unobserved frame or fill a missing first $2005 anchor.
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path

SUPPORTED_SHIFTS=frozenset((3,4,5))
CONFIDENT=frozenset(("strict_four_of_four","qualified_three_of_four",
                     "archived_qualified_unpartitioned"))
TIERS=CONFIDENT|frozenset(("image_inconclusive","mask_conflict"))
ORIGINS=frozenset(("stage350_aggregate","stage359_aggregate","stage360_cross_archive",
                   "fabricated_test"))
STAGE360_FORMAT="vpd_stage360_cross_archive_retrospective_original_continuity_public_v1"
STAGE359_FORMAT="vpd_stage359_preregistered_original_545_559_holdout_public_v1"


@dataclass(frozen=True)
class PairEvidence:
    start_frame:int
    image_shift:int|None
    tier:str
    first_ppu_y_signed_mod240_step:int|None
    origin:str
    source_provenance_ok:bool=True
    flat_or_byte_identical:bool=False


def classify_pair(pair:PairEvidence)->tuple[str,int|None]:
    """Pure witness classification. Never substitutes a source register value."""
    if (type(pair.start_frame) is not int or pair.start_frame<0 or
        pair.origin not in ORIGINS or pair.tier not in TIERS or
        type(pair.source_provenance_ok) is not bool or
        type(pair.flat_or_byte_identical) is not bool):
        raise ValueError("invalid bounded source witness")
    shift=pair.image_shift
    reg=pair.first_ppu_y_signed_mod240_step
    if (shift is not None and (type(shift) is not int or not -24<=shift<=24)
        or reg is not None and (type(reg) is not int or not -119<=reg<=119)):
        raise ValueError("invalid source shift or signed modulo240 first-write step")
    if pair.tier not in CONFIDENT and shift is not None:
        raise ValueError("inconclusive or contradictory images cannot carry a selected shift")
    if pair.tier in CONFIDENT and shift is None:
        raise ValueError("qualified RGB observation requires its actual measured shift")
    if pair.tier=="archived_qualified_unpartitioned" and pair.origin not in (
            "stage350_aggregate","stage359_aggregate"):
        raise ValueError("aggregate confidence not permitted on new per-frame witnesses")
    if not pair.source_provenance_ok:return ("source_unverified",None)
    if pair.tier=="mask_conflict":return ("confident_mask_conflict",None)
    if pair.tier=="image_inconclusive" or pair.flat_or_byte_identical:
        return ("image_inconclusive",None)
    if reg is None:return ("register_unsupported",None)
    if shift != -reg:return ("image_register_contradiction",None)
    if shift not in SUPPORTED_SHIFTS:return ("verified_out_of_scope_shift",None)
    return ("confirmed_finite_mode",shift)


def scan_contiguous(pairs:list[PairEvidence])->dict:
    """Observed pair edges only. Unknown/conflict results break a mode run."""
    if not pairs:
        raise ValueError("empty finite source interval")
    for i,p in enumerate(pairs):
        if i and p.start_frame!=pairs[i-1].start_frame+1:
            raise ValueError("missing/reordered/duplicate source edge; do not bridge gaps")
    classified=[classify_pair(p) for p in pairs]
    counts=Counter(tier for tier,shift in classified)
    segments=[]
    transitions=[]
    active=None
    for pair,(status,mode) in zip(pairs,classified):
        if status!="confirmed_finite_mode":
            if active is not None:segments.append(active);active=None
            continue
        if active is None:
            active={"shift_px":mode,"pair_start_first":pair.start_frame,
                    "pair_start_last":pair.start_frame,"observed_pair_count":1}
        elif active["shift_px"]==mode:
            active["pair_start_last"]=pair.start_frame
            active["observed_pair_count"]+=1
        else:
            transitions.append({
                "at_pair_start_frame":pair.start_frame,
                "from_shift_px":active["shift_px"],"to_shift_px":mode,
                "source_pair_witnesses_adjacent":True,
                "universal_physics_rule_proven":False
            })
            segments.append(active)
            active={"shift_px":mode,"pair_start_first":pair.start_frame,
                    "pair_start_last":pair.start_frame,"observed_pair_count":1}
    if active is not None:segments.append(active)
    return {
        "first_observed_pair_start":pairs[0].start_frame,
        "last_observed_pair_start":pairs[-1].start_frame,
        "observed_pair_count":len(pairs),
        "confirmed_pair_count":counts["confirmed_finite_mode"],
        "unverified_or_unqualified_pair_count":len(pairs)-counts["confirmed_finite_mode"],
        "pair_classification_counts":{k:counts[k] for k in (
            "confirmed_finite_mode","image_inconclusive","confident_mask_conflict",
            "source_unverified","register_unsupported","image_register_contradiction",
            "verified_out_of_scope_shift")},
        "observed_mode_segments":segments,
        "adjacent_observed_mode_transitions":transitions,
        "predicts_missing_or_future_frames":False,
        "source_original_sprite_vehicle_camera_physics_or_ppu_dot_proven":False,
    }


def _require(record:dict,checks:dict)->None:
    for key,value in checks.items():
        if record.get(key)!=value:
            raise ValueError("published source-safe aggregate missing/changed: "+key)


def reconstruct_prior_aggregate_witness(stage360:dict,stage359:dict)->list[PairEvidence]:
    """Only a finite *projection* of archived aggregates, not new frame-level reanalysis.

    Aggregate files do not specify which 3/4 vs 4/4 tier applies to every pair;
    label these edges archived_qualified_unpartitioned, never invent a tier.
    """
    if not isinstance(stage360,dict) or not isinstance(stage359,dict):
        raise ValueError("two archived source-safe JSON objects required")
    _require(stage360,{
        "format":STAGE360_FORMAT,"stage":360,"boundary_qualified_original_shift_register_matches":3,
        "boundary_confident_mask_conflicts":0,"boundary_inconclusive":0,
        "boundary_original_scroll_register_unsupported":0,
        "boundary_original_register_contradictions":0,
        "stage350_consecutive_original_image_pairs":24,
        "stage350_strict_four_roi_pairs":19,"stage350_qualified_three_roi_pairs":5,
        "stage350_confident_conflicts":0,"stage350_inconclusive":0,
        "stage350_qualified_original_image_scroll_matches":24,
        "stage350_first_four_pixel_image_shift_pair":"527–528",
        "stage350_pairs_first_shift_three":{"first_pair_start":520,"last_pair_start":526,"count":7},
        "stage350_pairs_next_shift_four":{"first_pair_start":527,"last_pair_start":543,"count":17},
        "original_source_manifest_member_sha_checks":118,
        "stage355_previous_scientific_failed_conclusion_unchanged":True,
        "stage357_five_ambiguous_image_pairs_preserved":True,
        "copyrighted_source_ROM_FM2_original_pixels_original_CPU_PPU_traces_public":False,
    })
    _require(stage359,{
        "format":STAGE359_FORMAT,"stage":359,"original_source_frames":[545,559],
        "adjacent_source_image_pairs":14,
        "strict_four_environment_band_confident_image_shift_pairs":9,
        "qualified_three_environment_band_confident_image_shift_pairs":5,
        "conflicting_confident_band_pairs":0,"image_inconclusive_pairs":0,
        "all_qualified_image_source_vertical_shift_pixels":4,
        "all_qualified_independent_first_ppu_2005_vertical_mod240_step":-4,
        "qualified_image_source_register_matches":14,
        "qualified_image_source_register_contradictions":0,
        "qualified_without_authenticated_source_register_pair":0,
        "original_source_members_individually_sha_verified":22,
        "previous_stage355_failed_source_motion_gate_unchanged":True,
        "previous_stage357_five_inconclusive_image_pairs_unchanged":True,
        "copyrighted_original_data_or_private_source_sha_public":False,
    })
    boundaries=stage360.get("boundary_pairs")
    if not isinstance(boundaries,list) or len(boundaries)!=3:
        raise ValueError("exactly three source-sealed original archive joins required")
    expected=[("519–520",3,-3),("544–545",4,-4),("559–560",5,-5)]
    for b,(edge,shift,step) in zip(boundaries,expected):
        if not isinstance(b,dict):
            raise ValueError("invalid original source boundary aggregate")
        _require(b,{"frame_pair":edge,"qualified_image_shift_px":shift,
                    "first_original_ppu_scroll_step_mod240":step,
                    "frozen_confidence":"strict_four_of_four","agrees":True})
    records=[]
    for i in range(519,560):
        if i==519 or i==544 or i==559:
            shift={519:3,544:4,559:5}[i]
            tier="strict_four_of_four";origin="stage360_cross_archive"
        elif 520<=i<=543:
            shift=3 if i<=526 else 4
            tier="archived_qualified_unpartitioned";origin="stage350_aggregate"
        else:
            shift=4;tier="archived_qualified_unpartitioned";origin="stage359_aggregate"
        records.append(PairEvidence(i,shift,tier,-shift,origin))
    return records


def bounded_model(stage360:dict,stage359:dict)->dict:
    rows=reconstruct_prior_aggregate_witness(stage360,stage359)
    envelope=scan_contiguous(rows)
    if envelope["observed_pair_count"]!=41 or envelope["confirmed_pair_count"]!=41:
        raise ValueError("historical source-safe finite witness invalid")
    if envelope["observed_mode_segments"]!=[
        {"shift_px":3,"pair_start_first":519,"pair_start_last":526,"observed_pair_count":8},
        {"shift_px":4,"pair_start_first":527,"pair_start_last":558,"observed_pair_count":32},
        {"shift_px":5,"pair_start_first":559,"pair_start_last":559,"observed_pair_count":1}]:
        raise ValueError("finite sequence differs from source-archived qualified observations")
    return {
        "format":"vpd_stage361_source_safe_bounded_scroll_mode_envelope_v1",
        "stage":361,
        "input_class":"reconstructed FROM previously public Stage359+Stage360 numeric aggregates only",
        "scientific_status":"retrospective engineering model, NOT independent original experiment",
        "window_observed_original_pair_starts":[519,559],
        "only_supported_observed_shifts_px":[3,4,5],
        "source_safe_original_archive_member_shas_not_present":True,
        "original_rom_fm2_pixels_cpu_ppu_rows_not_processed":True,
        "fixed_stage355_failed_source_gate_preserved":True,
        "fixed_stage357_five_inconclusive_pairs_preserved":True,
        **envelope,
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage360",type=Path,required=True)
    p.add_argument("--stage359",type=Path,required=True)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    try:
        for name in (args.stage360,args.stage359):
            if name.is_symlink() or not name.is_file():
                raise ValueError("missing source-safe aggregate")
        result=bounded_model(json.loads(args.stage360.read_text(encoding="utf8")),
                             json.loads(args.stage359.read_text(encoding="utf8")))
        body=json.dumps(result,indent=2,sort_keys=True)+"\n"
        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise ValueError("refuse to overwrite archived bounded envelope")
            with args.output.open("x",encoding="utf8") as out:
                out.write(body)
        else:
            print(body,end="")
    except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as e:
        p.exit(1,"VPD_STAGE361_FINITE_SOURCE_ENVELOPE_REJECTED: "+str(e)+"\n")


if __name__=="__main__":main()
