#!/usr/bin/env python3
"""Stage150: native same-ROM pre/post VBlank CPU OAM -> sprite XBuf proof.

All observations must come from the temporary pinned FCEUX with the
Stage149 real CPU register hooks plus Stage150 newppu evaluation/raster
hooks. Native success is not inferred from Python modeling.
"""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage148_vblank_oam_rom import MODES,make_rom
from run_stage149_native_vblank_oam import (
    verify as verify_cpu,verify_wrong_case, OamWriteError)
from run_stage100_fceux_synthetic_smoke import (
    backend_settings,categorize_exit)

PASS="VPD_STAGE150_NATIVE_OAM_FRAME_PASS"
REJECT="VPD_STAGE150_NATIVE_OAM_FRAME_REJECT"
REPORT=re.compile(
    r"^VPD_STAGE150_NATIVE_OAM_FRAME_(PASS|REJECT) "
    r"case=(activate_ninth|preserve_eight) "
    r"before_count=(\d+) after_count=(\d+) "
    r"before_overflow=(yes|no) after_overflow=(yes|no) "
    r"before_xbuf=(\d+) after_xbuf=(\d+) "
    r"before_raw=(\d+) after_raw=(\d+) "
    r"before_sprite=(\d+) after_sprite=(\d+) "
    r"oam7_before=(\d+) oam7_after=(\d+) "
    r"oam8_y_before=(\d+) oam8_y_after=(\d+) "
    r"cpu_writes=(\d+) samples=16 invalid=(\d+) "
    r"synthetic_only=yes original_game_dynamic_oam_proven=no$",
    re.MULTILINE)


class DynamicOamError(ValueError):
    pass


def _number(text):
    x=int(text)
    if str(x)!=text:raise DynamicOamError("Noncanonical native OAM-frame number")
    return x


def _parse(log,require_pass):
    wanted=PASS if require_pass else REJECT
    contradicted=REJECT if require_pass else PASS
    if (not isinstance(log,str) or log.count(wanted)!=1 or
            contradicted in log):
        raise DynamicOamError("Missing/duplicate/contradicted native frame result")
    found=list(REPORT.finditer(log))
    if len(found)!=1:
        raise DynamicOamError("Invalid native CPU to PPU framebuffer witness")
    category,case,*groups=found[0].groups()
    counts=tuple(_number(v) if v.isdigit() else v for v in groups)
    return category,case,counts


def verify(log,mode):
    if mode not in MODES:
        raise DynamicOamError("Invalid dynamic OAM case")
    category,case,observed=_parse(log,True)
    activated=mode=="activate_ninth"
    expected=(8,8,"no","yes" if activated else "no",
              170,143 if activated else 170,
              42,15 if activated else 42,
              1,0 if activated else 1,
              64,160 if activated else 64,
              255,120 if activated else 255,5,0)
    if category!="PASS" or case!=mode or observed!=expected:
        raise DynamicOamError("FCEUX native pre/post sprite source contradiction")
    try:
        cpu=verify_cpu(log,mode)
    except OamWriteError as exc:
        raise DynamicOamError("Missing real CPU OAM witness: "+str(exc)) from exc
    if not cpu["real_native_cpu_register_writes"]:
        raise DynamicOamError("No native CPU event provenance")
    return {"case":mode,"samples":16,"before_xbuf":170,
            "after_xbuf":143 if activated else 170,
            "cpu_oam_writes":5,"observed_native_dynamic_oam":True,
            "original_game_dynamic_oam_proven":False}


def verify_wrong_case(log):
    category,case,observed=_parse(log,False)
    if category!="REJECT" or case!="preserve_eight" or observed[-1]<1:
        raise DynamicOamError("Wrong OAM case was not rejected at PPU/raster level")
    # Native Stage149 wrong-case witness must be present as well.
    try:
        from run_stage149_native_vblank_oam import verify_wrong_case as cpu_wrong
        cpu_wrong(log)
    except OamWriteError as exc:
        raise DynamicOamError("Negative PPU case lacks true CPU mismatch") from exc
    return {"rejected":True,"native_cpu_and_raster_contradiction":True}


def execute(binary,rom,folder,mode,*,enabled=True,reject=False,
            boundary=False,timeout=45):
    if mode not in MODES or (reject and (not enabled or mode!="preserve_eight")):
        raise DynamicOamError("Invalid native dynamic OAM control request")
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    env.update(backend_settings("xvfb",folder))
    for key in list(env):
        if key.startswith("VPD_STAGE") and key.endswith("_PROBE"):
            env[key]="0"
    env["VPD_STAGE149_OAM_WRITES_PROBE"]="1" if enabled else "0"
    env["VPD_STAGE150_DYNAMIC_OAM_PROBE"]="1" if enabled else "0"
    env["VPD_STAGE151_BOUNDARY_PROBE"]="1" if enabled and boundary else "0"
    env["VPD_STAGE149_OAM_WRITES_CASE"]=mode
    env["VPD_STAGE150_DYNAMIC_OAM_CASE"]=mode
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
                if enabled:
                    marker=("VPD_STAGE151_NATIVE_PRERENDER_OAM_BOUNDARY_"
                            if boundary else
                            "VPD_STAGE150_NATIVE_OAM_FRAME_")
                    if marker in log:break
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
            raise DynamicOamError("Disabled native OAM observer yielded false frame")
        return None
    try:
        result=verify_wrong_case(log) if reject else verify(log,mode)
        if boundary:
            # Stage151 additionally needs the native reset-boundary proof;
            # a Stage150 pixel certificate alone is insufficient.
            from run_stage151_native_prerender_boundary import (
                verify as verify_boundary)
            result["boundary"]=verify_boundary(log,mode,reject=reject)
        return result
    except DynamicOamError as exc:
        details=re.findall(r"VPD_STAGE150_NATIVE_OAM_FRAME_[^\r\n]{0,650}",log)
        raise DynamicOamError(str(exc)+": "+(
            details[-1] if details else categorize_exit(p.returncode,log))) from exc


def run(binary,temp):
    with tempfile.TemporaryDirectory(dir=temp) as td:
        root=Path(td)
        reports=[]
        for mode in MODES:
            rom=root/(mode+".nes")
            make_rom(rom,mode)
            reports.append((mode,execute(binary,rom,root/mode,mode)))
        wrong=execute(binary,root/"activate_ninth.nes",
                      root/"wrong_mode","preserve_eight",reject=True)
        execute(binary,root/"preserve_eight.nes",root/"observer_off",
                "preserve_eight",enabled=False)
    if ([mode for mode,_ in reports]!=list(MODES) or
        any(report.get("samples")!=16 or
            report.get("observed_native_dynamic_oam") is not True or
            report.get("original_game_dynamic_oam_proven") is not False
            for _,report in reports) or
        not wrong["native_cpu_and_raster_contradiction"]):
        raise DynamicOamError("Incomplete native CPU OAM -> XBuf sweep")
    print("STAGE150_NATIVE_DYNAMIC_OAM_TO_XBUF_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes cases=2 "
          "frames=4 samples=32 cpu_oam_writes_verified=yes "
          "pre_oam_evaluation_xbuf=170 activation_post_xbuf=143 "
          "unchanged_control_post_xbuf=170 ninth_overflow=yes "
          "wrong_case_control=rejected observer_off_control=clean "
          "original_game_dynamic_oam_proven=no")
    return {"cases":2,"samples":32,"native_dynamic_oam_to_xbuf":True}


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("native_fceux",type=Path)
    cli.add_argument("private_temp",type=Path)
    args=cli.parse_args()
    run(args.native_fceux,args.private_temp)
