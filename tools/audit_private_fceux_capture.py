#!/usr/bin/env python3
"""Private FCEUX capture session preflight, never an original-stage proof.

By default read metadata, binary lengths and palette validity only.
With --require-logs, also parse the private FCEUX register/cycle TSV files.
DO NOT export PPU, RAM, images, raw traces or source ROM hashes.
Capture authenticity, scroll/camera mapping and collisions remain unknown.
"""
import argparse
import json
from pathlib import Path
import re

from audit_fceux_trace_alignment import verify_trace_alignment

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


def audit_directory(root,allow_incomplete=False,require_logs=False):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("private capture root must be an existing non-symlink directory")
    # FCEUX emits at least six digits; numeric frame order crosses width boundaries.
    metas=sorted(root.glob("frame_*.meta.txt"),
                 key=lambda path:(len(path.name),path.name))
    if not 1<=len(metas)<=512:
        raise ValueError("expected 1..512 capture metadata files")
    expected=set()
    frames=[]
    counter_samples=[]
    rom_hash=None
    cadence=None
    cap=None
    screen_mode=None
    capture_format=None
    trace_clock=None
    previous_frame=-1
    previous_events=-1
    previous_drops=-1
    incomplete=[]
    for metapath in metas:
        m=META_NAME.fullmatch(metapath.name)
        if not m:
            raise ValueError("capture filename is not frame_NUMBER.meta.txt")
        frame=int(m.group(1))
        if metapath.name!=f"frame_{frame:06d}.meta.txt":
            raise ValueError("noncanonical FCEUX frame filename")
        if frame<=previous_frame:
            raise ValueError("duplicate or out-of-order capture frame")
        previous_frame=frame
        meta=metadata(metapath)
        version=meta.get("format")
        if version not in (
            "fceux_ppu_snapshot_v3","fceux_ppu_snapshot_v4"
        ):
            raise ValueError("unsupported FCEUX capture schema")
        if capture_format is None:
            capture_format=version
        elif version!=capture_format:
            raise ValueError("mixed capture format versions in one session")
        if version=="fceux_ppu_snapshot_v4":
            clock=meta.get("cycle_trace_available")
            if clock not in ("yes","no"):
                raise ValueError("missing or invalid v4 CPU cycle trace availability")
            if meta.get("cycle_trace_counter_epoch")!="debugger_since_reset":
                raise ValueError("unexpected v4 CPU cycle counter epoch")
            if trace_clock is None:
                trace_clock=clock
            elif clock!=trace_clock:
                raise ValueError("mixed CPU cycle trace availability in one session")
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
        if version=="fceux_ppu_snapshot_v4" and observed>250000:
            raise ValueError("logged register count exceeds native FCEUX session cap")
        if observed<previous_events:
            raise ValueError("cumulative register writes decreased")
        previous_events=observed
        counter_samples.append((frame,observed))
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
    trace_report=(
        verify_trace_alignment(root,counter_samples,
                               None if trace_clock is None else trace_clock=="yes")
        if require_logs else
        {"register_trace_verified":False,"cpu_cycle_trace_verified":False,
         "verified_register_events":0}
    )
    return {
        **trace_report,
        "classification":("private ROM capture metadata and register trace consistency preflight only"
                          if require_logs else "private ROM capture metadata/length preflight only"),
        "capture_count":len(frames),
        "first_frame":frames[0],
        "last_frame":frames[-1],
        "screen_reference":screen_mode=="yes",
        "cycle_trace_available":None if trace_clock is None else trace_clock=="yes",
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
    p.add_argument("--require-logs",action="store_true",
                   help="verify actual private register TSV and CPU-cycle trace alignment")
    args=p.parse_args()
    try:
        report=audit_directory(args.private_directory,args.allow_incomplete,
                               args.require_logs)
    except (OSError,ValueError,UnicodeError) as exc:
        p.exit(1,"PRIVATE_FCEUX_CAPTURE_INCONCLUSIVE: "+str(exc)+"\n")
    print("PRIVATE_FCEUX_CAPTURE_PREFLIGHT_PASS")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
