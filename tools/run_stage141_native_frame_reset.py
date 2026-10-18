#!/usr/bin/env python3
"""Stage141 true two-frame FCEUX sprite overflow reset and XBuf proof."""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage141_frame_reset_rom import make_rom
from run_stage100_fceux_synthetic_smoke import (
    backend_settings,categorize_exit)

MODES=("eight_visible","nine_overflow")
PASS="VPD_STAGE141_NATIVE_FRAME_RESET_PASS"
REJECT="VPD_STAGE141_REJECTED_FRAME_RESET"
GOOD=re.compile(
    r"^VPD_STAGE141_NATIVE_FRAME_RESET_PASS "
    r"case=(eight_visible|nine_overflow) "
    r"first_overflow=(yes|no) reset_before=(yes|no) reset_after=no "
    r"second_overflow=(yes|no) first_xbuf=(\d+) second_xbuf=(\d+) "
    r"samples=16 invalid=0 actual_ppu_reset_and_xbuf=yes "
    r"synthetic_only=yes original_game_frame_reset_proven=no$",
    re.MULTILINE)
BAD=re.compile(
    r"^VPD_STAGE141_REJECTED_FRAME_RESET "
    r"case=(eight_visible|nine_overflow) invalid=(\d+) "
    r"first_overflow=(yes|no) reset_before=(yes|no) "
    r"reset_after=(yes|no) second_overflow=(yes|no) "
    r"first_xbuf=(\d+) second_xbuf=(\d+) "
    r"samples=16 synthetic_only=yes$", re.MULTILINE)


class FrameResetError(ValueError):
    pass


def _int(text):
    parsed=int(text)
    if str(parsed)!=text:
        raise FrameResetError("Noncanonical numeric FCEUX proof")
    return parsed


def verify(log,mode):
    if mode not in MODES or not isinstance(log,str) or log.count(PASS)!=1 or REJECT in log:
        raise FrameResetError("Missing, duplicate or contradicted frame reset proof")
    matches=list(GOOD.finditer(log))
    if len(matches)!=1:
        raise FrameResetError("Malformed native reset witness")
    name,first,before,second,color_first,color_second=matches[0].groups()
    color_first,color_second=_int(color_first),_int(color_second)
    bit="yes" if mode=="nine_overflow" else "no"
    expected=143 if mode=="nine_overflow" else 170
    if (name!=mode or (first,before,second)!=(bit,bit,bit) or
            (color_first,color_second)!=(expected,expected)):
        raise FrameResetError("FCEUX pre-render reset/status or XBuf contradiction")
    return {"case":mode,"samples":16,"before_reset":before,
            "after_reset":"no","two_rendered_frames":True,
            "status_at_first":first,"status_at_second":second,
            "first_xbuf":color_first,"second_xbuf":color_second,
            "original_game_frame_reset_proven":False}


def verify_rejection(log):
    if not isinstance(log,str) or log.count(REJECT)!=1 or PASS in log:
        raise FrameResetError("No single genuine false-clean-case rejection")
    matches=list(BAD.finditer(log))
    if len(matches)!=1:
        raise FrameResetError("Malformed negative frame reset witness")
    mode,invalid,first,before,after,second,c0,c1=matches[0].groups()
    invalid,c0,c1=map(_int,(invalid,c0,c1))
    if (mode!="eight_visible" or invalid!=19 or
            (first,before,after,second)!=("yes","yes","no","yes") or
            (c0,c1)!=(143,143)):
        raise FrameResetError("False eight-sprite control lacks actual overflow")
    return {"rejected":True,"false_no_overflow":True}


def verify_sweep(reports):
    if (not isinstance(reports,list) or
            [name for name,_ in reports]!=list(MODES)):
        raise FrameResetError("Two native 2-frame ROM controls required")
    for mode,item in reports:
        expected=143 if mode=="nine_overflow" else 170
        if (item.get("case")!=mode or item.get("samples")!=16 or
                item.get("after_reset")!="no" or
                item.get("two_rendered_frames") is not True or
                item.get("first_xbuf")!=expected or
                item.get("second_xbuf")!=expected or
                item.get("original_game_frame_reset_proven") is not False):
            raise FrameResetError("Incomplete native before/after reset evidence")
    return {"cases":2,"samples":32,"native_frame_reset_proven":True,
            "original_game_frame_reset_proven":False}


def execute(binary,rom,folder,mode,*,enabled=True,reject=False,timeout=45):
    if mode not in MODES or (reject and not enabled):
        raise FrameResetError("Invalid synthetic frame-reset control")
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
    for key in ("VPD_STAGE124_QUADRANT_PROBE","VPD_STAGE129_SPRITE_PROBE",
                "VPD_STAGE131_DUAL_PROBE","VPD_STAGE133_FLIP_PROBE",
                "VPD_STAGE135_8X16_PROBE","VPD_STAGE137_NINE_PROBE",
                "VPD_STAGE139_TEMPORAL_PROBE"):
        env[key]="0"
    env["VPD_STAGE141_FRAME_RESET_PROBE"]="1" if enabled else "0"
    env["VPD_STAGE141_FRAME_RESET_CASE"]=mode
    env.pop("VPD_STAGE126_TARGET_QUADRANT",None)
    env.pop("VPD_STAGE127_BACKDROP",None)
    cmd=[str(Path(binary).resolve()),"--newppu","1","--sound","0",
         "--opengl","0","--no-config","1",str(Path(rom).resolve())]
    logpath=folder/"native.log"
    with logpath.open("wb") as target:
        process=subprocess.Popen(cmd,cwd=folder,env=env,
            stdin=subprocess.DEVNULL,stdout=target,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+(timeout if enabled else 2)
        alive=False
        try:
            while time.monotonic()<deadline:
                time.sleep(.1)
                log=logpath.read_text(encoding="utf8",errors="replace")
                if enabled and (PASS in log or REJECT in log):break
                if process.poll() is not None:break
            alive=process.poll() is None
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=4)
    log=logpath.read_text(encoding="utf8",errors="replace")
    if not enabled:
        if not alive or PASS in log or REJECT in log:
            raise FrameResetError("Disabled native frame observer yielded false proof")
        return None
    try:
        return verify_rejection(log) if reject else verify(log,mode)
    except FrameResetError as exc:
        details=re.findall(r"VPD_STAGE141_REJECTED_FRAME_RESET [^\r\n]{0,500}",log)
        diagnostic=re.findall(
            r"VPD_STAGE143_FRAME_PIXEL_DIAGNOSTIC [^\r\n]{0,500}",log)
        summary=details[-1] if details else categorize_exit(process.returncode,log)
        if diagnostic:
            summary+=" | "+diagnostic[-1]
        raise FrameResetError(str(exc)+": "+summary) from exc


def run(binary,temp):
    with tempfile.TemporaryDirectory(dir=temp) as td:
        root=Path(td)
        reports=[]
        for mode in MODES:
            rom=root/(mode+".nes")
            make_rom(rom,mode)
            reports.append((mode,execute(binary,rom,root/mode,mode)))
        wrong=execute(binary,root/"nine_overflow.nes",
                      root/"wrong_clean","eight_visible",reject=True)
        execute(binary,root/"eight_visible.nes",root/"observer_off",
                "eight_visible",enabled=False)
    result=verify_sweep(reports)
    if not wrong["false_no_overflow"]:
        raise FrameResetError("False clean control was not natively rejected")
    print("STAGE141_NATIVE_FRAME_OVERFLOW_RESET_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes cases=2 "
          "frames=4 samples=32 observed_pre_render_status_reset=yes "
          "overflow_reappears_next_frame=yes clean_frame_remains_clean=yes "
          "wrong_clean_control=rejected observer_off_control=clean "
          "original_game_multiframe_proven=no")
    return result


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("native_fceux",type=Path)
    cli.add_argument("private_temp",type=Path)
    args=cli.parse_args()
    run(args.native_fceux,args.private_temp)
