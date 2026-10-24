#!/usr/bin/env python3
"""Stage358 exploratory original 405-419 render-onset diagnostic (not a new holdout).

Original image, original CPU/PPU trace rows, original hashes and ROM/movie
are read only from owner-private evidence; stdout is a non-reversible aggregate.
The already preregistered Stage357 nine source-qualified ZERO-pixel shifts and
five inconclusive transitions cannot be upgraded by this retrospective tool.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

FIRST,LAST=405,419
W,H=256,240
GD_HEADER=bytes((255,254,1,0,0,240,1,255,255,255,255))
REGIONS={
    "left_env_upper":(0,52,20,98),
    "left_env_lower":(0,52,98,175),
    "right_env_upper":(195,255,20,98),
    "right_env_lower":(195,255,98,175),
}


def rgb_from_gd(data:bytes)->bytes:
    if type(data) is not bytes or len(data)!=11+W*H*4 or data[:11]!=GD_HEADER or any(data[11::4]):
        raise ValueError("original FCEUX GD source encoding malformed")
    raw=data[11:]
    out=bytearray(W*H*3)
    out[0::3]=raw[1::4];out[1::3]=raw[2::4];out[2::3]=raw[3::4]
    return bytes(out)


def source_frame_features(image:bytes,*,width:int=W,height:int=H)->dict:
    if type(image) is not bytes or len(image)!=width*height*3 or width<=0 or height<=0:
        raise ValueError("native source RGB frame size invalid")
    return {"unique_colors":len({image[i:i+3] for i in range(0,len(image),3)}),
            "uniform":image==image[:3]*(width*height)}


def changed_pixels(previous:bytes,current:bytes,*,width:int=W,height:int=H,
                   rect:tuple[int,int,int,int]|None=None)->int:
    if any(type(p) is not bytes or len(p)!=width*height*3 for p in (previous,current)):
        raise ValueError("source RGB shape mismatch")
    x0,x1,y0,y1=rect if rect is not None else (0,width,0,height)
    if not (0<=x0<x1<=width and 0<=y0<y1<=height):
        raise ValueError("invalid ROI")
    changed=0
    for y in range(y0,y1):
        pos=3*(y*width+x0)
        for x in range(x0,x1):
            changed+=(previous[pos:pos+3]!=current[pos:pos+3])
            pos+=3
    return changed


def event_profile(cpu_events:list[str],native_line_zero_mask:int)->dict:
    if not isinstance(cpu_events,list) or any(type(x) is not str for x in cpu_events):
        raise ValueError("original CPU events must be named")
    if type(native_line_zero_mask) is not int or not 0<=native_line_zero_mask<=255:
        raise ValueError("native PPU line-zero source mask invalid")
    counts=Counter(cpu_events)
    return {"w2000":counts["W2000"],"w2006":counts["W2006"],
            "ppu_status_reads":counts["ppu_status_read"],
            "second_phase_writes":counts["ppu_bus_write"],
            "native_line_zero_mask_nonzero":native_line_zero_mask!=0}


def summarize(
    records:list[dict], *,first:int=FIRST, last:int=LAST
)->dict:
    if len(records)!=last-first+1 or first!=405 or last!=419:
        raise ValueError("15 consecutive owner-authenticated scene source frames needed")
    if [r.get("frame") for r in records]!=list(range(first,last+1)):
        raise ValueError("missing or reordered source frame")
    first_nonflat=next((r["frame"] for r in records if not r["uniform"]),None)
    if first_nonflat is None:
        raise ValueError("no original texture onset was observable")
    onset_pairs=[r["frame"] for r in records[1:] if r["delta_pixels"]>0]
    # These are descriptive correlations, not a new statistical hypothesis.
    all_band=[r["frame"] for r in records[1:] if r["regions_changing"]==4]
    extra=[r["frame"] for r in records if r["w2000"]==4 and
           r["w2006"]==14 and r["ppu_status_reads"]==4]
    if any(r["regions_changing"]<0 or r["regions_changing"]>4 or
           r["delta_pixels"]<0 or r["delta_pixels"]>W*H or
           r["unique_colors"]<1 or
           type(r["native_line_zero_mask_nonzero"]) is not bool for r in records):
        raise ValueError("invalid source numerics")
    return {
        "format":"vpd_stage358_original_405_419_posthoc_onset_diagnostic_public_v1",
        "stage":358,
        "scientific_status":"exploratory reanalysis of previously captured Stage357 original source",
        "original_source_frames":[FIRST,LAST],
        "first_nonflat_rgb_frame":first_nonflat,
        "uniform_prefix_frames":sum(r["frame"]<first_nonflat for r in records),
        "one_color_frames":sum(r["uniform"] for r in records),
        "distinct_complete_rgb_frames":len(set(r["image_sha"] for r in records)),
        "source_mask_nonzero_at_line0_frames":sum(r["native_line_zero_mask_nonzero"] for r in records),
        "whole_rgb_appearing_frame_changed_pixels":next(r["delta_pixels"] for r in records if r["frame"]==first_nonflat),
        "four_environment_region_change_frame_numbers":all_band,
        "four_environment_region_change_frame_count":len(all_band),
        "cpu_ppu_extra_write_and_status_read_frame_numbers":extra,
        "cpu_ppu_extra_write_and_status_read_frame_count":len(extra),
        "four_region_change_and_cpu_ppu_extra_event_overlap":len(set(extra)&set(all_band)),
        "all_cpu_ppu_extra_events_proven_cause_of_pixels":False,
        "prior_stage357_strict_zero_shift_qualified_pairs_modified":False,
        "prior_stage355_inconclusive_motion_gate_changed":False,
        "vehicle_speed_camera_road_collision_or_ppu_dots_proven":False,
        "raw_original_pixel_register_values_or_hashes_published":False,
    }


def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def authenticate(z:zipfile.ZipFile,manifest:dict,*,cpu_pin:str,native_pin:str)->None:
    if (manifest.get("format")!="vpd_stage344_original_consecutive_rgb_private_manifest_v1"
        or manifest.get("stage")!=357 or manifest.get("frames")!=list(range(FIRST,LAST+1))
        or manifest.get("palette_frames")!=[405,412,419]
        or manifest.get("original_readonly") is not True or manifest.get("newppu")!=0):
        raise ValueError("source manifest is not independently authenticated Stage357")
    pinned=manifest["sha256"]
    expected={"COMPLETE.txt","stage335_ppu_latch_ram0d_events.tsv",
              "stage341_classic_refreshaddr.tsv","stage343_rgb_palette_probes.tsv"}
    expected|={f"stage343_rgb_{f:04d}.gd" for f in range(FIRST,LAST+1)}
    expected|={f"stage343_palette_{f:04d}.idx" for f in (405,412,419)}
    if set(pinned)!=expected or len(expected)!=22:
        raise ValueError("22 exact Stage357 source components required")
    if (pinned["stage335_ppu_latch_ram0d_events.tsv"]!=cpu_pin or
        pinned["stage341_classic_refreshaddr.tsv"]!=native_pin):
        raise ValueError("independently sealed complete source CPU/PPU trace differs")
    if z.testzip() is not None:
        raise ValueError("owner-private original ZIP CRC failed")
    if any(k.lower().endswith((".nes",".fm2",".rom",".iso")) for k in z.namelist()):
        raise ValueError("original ROM/FM2 in derived witness ZIP")
    for name,digest in pinned.items():
        if _sha(z.read(name))!=digest:
            raise ValueError("owner-private source member digest differs")
    marker=set(z.read("COMPLETE.txt").decode("utf8").splitlines())
    if not {"rom_identity_verified=yes","fm2_readonly=yes","frames=261",
            "first_frame=380","last_frame=640"}<=marker:
        raise ValueError("original FCEUX source replay completion unverifiable")
    for name,frame_field,event_name in (
        ("stage335_ppu_latch_ram0d_events.tsv","frame","frame_begin"),
        ("stage341_classic_refreshaddr.tsv","core_frame_ordinal","core_frame_start")
    ):
        anchors=Counter()
        for row in csv.DictReader(io.StringIO(z.read(name).decode("utf8-sig")),delimiter="\t"):
            if row["event"]==event_name:
                anchors[int(row[frame_field])]+=1
        if len(anchors)!=261 or any(anchors[f]!=1 for f in range(380,641)):
            raise ValueError("261 original CPU/native source anchors not authenticated")


def audit(archive:Path,manifest:Path,*,manifest_pin:str,cpu_pin:str,native_pin:str)->dict:
    if any(p.is_symlink() or not p.is_file() for p in (archive,manifest)):
        raise ValueError("missing private source witness")
    raw_manifest=manifest.read_bytes()
    if _sha(raw_manifest)!=manifest_pin:
        raise ValueError("owner-private independent original manifest digest changed")
    m=json.loads(raw_manifest)
    with zipfile.ZipFile(archive,"r") as z:
        authenticate(z,m,cpu_pin=cpu_pin,native_pin=native_pin)
        image={f:rgb_from_gd(z.read(f"stage343_rgb_{f:04d}.gd")) for f in range(FIRST,LAST+1)}
        mask_by_frame=defaultdict(list);cpu_by_frame=defaultdict(list)
        for row in csv.DictReader(io.StringIO(z.read("stage341_classic_refreshaddr.tsv").decode("utf8-sig")),delimiter="\t"):
            f=int(row["core_frame_ordinal"])
            if FIRST<=f<=LAST and row["event"]=="legacy_line_start" and row["legacy_scanline"]=="0":
                mask_by_frame[f].append(int(row["ppu_mask"]))
        for row in csv.DictReader(io.StringIO(z.read("stage335_ppu_latch_ram0d_events.tsv").decode("utf8-sig")),delimiter="\t"):
            f=int(row["frame"])
            if FIRST<=f<=LAST:cpu_by_frame[f].append(row["event"])
        # Same source RGB/index sample and full indexed planes must stay independently consistent.
        probes=defaultdict(dict)
        for r in csv.DictReader(io.StringIO(z.read("stage343_rgb_palette_probes.tsv").decode("utf8")),delimiter="\t"):
            f,x,y=(int(r[k]) for k in ("frame","x","y"))
            rgb=bytes(int(r[k]) for k in ("r","g","b"))
            idx=int(r["palette_index"])
            if f not in image or not (0<=x<W and 0<=y<H and 0<=idx<=255):
                raise ValueError("invalid original RGB/index probe")
            if image[f][3*(y*W+x):3*(y*W+x)+3]!=rgb or (x,y) in probes[f]:
                raise ValueError("independent original RGB palette sample differs")
            probes[f][x,y]=idx
        if len(probes)!=15 or any(len(probes[f])!=6 for f in range(FIRST,LAST+1)):
            raise ValueError("source probe coverage incomplete")
        for f in (405,412,419):
            plane=z.read(f"stage343_palette_{f:04d}.idx")
            if len(plane)!=W*H or any(plane[y*W+x]!=idx for (x,y),idx in probes[f].items()):
                raise ValueError("original indexed plane crosscheck failed")
        records=[]
        for f in range(FIRST,LAST+1):
            if len(mask_by_frame[f])!=1:raise ValueError("native line0 PPU anchor incomplete")
            features=source_frame_features(image[f])
            prev=image[f-1] if f>FIRST else image[f]
            diff=changed_pixels(prev,image[f])
            bands=sum(changed_pixels(prev,image[f],rect=rect)>0 for rect in REGIONS.values())
            records.append({"frame":f,"image_sha":_sha(image[f]),**features,
                            "delta_pixels":diff,"regions_changing":bands,
                            **event_profile(cpu_by_frame[f],mask_by_frame[f][0])})
        result=summarize(records)
        result.update({
            "original_source_member_sha256_verified":22,
            "original_source_261_frame_cpu_native_ppu_anchors_verified":True,
            "original_indexed_palette_planes_verified":3,
            "original_rgb_index_probes_verified":90,
        })
        return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--sealed-manifest-sha256",required=True)
    p.add_argument("--sealed-cpu-sha256",required=True)
    p.add_argument("--sealed-native-sha256",required=True)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    try:
        result=audit(a.archive,a.manifest,manifest_pin=a.sealed_manifest_sha256,
                     cpu_pin=a.sealed_cpu_sha256,native_pin=a.sealed_native_sha256)
        body=json.dumps(result,indent=2,sort_keys=True)+"\n"
        if a.output:
            if a.output.exists() or a.output.is_symlink():
                raise ValueError("never overwrite source-derived result")
            a.output.write_text(body,encoding="utf8")
        else:print(body,end="")
    except (OSError,ValueError,KeyError,TypeError,UnicodeError,zipfile.BadZipFile,json.JSONDecodeError):
        p.exit(1,"VPD_STAGE358_OWNER_SOURCE_DIAGNOSTIC_INCONCLUSIVE\n")


if __name__=="__main__":main()
