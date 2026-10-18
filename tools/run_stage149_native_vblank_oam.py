#!/usr/bin/env python3
"""Stage149: actual FCEUX CPU BIT $2002 and subsequent $2003/$2004 proof.

No screenshot, source ROM content or original game asset is published.
Stage149 proves register writes; NOT yet a changed-frame OAM/XBuf result.
"""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from make_stage148_vblank_oam_rom import MODES,make_rom
from run_stage100_fceux_synthetic_smoke import (
    backend_settings,categorize_exit)

PASS="VPD_STAGE149_NATIVE_VBLANK_OAM_WRITE_PASS"
REJECT="VPD_STAGE149_NATIVE_VBLANK_OAM_WRITE_REJECT"
WITNESS=re.compile(
    r"^VPD_STAGE149_NATIVE_VBLANK_OAM_WRITE_(PASS|REJECT) "
    r"case=(activate_ninth|preserve_eight) "
    r"status_high_read=(yes|no) oamaddr=(\d+) writes=(\d+) "
    r"first_oam=31 last_oam=35 "
    r"oam7_x=(\d+) oam8_y=(\d+) oam8_tile=(\d+) "
    r"oam8_attr=(\d+) oam8_x=(\d+) "
    r"attr_stored=(\d+) invalid=(\d+) synthetic_only=yes "
    r"original_game_oam_writes_proven=no$",re.MULTILINE)


class OamWriteError(ValueError):
    pass


def _number(value):
    parsed=int(value)
    if str(parsed)!=value:
        raise OamWriteError("Noncanonical native OAM numeric evidence")
    return parsed


def _parse(log,pass_expected):
    wanted=PASS if pass_expected else REJECT
    contradicted=REJECT if pass_expected else PASS
    if (not isinstance(log,str) or log.count(wanted)!=1 or
            contradicted in log):
        raise OamWriteError("Absent, duplicate or contradicted native CPU register result")
    matched=list(WITNESS.finditer(log))
    if len(matched)!=1:
        raise OamWriteError("Malformed pinned FCEUX CPU OAM witness")
    status,mode,high,*fields=matched[0].groups()
    values=tuple(_number(x) for x in fields)
    return status,mode,high,values


def verify(log,mode):
    if mode not in MODES:
        raise OamWriteError("Unknown synthetic CPU OAM case")
    status,name,high,values=_parse(log,True)
    expect=(31,5,160,120,2,0,64,0,0) if mode=="activate_ninth" else (
        31,5,64,255,255,255,255,227,0)
    if status!="PASS" or name!=mode or high!="yes" or values!=expect:
        raise OamWriteError("Native CPU register writes contradict generated fixture")
    return {"case":mode,"writes":5,"vblank_high_read":True,
            "oam_values":values[2:7],"attr_stored":values[7],
            "real_native_cpu_register_writes":True,
            "original_game_oam_writes_proven":False}


def verify_wrong_case(log):
    status,name,high,values=_parse(log,False)
    if (status!="REJECT" or name!="preserve_eight" or high!="yes" or
            values!=(31,5,160,120,2,0,64,0,5)):
        raise OamWriteError("False unchanged-OAM control lacks actual 5-byte mismatch")
    return {"negative":True,"mismatched_cpu_written_bytes":5}


def verify_sweep(reports):
    if (not isinstance(reports,list) or
            [name for name,_ in reports]!=list(MODES)):
        raise OamWriteError("Both native CPU OAM fixtures required in strict order")
    if any(item.get("case")!=mode or item.get("writes")!=5 or
           item.get("vblank_high_read") is not True or
           item.get("real_native_cpu_register_writes") is not True or
           item.get("original_game_oam_writes_proven") is not False
           for mode,item in reports):
        raise OamWriteError("Incomplete native CPU OAM mutation/control evidence")
    return {"cases":2,"register_writes":10,
            "native_cpu_register_writes_proven":True,
            "original_game_oam_writes_proven":False}


def execute(binary,rom,folder,mode,*,enabled=True,reject=False,timeout=45):
    if mode not in MODES or (reject and not enabled):
        raise OamWriteError("Invalid native OAM write test scenario")
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    env.update(backend_settings("xvfb",folder))
    # Every other synthetic proof is disabled for isolation.
    for key in list(env):
        if key.startswith("VPD_STAGE") and key.endswith("_PROBE"):
            env[key]="0"
    env["VPD_STAGE149_OAM_WRITES_PROBE"]="1" if enabled else "0"
    env["VPD_STAGE149_OAM_WRITES_CASE"]=mode
    cmd=[str(Path(binary).resolve()),"--newppu","1","--sound","0",
         "--opengl","0","--no-config","1",str(Path(rom).resolve())]
    logfile=folder/"native.log"
    with logfile.open("wb") as stream:
        p=subprocess.Popen(cmd,cwd=folder,env=env,stdin=subprocess.DEVNULL,
                           stdout=stream,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+(timeout if enabled else 2)
        alive=False
        try:
            while time.monotonic()<deadline:
                time.sleep(.1)
                log=logfile.read_text(encoding="utf8",errors="replace")
                if enabled and (PASS in log or REJECT in log):break
                if p.poll() is not None:break
            alive=p.poll() is None
        finally:
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    p.kill();p.wait(timeout=4)
    log=logfile.read_text(encoding="utf8",errors="replace")
    if not enabled:
        if not alive or PASS in log or REJECT in log:
            raise OamWriteError("Native observer-off run produced false proof")
        return None
    try:
        return verify_wrong_case(log) if reject else verify(log,mode)
    except OamWriteError as exc:
        raw=re.findall(
            r"VPD_STAGE149_NATIVE_VBLANK_OAM_WRITE_[^\r\n]{0,500}",log)
        details=raw[-1] if raw else categorize_exit(p.returncode,log)
        raise OamWriteError(str(exc)+": "+details) from exc


def run(binary,temp):
    with tempfile.TemporaryDirectory(dir=temp) as td:
        root=Path(td)
        reports=[]
        for mode in MODES:
            rom=root/(mode+".nes")
            make_rom(rom,mode)
            reports.append((mode,execute(binary,rom,root/mode,mode)))
        wrong=execute(binary,root/"activate_ninth.nes",root/"wrong_mode",
                      "preserve_eight",reject=True)
        execute(binary,root/"preserve_eight.nes",root/"observer_off",
                "preserve_eight",enabled=False)
    result=verify_sweep(reports)
    if wrong.get("mismatched_cpu_written_bytes")!=5:
        raise OamWriteError("Missing native false-control CPU OAM mismatch")
    print("STAGE149_NATIVE_VBLANK_OAM_CPU_WRITE_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes cases=2 "
          "cpu_register_writes=10 actual_ppustatus_high_read=yes "
          "oamaddr_31_verified=yes oamdata_31_to_35_verified=yes "
          "attribute_mask_verified=yes mismatched_control=rejected "
          "observer_off_control=clean cpu_write_to_xbuf_proven=no "
          "original_game_oam_writes_proven=no")
    return result


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("native_fceux",type=Path)
    cli.add_argument("private_temp",type=Path)
    a=cli.parse_args()
    run(a.native_fceux,a.private_temp)
