#!/usr/bin/env python3
"""Stage139 fail-closed native time-dependent 8x16 ninth-OAM XBuf proof."""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage138_temporal_oam_rom import MODES, make_rom, expected
from run_stage100_fceux_synthetic_smoke import backend_settings,categorize_exit

PASS="VPD_STAGE139_NATIVE_TEMPORAL_NINE_PASS"
REJECT="VPD_STAGE139_REJECTED_TEMPORAL_NINE"
PATTERN=re.compile(
    r"^VPD_STAGE139_NATIVE_TEMPORAL_NINE_PASS "
    r"case=(eight_stable|nine_late|seven_plus_late|nine_early) "
    r"top_source=124 bottom_source=132 top_sl=(\d+) bottom_sl=(\d+) "
    r"top_count=(\d+) bottom_count=(\d+) "
    r"top_overflow=(yes|no) bottom_overflow=(yes|no) "
    r"top_xbuf=(\d+) bottom_xbuf=(\d+) "
    r"samples=16 invalid=0 native_fceux_xbuf=yes synthetic_only=yes "
    r"original_game_temporal_oam_proven=no$",re.MULTILINE)
REJECTED=re.compile(
    r"^VPD_STAGE139_REJECTED_TEMPORAL_NINE "
    r"case=(eight_stable|nine_late|seven_plus_late|nine_early) "
    r"invalid=(\d+) top_count=(\d+) bottom_count=(\d+) "
    r"top_overflow=(yes|no) bottom_overflow=(yes|no) "
    r"top_xbuf=(\d+) bottom_xbuf=(\d+) "
    r"top_sl=(\d+) bottom_sl=(\d+) samples=16 synthetic_only=yes$",
    re.MULTILINE)

class TemporalNativeError(ValueError):
    pass


def _int_fields(*fields):
    if any(str(int(v))!=v for v in fields):
        raise TemporalNativeError("Noncanonical native numeric evidence")
    return tuple(map(int,fields))


def verify(log,mode):
    if mode not in MODES or not isinstance(log,str) or log.count(PASS)!=1 or REJECT in log:
        raise TemporalNativeError("Absent/duplicate/contradicted two-row native proof")
    found=list(PATTERN.finditer(log))
    if len(found)!=1:
        raise TemporalNativeError("Malformed native two-row PPU witness")
    (name,top_sl,bottom_sl,top_count,bottom_count,
     top_bit,bottom_bit,top_color,bottom_color)=found[0].groups()
    top_sl,bottom_sl,top_count,bottom_count,top_color,bottom_color=_int_fields(
        top_sl,bottom_sl,top_count,bottom_count,top_color,bottom_color)
    model=expected(mode)
    bit_top="yes" if model["upper"]["sprite_overflow_bit"] else "no"
    bit_bottom="yes" if model["lower"]["sprite_overflow_bit"] else "no"
    if (name!=mode or top_sl!=126 or bottom_sl!=134 or
            top_count!=model["upper"]["selected_count"] or
            bottom_count!=model["lower"]["selected_count"] or
            top_bit!=bit_top or bottom_bit!=bit_bottom or
            top_color!=model["xbuf_upper"] or
            bottom_color!=model["xbuf_lower"]):
        raise TemporalNativeError("Actual two-row OAM status or final XBuf mismatch")
    return {"case":mode,"samples":16,"top_count":top_count,
            "bottom_count":bottom_count,
            "top_overflow":top_bit,"bottom_overflow":bottom_bit,
            "top_xbuf":top_color,"bottom_xbuf":bottom_color,
            "original_game_temporal_oam_proven":False}


def verify_rejection(log):
    if not isinstance(log,str) or log.count(REJECT)!=1 or PASS in log:
        raise TemporalNativeError("Native wrong-mode rejection missing/duplicated")
    found=list(REJECTED.finditer(log))
    if len(found)!=1:
        raise TemporalNativeError("Malformed genuine negative OAM evidence")
    (mode,invalid,top_count,bottom_count,top_bit,bottom_bit,
     top_color,bottom_color,top_sl,bottom_sl)=found[0].groups()
    (invalid,top_count,bottom_count,top_color,bottom_color,
     top_sl,bottom_sl)=_int_fields(
        invalid,top_count,bottom_count,top_color,bottom_color,
        top_sl,bottom_sl)
    if (mode!="nine_late" or not 1<=invalid<=16 or
            (top_count,bottom_count)!=(7,8) or
            (top_bit,bottom_bit)!=("no","no") or
            (top_color,bottom_color)!=(143,170) or
            (top_sl,bottom_sl)!=(126,134)):
        raise TemporalNativeError("Wrong-model report lacks free-slot causal witness")
    return {"rejected":True,"contradiction":"free_slot_reveals_OAM8"}


def verify_sweep(items):
    if not isinstance(items,list) or [mode for mode,_ in items]!=list(MODES):
        raise TemporalNativeError("Native four-mode order or coverage missing")
    for mode,report in items:
        e=expected(mode)
        if (report.get("case")!=mode or report.get("samples")!=16 or
                report.get("top_count")!=e["upper"]["selected_count"] or
                report.get("bottom_count")!=e["lower"]["selected_count"] or
                report.get("top_xbuf")!=e["xbuf_upper"] or
                report.get("bottom_xbuf")!=e["xbuf_lower"] or
                report.get("original_game_temporal_oam_proven") is not False):
            raise TemporalNativeError("Incomplete two-row native OAM proof")
    return {"cases":4,"samples":64,"native_temporal_OAM_proven":True,
            "original_game_temporal_oam_proven":False}


def execute(binary,rom,folder,mode,*,enabled=True,reject=False,timeout=45):
    if mode not in MODES or (reject and not enabled):
        raise TemporalNativeError("Invalid native temporal control")
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
                "VPD_STAGE135_8X16_PROBE","VPD_STAGE137_NINE_PROBE"):
        env[key]="0"
    env["VPD_STAGE139_TEMPORAL_PROBE"]="1" if enabled else "0"
    env["VPD_STAGE139_TEMPORAL_CASE"]=mode
    env.pop("VPD_STAGE126_TARGET_QUADRANT",None)
    env.pop("VPD_STAGE127_BACKDROP",None)
    cmd=[str(Path(binary).resolve()),"--newppu","1","--sound","0",
         "--opengl","0","--no-config","1",str(Path(rom).resolve())]
    logpath=folder/"native.log"
    with logpath.open("wb") as stream:
        p=subprocess.Popen(cmd,cwd=folder,env=env,stdin=subprocess.DEVNULL,
                           stdout=stream,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+(timeout if enabled else 2)
        alive=False
        try:
            while time.monotonic()<deadline:
                time.sleep(.1)
                log=logpath.read_text(encoding="utf8",errors="replace")
                if enabled and (PASS in log or REJECT in log):break
                if p.poll() is not None:break
            alive=p.poll() is None
        finally:
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    p.kill();p.wait(timeout=4)
    log=logpath.read_text(encoding="utf8",errors="replace")
    if not enabled:
        if not alive or PASS in log or REJECT in log:
            raise TemporalNativeError("Disabled observer emitted false native marker")
        return None
    try:
        return verify_rejection(log) if reject else verify(log,mode)
    except TemporalNativeError as exc:
        records=re.findall(r"VPD_STAGE139_REJECTED_TEMPORAL_NINE [^\r\n]{0,600}",log)
        raise TemporalNativeError(str(exc)+": "+(
            records[-1] if records else categorize_exit(p.returncode,log))) from exc


def run(binary,temp):
    with tempfile.TemporaryDirectory(dir=temp) as td:
        root=Path(td)
        items=[]
        for mode in MODES:
            rom=root/(mode+".nes")
            make_rom(rom,mode)
            items.append((mode,execute(binary,rom,root/mode,mode)))
        negative=execute(binary,root/"seven_plus_late.nes",root/"wrong_nine",
                         "nine_late",reject=True)
        execute(binary,root/"eight_stable.nes",root/"disabled",
                "eight_stable",enabled=False)
    result=verify_sweep(items)
    if not negative["rejected"]:
        raise TemporalNativeError("Free-slot control was not rejected")
    print("STAGE139_NATIVE_TEMPORAL_NINE_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes cases=4 samples=64 "
          "two_source_rows=124,132 overflow_transition=yes "
          "eighth_slot_release_xbuf_visible=yes wrong_model_control=rejected "
          "observer_off_control=clean original_game_temporal_oam_proven=no")
    return result


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("native_fceux",type=Path)
    cli.add_argument("private_temp",type=Path)
    a=cli.parse_args()
    run(a.native_fceux,a.private_temp)
