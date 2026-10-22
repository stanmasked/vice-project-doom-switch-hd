#!/usr/bin/env python3
"""Run real private FCEUX for the original 321-frame PPU window.

Only local ROM/FM2 sources and local private capture paths; never
upload or log full input hashes or original ROM/FCEUX CPU traces.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from seal_private_road_ppu_321 import preflight,finalize,verify,private_dir
from run_private_fm2_storyboard import private_target

SCRIPT=Path(__file__).resolve().with_name("capture_private_road_ppu_321.lua")

def launch(rom:Path,movie:Path,output:Path,
           fceux:str="fceux",timeout_seconds:int=1800)->dict:
    if type(timeout_seconds) is not int or not 10<=timeout_seconds<=7200:
        raise ValueError("invalid private capture watchdog interval")
    if not SCRIPT.is_file():
        raise ValueError("missing source-only FCEUX private Lua script")
    binary=shutil.which(fceux)
    if binary is None:raise ValueError("no installed FCEUX binary")
    # The target must be new and OUTSIDE any public Git checkout.
    target=private_target(output)
    target.mkdir(mode=0o700)
    try:
        pre=preflight(rom,movie,target)
        logfile=target/"fceux_private_session.log"
        env=os.environ.copy()
        env.update({
            "VPD_PRIVATE_PPU321_OUTPUT_DIR":str(target),
            "VPD_PRIVATE_FM2_PATH":str(movie.resolve(strict=True)),
            "VPD_PRIVATE_ROM_PAYLOAD_MD5":pre["rom_payload_md5"],
            "VPD_PRIVATE_FRAME_COUNT":str(pre["movie_frames"]),
        })
        command=[binary,"--no-config","1","--sound","0",
                 "--loadlua",str(SCRIPT),str(rom.resolve(strict=True))]
        if (sys.platform.startswith("linux") and not env.get("DISPLAY")
            and shutil.which("xvfb-run")):
            command=["xvfb-run","-a","-s","-screen 0 1024x768x24",*command]
        process=None
        with logfile.open("xb") as logs:
            try:
                process=subprocess.Popen(
                    command,env=env,stdout=logs,stderr=subprocess.STDOUT)
                deadline=time.monotonic()+timeout_seconds
                while time.monotonic()<deadline:
                    if (target/"COMPLETE.txt").is_file():
                        break
                    if process.poll() is not None:
                        raise ValueError("private FCEUX exited before 321-frame completion")
                    time.sleep(.25)
                else:
                    raise ValueError("private FCEUX did not reach movie frame 920")
            finally:
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill();process.wait(timeout=5)
        finalize(rom,movie,target)
        return verify(rom,movie,target)
    except Exception:
        # Keep private partial captures for local diagnostics only.
        # Never report success when the FCEUX or evidence run failed.
        raise

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom",required=True,type=Path)
    p.add_argument("--movie",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--fceux",default="fceux")
    p.add_argument("--timeout-seconds",type=int,default=1800)
    a=p.parse_args()
    launch(a.rom,a.movie,a.output,fceux=a.fceux,
           timeout_seconds=a.timeout_seconds)
    print("VPD_PRIVATE_ROAD_PPU321_REAL_FCEUX_SOURCE_SEAL_PASS"
          " source_files_unchanged=yes"
          " ppu321_phase_verified=yes"
          " sha256_identity_private=yes"
          " legacy_road_sha256_join_verified=no"
          " original_game_camera_proven=no")
if __name__=="__main__":
    main()
