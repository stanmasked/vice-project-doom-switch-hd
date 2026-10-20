#!/usr/bin/env python3
"""Private FCEUX capture session preflight, never an original-stage proof.

Read metadata and binary lengths only (plus palette byte validity).
DO NOT export PPU, RAM, images, palette content or source ROM hashes.
Capture authenticity, scroll/camera mapping and collisions remain unknown.
"""
import argparse
import json
from pathlib import Path
import re

META_NAME=re.compile(r"^frame_([0-9]{6,9})\.meta\.txt$")
HEX32=re.compile(r"^[0-9a-fA-F]{32}$")
VALID_SCREEN_PALETTE=set(range(64)) | {254}
DATA_SUFFIXES=(
    ".ppu.bin",".ram.bin",".screen.rgb.bin",".screen.pal.bin"
)


def metadata(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("metadata must be a regular local file")
    if path.stat().st_size>32768:
        raise ValueError("oversize capture metadata")
    result={}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("malformed metadata row in "+path.name)
        k,v=line.split("=",1)
        if not k or k in result:
            raise ValueError("missing/duplicate metadata key in "+path.name)
        result[k]=v
    return result


def integer(meta,key,lo,hi):
    value=meta.get(key)
    if value is None or not re.fullmatch(r"0|[1-9][0-9]*",value):
        raise ValueError("invalid integer metadata: "+key)
    parsed=int(value)
    if not lo<=parsed<=hi:
        raise ValueError("metadata range violation: "+key)
    return parsed


def regular_file_size(path,size):
    if path.is_symlink() or not path.is_file() or path.stat().st_size!=size:
        raise ValueError("missing, linked, or bad length: "+path.name)


def audit_directory(root,allow_incomplete=False):
    root=Path(root)
    if not root.is_dir():
        raise ValueError("private local capture directory is missing")
    metas=sorted(root.glob("frame_*.meta.txt"))
    if not 1<=len(metas)<=512:
        raise ValueError("expected 1..512 capture metadata files")
    expected=set()
    frames=[]
    rom_hash=None
    cadence=None
    cap=None
    screen_mode=None
    previous_frame=-1
    previous_events=-1
    previous_drops=-1
    incomplete=[]
    for metapath in metas:
        m=META_NAME.fullmatch(metapath.name)
        if not m:
            raise ValueError("capture filename is not frame_NUMBER.meta.txt")
        frame=int(m.group(1))
        if frame<=previous_frame:
            raise ValueError("duplicate or out-of-order capture frame")
        previous_frame=frame
        meta=metadata(metapath)
        if meta.get("format") not in (
            "fceux_ppu_snapshot_v3","fceux_ppu_snapshot_v4"
        ):
            raise ValueError("unsupported FCEUX capture schema")
        if integer(meta,"frame",0,999999999)!=frame:
            raise ValueError("source frame/metadata filename mismatch")
        rh=meta.get("rom_md5")
        if not isinstance(rh,str) or not HEX32.fullmatch(rh):
            raise ValueError("invalid FCEUX-provided ROM identity")
        if rom_hash is None:
            rom_hash=rh.lower()
        elif rh.lower()!=rom_hash:
            raise ValueError("different FCEUX ROM identities in same session")
        interval=integer(meta,"capture_interval",1,1200)
        limit=integer(meta,"capture_limit",1,512)
        if cadence is None:
            cadence,cap=interval,limit
        elif interval!=cadence or limit!=cap:
            raise ValueError("capture cadence or limit changed mid-session")
        if frame%interval:
            raise ValueError("frame violates recorded capture interval")
        if len(metas)>limit:
            raise ValueError("capture count exceeds recorded per-session limit")
        if meta.get("screen_reference") not in ("yes","no") or (
            meta.get("screen_size")!="256x240"
        ):
            raise ValueError("missing native FCEUX screen reference contract")
        if screen_mode is None:
            screen_mode=meta["screen_reference"]
        elif screen_mode!=meta["screen_reference"]:
            raise ValueError("mixed screen capture modes in one session")
        drops=integer(meta,"dropped_register_writes",0,10**9)
        completeness=meta.get("register_log_complete")
        if completeness not in ("yes","no") or (
            (drops==0)!=(completeness=="yes")
        ):
            raise ValueError("contradictory capture register completeness")
        if drops<previous_drops:
            raise ValueError("cumulative dropped-register counter decreased")
        previous_drops=drops
        if screen_mode=="no" and integer(
            meta,"invalid_screen_palette_values",0,256*240
        )!=0:
            raise ValueError("screen capture disabled but unavailable palette counter nonzero")
        observed=integer(meta,"logged_register_writes",0,10**9)
        if observed<previous_events:
            raise ValueError("cumulative register writes decreased")
        previous_events=observed
        if drops:
            incomplete.append(frame)
        prefix=root/("frame_"+m.group(1))
        expected.add(metapath.name)
        for suffix,size in ((".ppu.bin",16384),(".ram.bin",2048)):
            name=prefix.name+suffix
            regular_file_size(root/name,size)
            expected.add(name)
        if screen_mode=="yes":
            rgb=prefix.name+".screen.rgb.bin"
            pal=prefix.name+".screen.pal.bin"
            regular_file_size(root/rgb,256*240*3)
            regular_file_size(root/pal,256*240)
            expected.update((rgb,pal))
            raw=(root/pal).read_bytes()
            if any(byte not in VALID_SCREEN_PALETTE for byte in raw):
                raise ValueError("invalid NES palette index in "+pal)
            missing=integer(meta,"invalid_screen_palette_values",0,256*240)
            if raw.count(254)!=missing:
                raise ValueError("unavailable NES palette count mismatch")
        frames.append(frame)
    for path in root.iterdir():
        if (path.name.startswith("frame_") and
            (path.name.endswith(".meta.txt") or
             any(path.name.endswith(s) for s in DATA_SUFFIXES))
            and path.name not in expected):
            raise ValueError("orphan/unpaired frame file: "+path.name)
    if incomplete and not allow_incomplete:
        raise ValueError("incomplete register logs; use explicit --allow-incomplete")
    return {
        "classification":"private ROM capture metadata/length preflight only",
        "capture_count":len(frames),
        "first_frame":frames[0],
        "last_frame":frames[-1],
        "screen_reference":screen_mode=="yes",
        "all_register_logs_complete":not bool(incomplete),
        "incomplete_frame_count":len(incomplete),
        "fceux_rom_identity_consistent":True,
        "private_capture_authenticity_proven":False,
        "actual_first_stage_proven":False,
        "camera_scroll_measured":False,
        "first_stage_geometry_recovered":False,
        "next_step":"Privately verify stage and independent camera/scroll provenance, then assemble map manifest."
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_directory",type=Path)
    p.add_argument("--allow-incomplete",action="store_true")
    args=p.parse_args()
    try:
        report=audit_directory(args.private_directory,args.allow_incomplete)
    except (OSError,ValueError,UnicodeError) as exc:
        p.exit(1,"PRIVATE_FCEUX_CAPTURE_INCONCLUSIVE: "+str(exc)+"\n")
    print("PRIVATE_FCEUX_CAPTURE_PREFLIGHT_PASS")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
