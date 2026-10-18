#!/usr/bin/env python3
"""Stage151: source-level pre-render reset between CPU-OAM and next XBuf.

Explicit extra native certificate on top of independent Stage149 and
Stage150 source witnesses. Synthetic NES Mapper4 ROMs only.
"""
import argparse
import re
import tempfile
from pathlib import Path

from make_stage148_vblank_oam_rom import MODES,make_rom
from run_stage150_native_dynamic_oam import execute

PREFIX="VPD_STAGE151_NATIVE_PRERENDER_OAM_BOUNDARY_"
CERT=re.compile(
    r"^VPD_STAGE151_NATIVE_PRERENDER_OAM_BOUNDARY_(PASS|REJECT) "
    r"case=(activate_ninth|preserve_eight) "
    r"resets_between_frames=(\d+) reset_after_status=(\d+) "
    r"before_samples=(\d+) after_samples=(\d+) cpu_writes=(\d+) "
    r"invalid=(\d+) synthetic_only=yes "
    r"original_game_frame_timing_proven=no$",re.MULTILINE)


class BoundaryError(ValueError):
    pass


def _numeric(value):
    x=int(value)
    if str(x)!=value:raise BoundaryError("Noncanonical reset boundary number")
    return x


def verify(log,mode,*,reject=False):
    if mode not in MODES or not isinstance(log,str):
        raise BoundaryError("Invalid Stage151 source witness")
    status="REJECT" if reject else "PASS"
    if (log.count(PREFIX)!=1 or
            log.count(PREFIX+status)!=1):
        raise BoundaryError("Missing, duplicated or contradicted native reset")
    reports=list(CERT.finditer(log))
    if len(reports)!=1:
        raise BoundaryError("Malformed native pre-render reset provenance")
    decision,name,*fields=reports[0].groups()
    values=tuple(_numeric(x) for x in fields)
    if decision!=status or name!=mode:
        raise BoundaryError("Wrong synthetic mode or status in reset witness")
    if reject:
        if (values[2:5]!=(8,8,5) or values[-1]<1):
            raise BoundaryError("Native reset negative case lacks a real contradiction")
    elif values!=(1,0,8,8,5,0):
        raise BoundaryError("CPU writes and visible frames lack exactly one PPU reset")
    return {"case":mode,"rejected":bool(reject),
            "boundary_reset":values[0],"before_samples":values[2],
            "after_samples":values[3],"cpu_writes":values[4],
            "invalid":values[5],
            "original_game_frame_timing_proven":False}


def run(binary,temp):
    with tempfile.TemporaryDirectory(dir=temp) as td:
        root=Path(td)
        reports=[]
        for mode in MODES:
            rom=root/(mode+".nes")
            make_rom(rom,mode)
            reports.append((mode,execute(binary,rom,root/mode,mode,
                                         boundary=True)))
        wrong=execute(binary,root/"activate_ninth.nes",
                      root/"wrong_mode","preserve_eight",
                      reject=True,boundary=True)
        execute(binary,root/"preserve_eight.nes",root/"off",
                "preserve_eight",enabled=False,boundary=True)
    if ([name for name,_ in reports]!=list(MODES) or
            any(r["boundary"]["boundary_reset"]!=1 or
                r["boundary"]["before_samples"]!=8 or
                r["boundary"]["after_samples"]!=8 or
                r["boundary"]["original_game_frame_timing_proven"] is not False
                for _,r in reports) or
            not wrong["boundary"]["rejected"]):
        raise BoundaryError("Incomplete native pre-render temporal sweep")
    print("STAGE151_NATIVE_PRERENDER_OAM_FRAME_BOUNDARY_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes cases=2 "
          "pre_render_resets=1_each cpu_oam_writes=5_each "
          "before_xbuf_samples=8_each after_xbuf_samples=8_each "
          "wrong_mode_control=rejected observer_off_control=clean "
          "original_game_frame_timing_proven=no")
    return {"cases":2,"native_source_frame_boundary":True}


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("native_fceux",type=Path)
    cli.add_argument("private_temp",type=Path)
    args=cli.parse_args()
    run(args.native_fceux,args.private_temp)
