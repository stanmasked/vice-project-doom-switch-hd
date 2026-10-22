#!/usr/bin/env python3
"""Strict private FCEUX 321-frame raw CPU $2005 writer witness audit.

All full event tables remain on the owner's machine. Public output
includes counts and booleans only. CPU writes != effective PPU scroll.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re

NUM=re.compile(r"(?:0|[1-9][0-9]*)\Z")
HEX4=re.compile(r"[0-9A-F]{4}\Z")
HEX2=re.compile(r"[0-9A-F]{2}\Z")
START,STOP=600,920
PCS=("E8EC","E8F1","E369","E36C")
ANCHORS={600:(79,79),744:(136,134),800:(144,139),920:(24,19)}
W_FIELDS=["frame","ordinal","pc","value","cycle"]
R_FIELDS=["frame","ram_0d","ppu_2005_writes"]
C_FIELDS={"format","first_observed_frame","last_observed_frame",
          "frame_gaps","frames_sampled","cpu_writer_events",
          "registerwrite_2005_events","postframe_ram_samples",
          "movie_frames","rom_identity_verified","movie_readonly_verified"}

def _input(path:Path,maxsize=128*1024):
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=maxsize:
        raise ValueError("missing, linked, empty or oversized private report")
    return path

def num(s,what):
    if not isinstance(s,str) or not NUM.fullmatch(s):
        raise ValueError("invalid decimal "+what)
    return int(s)

def hexn(s,pat,what):
    if not isinstance(s,str) or not pat.fullmatch(s):
        raise ValueError("invalid source hex "+what)
    return int(s,16)

def rows(path:Path,columns:list[str],expected:int):
    with _input(path).open("r",encoding="ascii",newline="") as f:
        table=csv.DictReader(f,delimiter="\t")
        if table.fieldnames!=columns:
            raise ValueError("invalid private source tabular schema")
        result=list(table)
    if len(result)!=expected:
        raise ValueError("private FCEUX source window incomplete")
    if any(set(x)!=set(columns) or any(v is None for v in x.values())
           for x in result):
        raise ValueError("malformed private source table row")
    return result

def completion(path:Path):
    result={}
    for line in _input(path,maxsize=8192).read_text("ascii").splitlines():
        k,sep,v=line.partition("=")
        if not sep or not k or not v or k in result:
            raise ValueError("malformed or duplicate completion field")
        result[k]=v
    if set(result)!=C_FIELDS or result["format"]!="private_road_ppu321_raw_v1":
        raise ValueError("private FCEUX completion schema mismatch")
    if (num(result["first_observed_frame"],"first frame") not in (0,1) or
        num(result["last_observed_frame"],"last frame")!=STOP or
        num(result["frame_gaps"],"frame gaps")!=0 or
        num(result["frames_sampled"],"samples")!=321 or
        num(result["cpu_writer_events"],"exec count")!=1284 or
        num(result["registerwrite_2005_events"],"port count")!=1284 or
        num(result["postframe_ram_samples"],"ram count")!=321 or
        num(result["movie_frames"],"movie length")<=STOP or
        result["rom_identity_verified"]!="yes" or
        result["movie_readonly_verified"]!="yes"):
        raise ValueError("private FCEUX completion attestation incomplete")
    return result

def audit(directory:Path)->dict:
    completion(directory/"COMPLETE.txt")
    writers=rows(directory/"road_321_writers.tsv",W_FIELDS,321*4)
    ram=rows(directory/"road_321_postframe.tsv",R_FIELDS,321)
    last_cycle=None
    for index,row in enumerate(writers):
        frame=START+index//4
        ordinal=1+index%4
        if (num(row["frame"],"writer frame")!=frame or
            num(row["ordinal"],"writer ordinal")!=ordinal or
            row["pc"]!=PCS[ordinal-1] or
            not HEX4.fullmatch(row["pc"])):
            raise ValueError("missing/reordered private writer PC")
        value=hexn(row["value"],HEX2,"CPU accumulator")
        cycle=num(row["cycle"],"absolute CPU cycle")
        if value<0 or value>255 or cycle<0:
            raise ValueError("source event outside CPU range")
        if ordinal in (1,3,4) and value!=0:
            raise ValueError("original four-write accumulator pattern changed")
        if ordinal==2 and frame in ANCHORS and value!=ANCHORS[frame][0]:
            raise ValueError("published original second $2005 anchor changed")
        if ordinal==1:
            last_cycle=cycle
        elif ordinal==2:
            if cycle-last_cycle!=7:
                raise ValueError("early PC execution cycle gap not seven")
            last_cycle=cycle
        elif ordinal==3:
            if cycle<=last_cycle:
                raise ValueError("late phase occurs before early PC pair")
            last_cycle=cycle
        else:
            if cycle-last_cycle!=4:
                raise ValueError("late PC pair CPU gap not four")
    for index,row in enumerate(ram):
        frame=START+index
        if (num(row["frame"],"postframe RAM frame")!=frame or
            num(row["ppu_2005_writes"],"validated port writes")!=4):
            raise ValueError("postframe RAM/CPU writer count mismatch")
        val=hexn(row["ram_0d"],HEX2,"RAM $0D")
        if frame in ANCHORS and val!=ANCHORS[frame][1]:
            raise ValueError("published original RAM $0D anchor changed")
    return {
        "frame_start":START,"frame_stop":STOP,"frames_checked":321,
        "cpu_pc_callbacks":1284,"ppu_registerwrite_callbacks":1284,
        "postframe_ram_samples":321,"published_anchor_pairs_checked":4,
        "source_rom_md5_and_fm2_runtime_attested":True,
        "source_rom_fm2_sha256_join_verified":False,
        "absolute_cpu_clock_has_proven_frame_phase":False,
        "effective_ppu_scroll_proven":False,
        "camera_speed_proven":False,
        "road_collision_proven":False,
        "original_image_or_binary_included":False,
    }

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-dir",required=True,type=Path)
    p.add_argument("--summary",type=Path)
    opts=p.parse_args()
    result=audit(opts.private_dir)
    if opts.summary:
        repo=Path(__file__).resolve().parents[1]
        dest=opts.summary.expanduser().resolve()
        if dest==repo or repo in dest.parents or dest.exists():
            raise ValueError("sanitized summary must be NEW and outside public GitHub checkout")
        dest.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n","utf8")
    print("VPD_PRIVATE_ROAD_PPU321_RAW_AUDIT_PASS"
          " frames=321 exact_2005_writes=1284"
          " original_ppu_scroll_proven=no original_assets=no")

if __name__=="__main__":
    main()
