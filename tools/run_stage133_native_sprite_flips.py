#!/usr/bin/env python3
"""Stage133 native pinned FCEUX asymmetric sprite H/V flip and XBuf proof."""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage129_oam_sprite_rom import make_rom, asymmetric_pattern
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

MODES=("none","horizontal","vertical","both")
MARKER="VPD_STAGE133_NATIVE_SPRITE_FLIP_PASS"
REJECTED="VPD_STAGE133_REJECTED_SPRITE_FLIP"
PATTERN=re.compile(
    r"^VPD_STAGE133_NATIVE_SPRITE_FLIP_PASS "
    r"mode=(none|horizontal|vertical|both) "
    r"row=(\d+) source_row=(\d+) samples=8 "
    r"patterns=((?:\d+,){7}\d+) xbuf=((?:\d+,){7}\d+) "
    r"invalid=0 actual_fceux_sprite_flips=yes synthetic_only=yes "
    r"original_game_flips_proven=no$", re.MULTILINE)
REJECT_PATTERN=re.compile(
    r"^VPD_STAGE133_REJECTED_SPRITE_FLIP "
    r"mode=(none|horizontal|vertical|both) "
    r"invalid=(\d+) row=(\d+) source_row=(\d+) "
    r"samples=8 synthetic_only=yes$", re.MULTILINE)


class NativeFlipError(ValueError):
    pass


def flags_for(mode):
    if mode not in MODES:
        raise NativeFlipError("Unknown native reflection mode")
    return (mode in ("horizontal","both"),
            mode in ("vertical","both"))


def reference(mode,source_row):
    horizontal,vertical=flags_for(mode)
    if type(source_row) is not int or not 0<=source_row<8:
        raise NativeFlipError("Invalid native source row")
    patterns=[asymmetric_pattern(source_row, 7-i if horizontal else i)
              for i in range(8)]
    colors=[128 | {1:0x1A,2:0x2B,3:0x2A}[pixel] for pixel in patterns]
    return patterns,colors


def verify(log,mode):
    flags_for(mode)
    if not isinstance(log,str) or log.count(MARKER)!=1 or REJECTED in log:
        raise NativeFlipError("Absent, duplicate or contradicted FCEUX flip witness")
    matches=list(PATTERN.finditer(log))
    if len(matches)!=1:
        raise NativeFlipError("Malformed real sprite CHR/XBuf certificate")
    actual,row,source_row,patterns,xbuf=matches[0].groups()
    row,source_row=map(int,(row,source_row))
    measured_patterns=list(map(int,patterns.split(",")))
    measured_colors=list(map(int,xbuf.split(",")))
    expected_patterns,expected_colors=reference(mode,source_row)
    if (actual!=mode or not 120<=row<=140 or
            measured_patterns!=expected_patterns or
            measured_colors!=expected_colors):
        raise NativeFlipError("Observed native sprite flip pixels contradict CHR source")
    return {"mode":mode,"scanline":row,"source_row":source_row,
            "patterns":measured_patterns,"xbuf":measured_colors,
            "samples":8,"native_flip_pixels_proven":True,
            "original_game_flips_proven":False}


def verify_rejection(log):
    if not isinstance(log,str) or log.count(REJECTED)!=1 or MARKER in log:
        raise NativeFlipError("Expected one native reject of forged flip flags")
    matches=list(REJECT_PATTERN.finditer(log))
    if len(matches)!=1:
        raise NativeFlipError("Malformed native reject marker")
    mode,invalid,row,source_row=matches[0].groups()
    if (mode!="horizontal" or int(invalid)<=0 or
            not 120<=int(row)<=140 or
            not 0<=int(source_row)<8):
        raise NativeFlipError("Failed to prove the wrong flip-flag mismatch")
    return {"rejected":True,"errors":int(invalid)}


def verify_sweep(results):
    if not isinstance(results,list) or [mode for mode,_ in results]!=list(MODES):
        raise NativeFlipError("Four reflected sprite modes required in order")
    a={mode:result for mode,result in results}
    baseline=a["none"]
    if (a["horizontal"]["source_row"]!=baseline["source_row"] or
            a["vertical"]["source_row"]+baseline["source_row"]!=7 or
            a["both"]["source_row"]!=a["vertical"]["source_row"] or
            len({r["scanline"] for r in a.values()})!=1):
        raise NativeFlipError("H/V reflection source rows or scanlines diverged")
    for mode,result in results:
        pat,col=reference(mode,result["source_row"])
        if (result["patterns"]!=pat or result["xbuf"]!=col or
                result["samples"]!=8 or
                result["native_flip_pixels_proven"] is not True or
                result["original_game_flips_proven"] is not False):
            raise NativeFlipError("Native sprite flip sweep missing evidence")
    return {"modes":4,"samples":32,"source_row":baseline["source_row"],
            "native_flip_pixels_proven":True,
            "original_game_flips_proven":False}


def execute(binary,rom,folder,mode,*,enabled=True,reject=False,timeout=35):
    flags_for(mode)
    if reject and not enabled:
        raise NativeFlipError("Negative control requires enabled observer")
    folder.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    env.update(backend_settings("xvfb",folder))
    for key in ("VPD_STAGE100_SYNTHETIC_SMOKE","VPD_STAGE102_STATUS_PROBE",
                "VPD_STAGE103_PPUSTATUS_READ_PROBE","VPD_STAGE104_EVENT_ORDER_PROBE",
                "VPD_STAGE105_PRECLEAR_PROBE","VPD_STAGE106_MMC3_CHR_PROBE",
                "VPD_STAGE107_BG_PIXEL_PROBE","VPD_STAGE108_BG_FETCH_PROBE",
                "VPD_STAGE109_CHR_TIMELINE_PROBE","VPD_STAGE111_BG_TILE_PROBE",
                "VPD_STAGE113_BG_PREFETCH_PROBE","VPD_STAGE114_PLANE_PAIR_PROBE",
                "VPD_STAGE115_SCANLINE_CARRY_PROBE","VPD_STAGE116_FINE_SCROLL_PROBE",
                "VPD_STAGE117_DYNAMIC_SCROLL_PROBE","VPD_STAGE118_TWO_SCROLL_PROBE",
                "VPD_STAGE119_NAMETABLE_PROBE"):
        env[key]="0"
    env["VPD_STAGE110_MIDFRAME_CHR_PROBE"]="1"
    env["VPD_STAGE124_QUADRANT_PROBE"]="0"
    env["VPD_STAGE129_SPRITE_PROBE"]="0"
    env["VPD_STAGE131_DUAL_PROBE"]="0"
    env["VPD_STAGE133_FLIP_MODE"]=mode
    env["VPD_STAGE133_FLIP_PROBE"]="1" if enabled else "0"
    env.pop("VPD_STAGE126_TARGET_QUADRANT",None)
    env.pop("VPD_STAGE127_BACKDROP",None)
    cmd=[str(Path(binary).resolve()),"--newppu","1","--sound","0",
         "--opengl","0","--no-config","1",str(Path(rom).resolve())]
    logfile=folder/"native.log"
    with logfile.open("wb") as stream:
        p=subprocess.Popen(cmd,cwd=folder,env=env,stdin=subprocess.DEVNULL,
                           stdout=stream,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+(timeout if enabled else 2)
        was_running=False
        try:
            while time.monotonic()<deadline:
                time.sleep(0.1)
                log=logfile.read_text(encoding="utf8",errors="replace")
                if enabled and (MARKER in log or REJECTED in log):
                    break
                if p.poll() is not None:
                    break
            was_running=p.poll() is None
        finally:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=4)
    log=logfile.read_text(encoding="utf8",errors="replace")
    if not enabled:
        if not was_running or MARKER in log or REJECTED in log:
            raise NativeFlipError("Disabled flip observer emitted evidence or emulator exited")
        return None
    try:
        return verify_rejection(log) if reject else verify(log,mode)
    except NativeFlipError as exc:
        errors=re.findall(r"VPD_STAGE133_REJECTED_SPRITE_FLIP [^\r\n]{0,200}",log)
        raise NativeFlipError(str(exc)+": "+(errors[-1] if errors else
                              categorize_exit(p.returncode,log))) from exc


def run(binary,temp):
    with tempfile.TemporaryDirectory(dir=temp) as name:
        root=Path(name)
        reports=[]
        for mode in MODES:
            h,v=flags_for(mode)
            rom=root/(mode+".nes")
            make_rom(rom,hflip=h,vflip=v,asymmetric_sprite=True)
            reports.append((mode,execute(binary,rom,root/mode,mode)))
        # One unchanged ROM falsely labelled H-flipped must be REJECTED
        # after all eight actual framebuffer pixels are sampled.
        negative=execute(binary,root/"none.nes",root/"bad_flip",
                         "horizontal",reject=True)
        execute(binary,root/"none.nes",root/"disabled","none",enabled=False)
    summary=verify_sweep(reports)
    if not negative["rejected"]:
        raise NativeFlipError("False flip negative control was not rejected")
    print("STAGE133_NATIVE_SPRITE_HV_FLIP_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes "
          "modes=none,horizontal,vertical,both samples=32 "
          "source_rows_reflected=yes actual_xbuf_verified=yes "
          "forged_hflip_control=rejected observer_off_control=clean "
          "original_game_flips_proven=no")
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_fceux",type=Path)
    parser.add_argument("private_temp",type=Path)
    args=parser.parse_args()
    run(args.native_fceux,args.private_temp)
