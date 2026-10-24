#!/usr/bin/env python3
"""Stage357: preregistered 405-419 original RGB transition diagnostic.

Source-only immutable window, four fixed environment regions, optional native
register corroboration. ROM-free tests exercise only fabricated observations.
No proprietary original source is read by public CI.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import audit_private_stage344_motion as motion
import audit_private_stage345_scroll_motion as scroll

FIRST, LAST = 405, 419
FRAMES = tuple(range(FIRST, LAST+1))
PALETTE_FRAMES = (405, 412, 419)
REGIONS = {
    "left_env_upper":(0,52,20,98),
    "left_env_lower":(0,52,98,175),
    "right_env_upper":(195,255,20,98),
    "right_env_lower":(195,255,98,175),
}
OFFSETS = tuple(range(-24,25))
MAX_ERROR, MIN_GAP = .16, .045


def classify_masks(scores:dict[str,tuple[int,float,float]])->tuple[str,int|None]:
    if set(scores) != set(REGIONS):
        raise ValueError("four original source masks mandatory")
    selected=[]
    for region in REGIONS:
        record=scores[region]
        if not isinstance(record,(tuple,list)) or len(record)!=3:
            raise ValueError("bad original band score")
        shift, error, gap=record
        if (type(shift) is not int or shift not in OFFSETS or
            type(error) not in (int,float) or type(gap) not in (int,float) or
            not (0<=error<=1 and 0<=gap<=1)):
            raise ValueError("invalid source band confidence")
        if error<=MAX_ERROR and gap>=MIN_GAP:
            selected.append(shift)
    if len(set(selected))>1:return "mask_conflict",None
    if len(selected)==4:return "strict_four_of_four",selected[0]
    if len(selected)==3:return "qualified_three_of_four",selected[0]
    return "image_inconclusive",None


def rgb_features(frames:list[bytes],width:int=256,height:int=240)->dict:
    if len(frames)!=15 or any(type(img) is not bytes or len(img)!=width*height*3 for img in frames):
        raise ValueError("15 complete source RGB images required")
    uniform=[img==img[:3]*(width*height) for img in frames]
    return {
        "rgb_frames":15,
        "flat_single_color_frames":sum(uniform),
        "unique_whole_rgb_frames":len(set(frames)),
        "identical_adjacent_rgb_pairs":sum(a==b for a,b in zip(frames,frames[1:])),
        "pairs_with_at_least_one_flat_frame":sum(a or b for a,b in zip(uniform,uniform[1:])),
        "pairs_with_both_nonflat_and_nonidentical":sum(
           not uniform[i] and not uniform[i+1] and frames[i]!=frames[i+1] for i in range(14)),
    }


def register_features(samples:list[tuple[bool,bool,bool]])->dict:
    """Each (CPU write present, native mask zero, verified first Y anchor)."""
    if len(samples)!=15 or any(
        not isinstance(x,tuple) or len(x)!=3 or any(type(v) is not bool for v in x)
        for x in samples):
        raise ValueError("15 strict source mask/write frame records required")
    return {
        "native_line_zero_anchors":15,
        "frames_missing_second_phase_cpu_write":sum(not a for a,b,c in samples),
        "native_line_zero_mask_zero_frames":sum(b for a,b,c in samples),
        "missing_write_and_zero_mask_frames":sum(not a and b for a,b,c in samples),
        "present_write_and_zero_mask_frames":sum(a and b for a,b,c in samples),
        "missing_write_and_nonzero_mask_frames":sum(not a and not b for a,b,c in samples),
        "verified_first_scroll_y_anchor_frames":sum(c for a,b,c in samples),
        "pairs_with_two_verified_first_scroll_y":sum(
            samples[i][2] and samples[i+1][2] for i in range(14)),
        "missing_write_implies_scroll_zero":False,
        "retained_ppu_scroll_proven":False,
    }


def summarize(image:dict,register:dict,pairs:list[tuple[str,int|None,int|None]])->dict:
    if image.get("rgb_frames")!=15 or register.get("native_line_zero_anchors")!=15 or len(pairs)!=14:
        raise ValueError("partial original scene transition source")
    out=Counter()
    for tier,shift,source_step in pairs:
        if tier not in ("mask_conflict","strict_four_of_four","qualified_three_of_four","image_inconclusive"):
            raise ValueError("unknown original source evidence tier")
        out[tier]+=1
        if tier in ("strict_four_of_four","qualified_three_of_four"):
            if type(shift) is not int or shift not in OFFSETS:raise ValueError("invalid qualified shift")
            if source_step is None:out["qualified_register_unsupported"]+=1
            elif type(source_step) is not int or not -119<=source_step<=119:
                raise ValueError("invalid source register step")
            elif shift == -source_step:out["qualified_register_matches"]+=1
            else:out["qualified_register_contradictions"]+=1
        elif shift is not None:
            raise ValueError("unqualified image displacement may not be imputed")
    return {
        "format":"vpd_stage357_original_transition_405_419_public_v1",
        "stage":357,
        "original_source_frame_window":[FIRST,LAST],
        "original_adjacent_pairs":14,
        **image,**register,
        "source_rgb_four_of_four_pairs":out["strict_four_of_four"],
        "source_rgb_three_of_four_pairs":out["qualified_three_of_four"],
        "source_rgb_mask_conflict_pairs":out["mask_conflict"],
        "source_rgb_inconclusive_pairs":out["image_inconclusive"],
        "qualified_register_matches":out["qualified_register_matches"],
        "qualified_register_contradictions":out["qualified_register_contradictions"],
        "qualified_register_unsupported":out["qualified_register_unsupported"],
        "source_motion_pairs_passed_without_register_provenance":False,
        "prior_stage355_failed_motion_result_changed":False,
        "hardware_ppu_dot_vehicle_camera_physics_proven":False,
        "public_original_raw_source_disclosed":False,
    }


def mismatch(left,right,region,dy):
    # Numpy arrays of 240x256x3, only used owner-locally (never original in CI).
    import numpy as np
    x0,x1,y0,y1=region
    lo=max(y0,y0-dy);hi=min(y1,y1-dy)
    if hi<=lo:return 1.
    return float(np.any(left[lo:hi,x0:x1]!=right[lo+dy:hi+dy,x0:x1],axis=2).mean())


def audit(root:Path,manifest:Path,*,manifest_sha:str,cpu_pin:str,native_pin:str)->dict:
    import numpy as np
    if root.is_symlink() or not root.is_dir() or manifest.is_symlink():
        raise ValueError("untrusted private replay path")
    motion.checked(manifest,manifest_sha,min_size=500,max_size=20000)
    m=json.loads(manifest.read_text(encoding="utf8"))
    if (m.get("format")!="vpd_stage344_original_consecutive_rgb_private_manifest_v1"
        or m.get("stage")!=357 or m.get("frames")!=list(FRAMES)
        or m.get("palette_frames")!=list(PALETTE_FRAMES)
        or m.get("newppu")!=0 or m.get("original_readonly") is not True):
        raise ValueError("original source manifest not correctly sealed")
    names={"COMPLETE.txt","stage335_ppu_latch_ram0d_events.tsv",
           "stage341_classic_refreshaddr.tsv","stage343_rgb_palette_probes.tsv"}
    names.update(f"stage343_rgb_{f:04d}.gd" for f in FRAMES)
    names.update(f"stage343_palette_{f:04d}.idx" for f in PALETTE_FRAMES)
    pins=m["sha256"]
    if set(pins)!=names or len(pins)!=22:
        raise ValueError("unexpected original source member names")
    for name,sha in pins.items():motion.checked(root/name,sha)
    if (pins["stage335_ppu_latch_ram0d_events.tsv"]!=cpu_pin or
        pins["stage341_classic_refreshaddr.tsv"]!=native_pin):
        raise ValueError("independent original complete-trace SHA changed")
    marker=set((root/"COMPLETE.txt").read_text(encoding="utf8").splitlines())
    if not {"rom_identity_verified=yes","fm2_readonly=yes","frames=261",
            "first_frame=380","last_frame=640"}<=marker:
        raise ValueError("read-only original movie witness incomplete")
    cpu=root/"stage335_ppu_latch_ram0d_events.tsv"
    native=root/"stage341_classic_refreshaddr.tsv"
    motion.verify_frame_anchors(cpu,"frame","frame_begin",380,640)
    motion.verify_frame_anchors(native,"core_frame_ordinal","core_frame_start",380,640)
    frames=[motion.read_frame(root/f"stage343_rgb_{f:04d}.gd",
                             pins[f"stage343_rgb_{f:04d}.gd"]) for f in FRAMES]
    pix={f:np.frombuffer(raw,np.uint8).reshape(240,256,3) for f,raw in zip(FRAMES,frames)}
    palette_points={};coverage=Counter()
    with (root/"stage343_rgb_palette_probes.tsv").open(newline="",encoding="utf8-sig") as handle:
        reader=csv.DictReader(handle,delimiter="\t")
        if reader.fieldnames!=["frame","x","y","r","g","b","palette_index"]:
            raise ValueError("source probe schema invalid")
        for rec in reader:
            f,x,y=(int(rec[k]) for k in ("frame","x","y"))
            rgb=[int(rec[k]) for k in ("r","g","b")]
            idx=int(rec["palette_index"])
            if (f not in pix or (x,y) not in motion.POINTS or (f,x,y) in palette_points
                or not all(0<=v<=255 for v in rgb+[idx]) or
                tuple(pix[f][y,x])!=tuple(rgb)):
                raise ValueError("original rgb/index probe mismatch")
            coverage[f]+=1;palette_points[f,x,y]=idx
    if len(palette_points)!=90 or any(coverage[f]!=6 for f in FRAMES):
        raise ValueError("90 original source cross-probes required")
    for f in PALETTE_FRAMES:
        plane=(root/f"stage343_palette_{f:04d}.idx").read_bytes()
        if len(plane)!=61440 or any(plane[y*256+x]!=palette_points[f,x,y]
                                    for x,y in motion.POINTS):
            raise ValueError("original full indexed palette mismatch")
    c=scroll.original_rows(cpu,columns=scroll.CPU_HEADER,
                           frame_column="frame",first=FIRST,last=LAST)
    n=scroll.original_rows(native,columns=scroll.NATIVE_HEADER,
                           frame_column="core_frame_ordinal",first=FIRST,last=LAST)
    register=[];source_y=[]
    for f in FRAMES:
        events=[r for r in c[f] if r["event"]=="ppu_bus_write"
                and r["ppu_toggle_before"]=="1"]
        native0=[r for r in n[f] if r["event"]=="legacy_line_start"
                 and r["legacy_scanline"]=="0"]
        if len(native0)!=1 or not native0[0]["ppu_mask"].isdecimal():
            raise ValueError("native classic scanline0 source incomplete")
        source_state=None
        if events:
            try:source_state=scroll.frame_scroll(c[f],n[f])["first_y"]
            except ValueError:source_state=None
        register.append((bool(events),int(native0[0]["ppu_mask"])==0,
                         source_state is not None))
        source_y.append(source_state)
    diagnostics=[]
    for i,f in enumerate(FRAMES[:-1]):
        a=pix[f];b=pix[f+1]
        scores={}
        for name,rect in REGIONS.items():
            ranked=sorted((mismatch(a,b,rect,dy),dy) for dy in OFFSETS)
            (best,shift),(runner,_)=ranked[:2]
            scores[name]=(shift,best,runner-best)
        tier,dy=classify_masks(scores)
        ya,yb=source_y[i],source_y[i+1]
        step=None
        if ya is not None and yb is not None and 0<=ya<240 and 0<=yb<240:
            raw_step=((yb-ya+120)%240)-120
            if raw_step!=-120:step=raw_step
        diagnostics.append((tier,dy,step))
    report=summarize(rgb_features(frames),register_features(register),diagnostics)
    report["original_source_members_independently_sha256_verified"]=22
    report["original_palette_index_planes_verified"]=3
    report["independent_original_rgb_palette_index_probes_verified"]=90
    report["complete_cpu_and_native_ppu_trace_pins_verified"]=True
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for opt in ("root","manifest","sealed-manifest-sha256","sealed-cpu-sha256","sealed-native-sha256"):
        p.add_argument("--"+opt,required=True,type=Path if opt in ("root","manifest") else str)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    try:
        result=audit(a.root,a.manifest,manifest_sha=a.sealed_manifest_sha256,
                     cpu_pin=a.sealed_cpu_sha256,native_pin=a.sealed_native_sha256)
        payload=json.dumps(result,indent=2,sort_keys=True)+"\n"
        if a.output:
            if a.output.exists() or a.output.is_symlink():
                raise ValueError("cannot replace private report")
            with a.output.open("x",encoding="utf8") as file:file.write(payload)
        else:print(payload,end="")
    except (OSError,ValueError,KeyError,TypeError,UnicodeError):
        p.exit(1,"VPD_STAGE357_ORIGINAL_EVIDENCE_INCONCLUSIVE\n")


if __name__=="__main__":main()
