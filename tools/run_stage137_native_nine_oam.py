#!/usr/bin/env python3
"""Stage137 native FCEUX nine-OAM overflow, missing ninth pixel, controls."""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from make_stage137_nine_sprite_rom import MODES, make_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

PASS="VPD_STAGE137_NATIVE_NINE_OAM_PASS"
REJECT="VPD_STAGE137_REJECTED_NINE_OAM"
POSITIVE=re.compile(
    r"^VPD_STAGE137_NATIVE_NINE_OAM_PASS "
    r"case=(eight_visible|nine_overflow|ninth_offscreen|nine_8x16) "
    r"row=(\d+) eval_row=(\d+) count=8 overflow=(yes|no) "
    r"xbuf=(\d+) samples=8 invalid=0 observed_oam_and_xbuf=yes "
    r"synthetic_only=yes original_game_overflow_proven=no$",re.MULTILINE)
NEGATIVE=re.compile(
    r"^VPD_STAGE137_REJECTED_NINE_OAM "
    r"case=(eight_visible|nine_overflow|ninth_offscreen|nine_8x16) "
    r"invalid=(\d+) row=(\d+) eval_row=(\d+) count=(\d+) "
    r"overflow=(yes|no) xbuf=(\d+) samples=8 synthetic_only=yes$",
    re.MULTILINE)


class NativeNineError(ValueError):
    pass


def expectation(case):
    if case not in MODES:
        raise NativeNineError("Four controlled nine-OAM scenarios only")
    return ("yes" if case in ("nine_overflow","nine_8x16") else "no",
            170 if case=="eight_visible" else 143)


def _numbers(*values):
    if any(str(int(v))!=v for v in values):
        raise NativeNineError("Noncanonical numeric native evidence")
    return tuple(map(int,values))


def verify(log,case):
    overflow,color=expectation(case)
    if not isinstance(log,str) or log.count(PASS)!=1 or REJECT in log:
        raise NativeNineError("Missing, duplicate, contradicted native nine-OAM proof")
    matches=list(POSITIVE.finditer(log))
    if len(matches)!=1:
        raise NativeNineError("Malformed nine-OAM native evidence")
    observed,row,eval_row,bit,observed_color=matches[0].groups()
    row,eval_row,observed_color=_numbers(row,eval_row,observed_color)
    if (observed!=case or bit!=overflow or observed_color!=color or
            not 120<=row<=140 or not 120<=eval_row<=141 or
            abs(row-eval_row)>2 or
            (case=="nine_8x16" and row<132)):
        raise NativeNineError("OAM selection/overflow or real XBuf contradicts ROM")
    return dict(mode=case,row=row,eval_row=eval_row,xbuf=color,
                overflow=bit,samples=8,original_game_overflow_proven=False)


def verify_rejection(log):
    if not isinstance(log,str) or log.count(REJECT)!=1 or PASS in log:
        raise NativeNineError("Native wrong-scenario rejection absent or contradicted")
    found=list(NEGATIVE.finditer(log))
    if len(found)!=1:
        raise NativeNineError("Malformed negative native nine-OAM certificate")
    mode,invalid,row,eval_row,count,bit,color=found[0].groups()
    invalid,row,eval_row,count,color=_numbers(invalid,row,eval_row,count,color)
    if (mode!="eight_visible" or not 1<=invalid<=8 or
            not 120<=row<=140 or not 120<=eval_row<=141 or
            count!=8 or bit!="yes" or color!=143):
        raise NativeNineError("Wrong ROM was not visibly rejected as overflow")
    return dict(rejected=True,invalid=invalid,overflow=bit,xbuf=color)


def verify_sweep(items):
    if not isinstance(items,list) or [i for i,_ in items]!=list(MODES):
        raise NativeNineError("Complete four-mode native OAM sweep required")
    for mode,value in items:
        bit,color=expectation(mode)
        if (value.get("mode")!=mode or value.get("xbuf")!=color or
                value.get("overflow")!=bit or value.get("samples")!=8 or
                value.get("original_game_overflow_proven") is not False):
            raise NativeNineError("Native OAM overflow sweep incomplete")
    return dict(cases=4,samples=32,native_9_sprite_limit_proven=True,
                original_game_overflow_proven=False)


def execute(binary,rom,folder,mode,*,enabled=True,reject=False,timeout=40):
    expectation(mode)
    if reject and not enabled:
        raise NativeNineError("Reject needs enabled native observer")
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
                "VPD_STAGE135_8X16_PROBE"):
        env[key]="0"
    env["VPD_STAGE137_NINE_PROBE"]="1" if enabled else "0"
    env["VPD_STAGE137_NINE_CASE"]=mode
    env.pop("VPD_STAGE126_TARGET_QUADRANT",None)
    env.pop("VPD_STAGE127_BACKDROP",None)
    cmd=[str(Path(binary).resolve()),"--newppu","1","--sound","0",
         "--opengl","0","--no-config","1",str(Path(rom).resolve())]
    logfile=folder/"native.log"
    with logfile.open("wb") as sink:
        proc=subprocess.Popen(cmd,cwd=folder,env=env,stdin=subprocess.DEVNULL,
                              stdout=sink,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+(timeout if enabled else 2)
        live=False
        try:
            while time.monotonic()<deadline:
                time.sleep(.1)
                log=logfile.read_text(encoding="utf8",errors="replace")
                if enabled and (PASS in log or REJECT in log):break
                if proc.poll() is not None:break
            live=proc.poll() is None
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill();proc.wait(timeout=4)
    log=logfile.read_text(encoding="utf8",errors="replace")
    if not enabled:
        if not live or PASS in log or REJECT in log:
            raise NativeNineError("Disabled native observer emitted false report")
        return None
    try:
        return verify_rejection(log) if reject else verify(log,mode)
    except NativeNineError as exc:
        details=re.findall(r"VPD_STAGE137_REJECTED_NINE_OAM [^\r\n]{0,500}",log)
        raise NativeNineError(str(exc)+": "+(
            details[-1] if details else categorize_exit(proc.returncode,log))) from exc


def run(binary,temp):
    with tempfile.TemporaryDirectory(dir=temp) as td:
        root=Path(td)
        cases=[]
        for mode in MODES:
            rom=root/(mode+".nes")
            make_rom(rom,mode)
            cases.append((mode,execute(binary,rom,root/mode,mode)))
        control=execute(binary,root/"nine_overflow.nes",
                        root/"false_eight","eight_visible",reject=True)
        execute(binary,root/"eight_visible.nes",root/"off",
                "eight_visible",enabled=False)
    summary=verify_sweep(cases)
    if not control["rejected"]:
        raise NativeNineError("False eight-sprite claim was not rejected")
    print("STAGE137_NATIVE_NINE_SPRITE_OVERFLOW_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes cases=4 "
          "samples=32 first_eight_only=yes overflow_bit20_checked=yes "
          "ninth_sprite_absent_from_xbuf=yes wrong_case_control=rejected "
          "observer_off_control=clean original_game_overflow_proven=no")
    return summary


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("native_fceux",type=Path)
    cli.add_argument("private_temp",type=Path)
    a=cli.parse_args()
    run(a.native_fceux,a.private_temp)
