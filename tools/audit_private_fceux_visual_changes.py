#!/usr/bin/env python3
"""Locate candidate visual changes in a PRIVATE audited FCEUX storyboard.

Candidate changes are not known level boundaries. Does not emit game pixels,
individual palette indices, ROM checksums, or original artwork.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from audit_private_fceux_storyboard import audit, WIDTH, HEIGHT

MAX_SAMPLES = 64


def sample_palette(path, stride):
    data=path.read_bytes()
    if len(data)!=WIDTH*HEIGHT:
        raise ValueError("noncanonical private NES palette size")
    return bytes(data[y*WIDTH+x]
                 for y in range(0,HEIGHT,stride)
                 for x in range(0,WIDTH,stride))


def pair_metrics(first,second):
    if len(first)!=len(second) or not first:
        raise ValueError("invalid sampled private frames")
    n=len(first)
    different=sum(a!=b for a,b in zip(first,second))/n
    left,right=Counter(first),Counter(second)
    distribution=sum(abs(left.get(k,0)-right.get(k,0))
                     for k in left.keys()|right.keys())/(2*n)
    unknown=max(first.count(254),second.count(254))/n
    return different,distribution,unknown


def analyze(root,*,require_complete=True,stride=4,
            min_pixel_change=0.55,min_palette_shift=0.35,
            max_unknown=0.10):
    if not 1<=stride<=16:
        raise ValueError("palette sampling stride must be 1..16")
    for value in (min_pixel_change,min_palette_shift,max_unknown):
        if not isinstance(value,(int,float)) or not 0<=value<=1:
            raise ValueError("palette thresholds must be within 0..1")
    root=Path(root)
    integrity=audit(root,require_complete=require_complete)
    names=sorted(root.glob("frame_*.meta.txt"),
                 key=lambda p:int(p.name[6:-9]))
    if not 1<=len(names)<=MAX_SAMPLES:
        raise ValueError("invalid private storyboard sample count")
    frames=[int(path.name[6:-9]) for path in names]
    palette=[sample_palette(root/f"frame_{frame:06d}.pal.bin",stride)
             for frame in frames]
    candidates=[]
    uncertain_pairs=0
    compared=0
    for i in range(1,len(frames)):
        change,shift,unknown=pair_metrics(palette[i-1],palette[i])
        if unknown>max_unknown:
            uncertain_pairs+=1
            continue
        compared+=1
        if change>=min_pixel_change and shift>=min_palette_shift:
            candidates.append({
                "frame_before":frames[i-1],
                "frame_after":frames[i],
                "sampled_pixel_change_ratio":round(change,4),
                "sampled_palette_distribution_shift":round(shift,4),
                "interpretation":"candidate scene change; level identity unverified"
            })
    return {
        "classification":"private FCEUX visual-change candidates only",
        "complete_window_verified":integrity["complete_window_verified"],
        "sample_count":len(frames),
        "compared_frame_pairs":compared,
        "uncertain_pairs_due_to_unavailable_palette":uncertain_pairs,
        "candidate_count":len(candidates),
        "candidates":candidates,
        "original_level_boundaries_proven":False,
        "original_game_completion_proven":False,
        "next_step":"Review adjacent original frames privately; confirm stages using gameplay and PPU/RAM evidence."
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_storyboard",type=Path)
    parser.add_argument("--allow-partial",action="store_true")
    parser.add_argument("--stride",type=int,default=4)
    parser.add_argument("--pixel-threshold",type=float,default=0.55)
    parser.add_argument("--palette-threshold",type=float,default=0.35)
    args=parser.parse_args()
    try:
        report=analyze(
            args.private_storyboard,require_complete=not args.allow_partial,
            stride=args.stride,min_pixel_change=args.pixel_threshold,
            min_palette_shift=args.palette_threshold)
    except (OSError,ValueError,UnicodeError) as exc:
        parser.exit(1,"PRIVATE_VISUAL_CHANGE_INCONCLUSIVE: "+str(exc)+"\n")
    print("PRIVATE_VISUAL_CHANGE_PREFLIGHT_PASS")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
