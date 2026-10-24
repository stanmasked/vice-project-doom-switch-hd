#!/usr/bin/env python3
"""Stage360: owner-only ORIGINAL four-archive boundary continuity; retrospective.

GitHub CI uses only fabricated data through tests/test_stage360_bridge.py.
This executable requires four explicitly pinned owner-private original captures.
Never publish original pixels, traces, ROM/FM2 or owner-private digests.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np

import audit_private_stage345_scroll_motion as scroll

WINDOWS = {354:(495,519),350:(520,544),359:(545,559),351:(560,584)}
BOUNDARIES=((519,520),(544,545),(559,560))
ROIS = {
 "left_env_upper":(0,52,20,98),
 "left_env_lower":(0,52,98,175),
 "right_env_upper":(195,255,20,98),
 "right_env_lower":(195,255,98,175),
}
OFFSETS=range(-24,25)
MAX_ERROR=.16
MIN_GAP=.045
GD_HEADER=bytes([255,254,1,0,0,240,1,255,255,255,255])
PROBES=((0,0),(127,32),(128,120),(64,180),(192,200),(255,239))


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def decode_gd(data:bytes)->np.ndarray:
    if (type(data) is not bytes or len(data)!=11+256*240*4 or
        data[:11]!=GD_HEADER or any(data[11::4])):
        raise ValueError("original native RGB/GD data invalid")
    return np.frombuffer(data[11:],dtype=np.uint8).reshape(240,256,4)[:,:,1:4].copy()


def one_band(a:np.ndarray,b:np.ndarray,rect:tuple[int,int,int,int]):
    x0,x1,y0,y1=rect
    if a.shape!=(240,256,3) or b.shape!=(240,256,3):
        raise ValueError("native original 256x240x3 image shape required")
    ranked=[]
    for shift in OFFSETS:
        lo=max(y0,y0-shift)
        hi=min(y1,y1-shift)
        if hi<=lo:raise ValueError("empty original source ROI overlap")
        mismatch=np.any(a[lo:hi,x0:x1]!=b[lo+shift:hi+shift,x0:x1],axis=2).mean()
        ranked.append((float(mismatch),shift))
    ranked.sort(key=lambda z:(z[0],z[1]))
    (best,shift),(second,_)=ranked[:2]
    confident=(best<=MAX_ERROR and second-best>=MIN_GAP)
    return (shift,best,float(second-best),confident)


def classify_bands(rows:dict[str,tuple])->tuple[str,int|None]:
    if set(rows)!=set(ROIS):raise ValueError("four fixed source regions required")
    selected=[]
    for name in ROIS:
        shift,error,gap,confident=rows[name]
        if (type(shift) is not int or shift not in OFFSETS or
            type(error) not in (int,float) or not 0<=error<=1 or
            type(gap) not in (int,float) or not 0<=gap<=1 or
            type(confident) is not bool or
            confident!=(error<=MAX_ERROR and gap>=MIN_GAP)):
            raise ValueError("malformed confidence value")
        if confident:selected.append(shift)
    if len(set(selected))>1:return ("mask_conflict",None)
    if len(selected)==4:return ("strict_four_of_four",selected[0])
    if len(selected)==3:return ("qualified_three_of_four",selected[0])
    return ("image_inconclusive",None)


def signed_mod240_step(before:int,after:int)->int|None:
    if type(before) is not int or type(after) is not int or not 0<=before<240 or not 0<=after<240:
        return None
    delta=((after-before+120)%240)-120
    return delta if delta!=-120 else None


def classify_pair(a:np.ndarray,b:np.ndarray,ya:int|None,yb:int|None)->dict:
    if a.shape!=(240,256,3) or b.shape!=(240,256,3):
        raise ValueError("native image shape invalid")
    flat_a=bool(np.all(a==a[0,0]))
    flat_b=bool(np.all(b==b[0,0]))
    same=bool(np.array_equal(a,b))
    bands={k:one_band(a,b,v) for k,v in ROIS.items()}
    tier,shift=classify_bands(bands)
    if (flat_a or flat_b or same) and tier in ("strict_four_of_four","qualified_three_of_four"):
        tier="image_inconclusive";shift=None
    step=signed_mod240_step(ya,yb) if ya is not None and yb is not None else None
    if shift is None:
        compare="not_qualified"
    elif step is None:
        compare="register_unsupported"
    elif shift==-step:
        compare="matched"
    else:
        compare="contradiction"
    return {
        "tier":tier,"shift":shift,"register_step":step,
        "comparison":compare,"flat_endpoints":flat_a or flat_b,
        "identical_complete_rgb":same,
        "bands":{k:{"best_shift":v[0],"mismatch":round(v[1],7),
                    "gap":round(v[2],7),"confident":v[3]}
                 for k,v in bands.items()},
    }


def source_manifest_check(archive:Path,manifest:Path,manifest_sha:str,stage:int,
                          cpu_pin:str,native_pin:str)->dict:
    first,last=WINDOWS[stage];count=last-first+1
    if any(p.is_symlink() or not p.is_file() for p in (archive,manifest)):
        raise ValueError("owner private original evidence files missing")
    raw=manifest.read_bytes()
    if sha(raw)!=manifest_sha:raise ValueError("original manifest prior SHA changed")
    m=json.loads(raw)
    if (m.get("stage")!=stage or m.get("frames")!=list(range(first,last+1))
        or m.get("format")!="vpd_stage344_original_consecutive_rgb_private_manifest_v1"
        or m.get("original_readonly") is not True or m.get("newppu")!=0
        or len(m.get("palette_frames",[]))!=3):
        raise ValueError("not the independently fixed original source manifest")
    source={"COMPLETE.txt","stage335_ppu_latch_ram0d_events.tsv",
            "stage341_classic_refreshaddr.tsv","stage343_rgb_palette_probes.tsv"}
    source.update(f"stage343_rgb_{f:04d}.gd" for f in range(first,last+1))
    source.update(f"stage343_palette_{f:04d}.idx" for f in m["palette_frames"])
    pinned=m["sha256"]
    if set(pinned)!=source or len(pinned)!=count+7 or (
      pinned["stage335_ppu_latch_ram0d_events.tsv"]!=cpu_pin or
      pinned["stage341_classic_refreshaddr.tsv"]!=native_pin):
        raise ValueError("original 22/32 source member or independent full trace pins differ")
    with zipfile.ZipFile(archive,"r") as z:
        names=z.namelist()
        if z.testzip() is not None or any(n.lower().endswith((".nes",".fm2",".rom",".iso")) for n in names):
            raise ValueError("source archive corrupt or contains original ROM/movie")
        if len(set(names))!=len(names):raise ValueError("duplicate original ZIP member")
        for name,digest in pinned.items():
            if sha(z.read(name))!=digest:raise ValueError("one original indexed source member SHA changed")
        marker=set(z.read("COMPLETE.txt").decode("utf8").splitlines())
        if not {"rom_identity_verified=yes","fm2_readonly=yes","frames=261",
                "first_frame=380","last_frame=640"}<=marker:
            raise ValueError("readonly FCEUX original movie replay not sealed")
        stream_cpu=z.read("stage335_ppu_latch_ram0d_events.tsv").decode("utf8-sig")
        stream_ppu=z.read("stage341_classic_refreshaddr.tsv").decode("utf8-sig")
        for stream,col,anchor in ((stream_cpu,"frame","frame_begin"),
                                  (stream_ppu,"core_frame_ordinal","core_frame_start")):
            counts=Counter(int(r[col]) for r in csv.DictReader(io.StringIO(stream),delimiter="\t")
                           if r["event"]==anchor)
            if len(counts)!=261 or any(counts[f]!=1 for f in range(380,641)):
                raise ValueError("full original 261-frame CPU/PPU frame anchors missing")
        images={f:decode_gd(z.read(f"stage343_rgb_{f:04d}.gd")) for f in range(first,last+1)}
        samples=defaultdict(dict)
        for r in csv.DictReader(io.StringIO(z.read("stage343_rgb_palette_probes.tsv").decode("utf8-sig")),delimiter="\t"):
            f,x,y=map(int,(r["frame"],r["x"],r["y"]))
            rgb=tuple(map(int,(r["r"],r["g"],r["b"])))
            idx=int(r["palette_index"])
            if (f not in images or (x,y) not in PROBES or not 0<=idx<256
                or (x,y) in samples[f] or tuple(images[f][y,x])!=rgb):
                raise ValueError("original RGB/index probe mismatch")
            samples[f][x,y]=idx
        if len(samples)!=count or any(len(samples[f])!=6 for f in images):
            raise ValueError("original 6-per-frame source sample coverage not authenticated")
        for frame in m["palette_frames"]:
            plane=z.read(f"stage343_palette_{frame:04d}.idx")
            if len(plane)!=256*240 or any(plane[y*256+x]!=idx for (x,y),idx in samples[frame].items()):
                raise ValueError("source full indexed palette plane mismatch")
    return {"stage":stage,"range":[first,last],"images":images,
            "cpu":stream_cpu,"native":stream_ppu,"verified_source_members":len(pinned)}


def original_scroll_by_frame(cpu:str,native:str,required:list[int])->dict[int,int|None]:
    c=defaultdict(list);n=defaultdict(list)
    reader=csv.DictReader(io.StringIO(cpu),delimiter="\t")
    if reader.fieldnames!=list(scroll.CPU_HEADER):raise ValueError("wrong CPU original source schema")
    for r in reader:
        frame=int(r["frame"])
        if frame in required:c[frame].append(r)
    reader=csv.DictReader(io.StringIO(native),delimiter="\t")
    if reader.fieldnames!=list(scroll.NATIVE_HEADER):raise ValueError("wrong native original source schema")
    for r in reader:
        frame=int(r["core_frame_ordinal"])
        if frame in required:n[frame].append(r)
    result={}
    for f in required:
        try:result[f]=scroll.frame_scroll(c[f],n[f])["first_y"]
        except ValueError:result[f]=None
    return result


def summarize(joins:list[dict],within:list[dict],*,verified_original_members:int)->dict:
    if len(joins)!=3 or len(within)!=24:
        raise ValueError("three source cross-archive joins + 24 Stage350 pairs required")
    valid={"strict_four_of_four","qualified_three_of_four","image_inconclusive","mask_conflict"}
    out={"format":"vpd_stage360_cross_archive_retrospective_original_continuity_public_v1",
         "stage":360,"scientific_category":"posthoc join of already captured original source, NOT virgin holdout",
         "boundary_pairs_checked":3,"stage350_within_pairs_checked":24,
         "source_original_members_sha256_checked_across_all_archives":verified_original_members,
         "original_prior_stages_changed":False,
         "new_original_unseen_rgb_frames_captured":0,
         "stage355_inconclusive_failed_gate_changed":False,
         "stage357_five_inconclusive_image_pairs_changed":False,
         "original_rom_fm2_pixels_full_source_traces_or_private_hashes_on_public_github":False,
         "camera_vehicle_speed_law_physics_collision_hardware_ppu_dot_verified":False}
    for prefix,data in (("boundary",joins),("stage350_within",within)):
        for d in data:
            if d["tier"] not in valid or d["comparison"] not in (
                "matched","contradiction","register_unsupported","not_qualified"):
                raise ValueError("unknown original source pair evidence status")
            if d["comparison"]=="matched" and d["tier"] not in (
                 "strict_four_of_four","qualified_three_of_four"):
                raise ValueError("unsupported result promoted to match")
        for key in ("strict_four_of_four","qualified_three_of_four","image_inconclusive","mask_conflict"):
            out[f"{prefix}_{key}"]=sum(d["tier"]==key for d in data)
        for key in ("matched","contradiction","register_unsupported","not_qualified"):
            out[f"{prefix}_register_{key}"]=sum(d["comparison"]==key for d in data)
        out[f"{prefix}_qualified_image_shift_histogram"]={
            str(k):v for k,v in sorted(Counter(d["shift"] for d in data if d["shift"] is not None).items())}
    return out


def audit(config:dict)->tuple[dict,dict]:
    if set(config)!={"sources","sealed_cpu_sha256","sealed_native_sha256"} or (
        set(config["sources"])!={"354","350","359","351"}):
        raise ValueError("four exact original source archive inputs required")
    cpu_pin=config["sealed_cpu_sha256"];ppu_pin=config["sealed_native_sha256"]
    if not (isinstance(cpu_pin,str) and isinstance(ppu_pin,str)
       and len(cpu_pin)==64 and len(ppu_pin)==64):
        raise ValueError("owner-private independent original trace pins missing")
    sources={}
    for st in (354,350,359,351):
        item=config["sources"][str(st)]
        if set(item)!={"archive","manifest","manifest_sha256"}:
            raise ValueError("unsealed source archive config")
        sources[st]=source_manifest_check(Path(item["archive"]),Path(item["manifest"]),
            item["manifest_sha256"],st,cpu_pin,ppu_pin)
    if len({s["cpu"] for s in sources.values()})!=1 or len({s["native"] for s in sources.values()})!=1:
        raise ValueError("four independently captured CPU/PPU originals do not match")
    all_frames=list(range(495,585))
    y=original_scroll_by_frame(sources[350]["cpu"],sources[350]["native"],all_frames)
    owner_by_frame={f:s["images"][f] for s in sources.values() for f in s["images"]}
    if set(owner_by_frame)!=set(all_frames):raise ValueError("original 90-frame source join incomplete")
    joins=[]
    for lo,hi in BOUNDARIES:
        record=classify_pair(owner_by_frame[lo],owner_by_frame[hi],y[lo],y[hi])
        joins.append({"from":lo,"to":hi,**record})
    within=[]
    for lo in range(520,544):
        record=classify_pair(owner_by_frame[lo],owner_by_frame[lo+1],y[lo],y[lo+1])
        within.append({"from":lo,"to":lo+1,**record})
    result=summarize(joins,within,verified_original_members=sum(s["verified_source_members"] for s in sources.values()))
    return result,{"format":"vpd_stage360_owner_private_pair_diagnostics_v1",
                   "boundary_details":joins,"stage350_within_details":within,
                   "full_original_source_authentication_passed":True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-config",type=Path,required=True)
    p.add_argument("--private-aggregate",type=Path,required=True)
    p.add_argument("--private-details",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.private_config.is_symlink() or not a.private_config.is_file():
            raise ValueError("private source config unavailable")
        result,details=audit(json.loads(a.private_config.read_text(encoding="utf8")))
        for path,data in ((a.private_aggregate,result),(a.private_details,details)):
            if path.exists() or path.is_symlink():raise ValueError("never overwrite original analysis output")
            with path.open("x",encoding="utf8") as stream:
                stream.write(json.dumps(data,indent=2,sort_keys=True)+"\n")
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile,
            json.JSONDecodeError):
        p.exit(1,"VPD_STAGE360_OWNER_PRIVATE_CROSS_ARCHIVE_INCONCLUSIVE\n")


if __name__=="__main__":main()
