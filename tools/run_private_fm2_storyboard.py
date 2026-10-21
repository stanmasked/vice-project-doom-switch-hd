#!/usr/bin/env python3
"""Run a locally installed real FCEUX with a private ROM and matching FM2.

Never copy files to any GitHub repository or third-party service.
The command does not claim it has reproduced the source game unless a real
local FCEUX process completes the movie-timeline witness and capture audit.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from audit_private_fm2 import audit_movie
from audit_private_fceux_storyboard import audit as audit_storyboard

SCRIPT_DIR=Path(__file__).resolve().parent


def private_target(directory):
    directory=Path(directory).expanduser().resolve(strict=False)
    if directory.is_symlink() or directory.exists():
        raise ValueError("private capture destination must be a NEW directory")
    parent=directory.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError("private output parent must exist and not be a symlink")
    for ancestor in (parent,*parent.parents):
        if (ancestor/".git").exists():
            raise ValueError("refusing a private capture folder inside any Git checkout")
    return directory


def capture_plan(movie_summary,interval=1803):
    frames=movie_summary["frames"]
    if not movie_summary["rom_identity_matched"]:
        raise ValueError("ROM identity not independently verified")
    if not movie_summary["starts_from_power_on"]:
        raise ValueError("FM2 does not have a reliable power-on initial state")
    if not 1<=interval<=120000:
        raise ValueError("unsupported storyboard frame interval")
    samples=1+(frames-1)//interval
    if samples>64:
        raise ValueError("movie requires more than 64 storyboard samples")
    return {"frames":frames,"last_frame":frames-1,
            "interval":interval,"sample_count":samples}


def launch(rom,movie,directory,fceux="fceux",timeout_seconds=1800,
           interval=1803):
    rom=Path(rom).expanduser().resolve(strict=True)
    movie=Path(movie).expanduser().resolve(strict=True)
    if rom.is_symlink() or movie.is_symlink():
        raise ValueError("private ROM/movie symlinks are not accepted")
    summary=audit_movie(movie,rom=rom)
    plan=capture_plan(summary,interval=interval)
    target=private_target(directory)
    binary=shutil.which(fceux)
    if binary is None:
        raise ValueError("FCEUX executable not installed (no emulation performed)")
    if not 1<=timeout_seconds<=7200:
        raise ValueError("invalid private replay watchdog")
    storyboard=SCRIPT_DIR/"capture_fceux_movie_storyboard.lua"
    wrapper=SCRIPT_DIR/"run_private_fm2_storyboard.lua"
    for source in (storyboard,wrapper):
        if not source.is_file():
            raise ValueError("missing public source-only FCEUX Lua script")
    target.mkdir(mode=0o700)
    witness=target.parent/(target.name+".terminal_witness.txt")
    logfile=target.parent/(target.name+".fceux.log")
    if witness.exists() or logfile.exists() or witness.is_symlink() or logfile.is_symlink():
        raise ValueError("private witness or log filename already exists")
    env=os.environ.copy()
    env.update({
        "VPD_PRIVATE_OUTPUT_DIR":str(target),
        "VPD_PRIVATE_FM2_PATH":str(movie),
        "VPD_PRIVATE_STORYBOARD_SCRIPT":str(storyboard.resolve()),
        "VPD_PRIVATE_WITNESS":str(witness),
        "VPD_PRIVATE_FRAME_COUNT":str(plan["frames"]),
        "VPD_PRIVATE_CAPTURE_INTERVAL":str(plan["interval"]),
        "VPD_PRIVATE_CAPTURE_LIMIT":str(plan["sample_count"])
    })
    command=[binary,"--no-config","1","--sound","0",
             "--loadlua",str(wrapper.resolve()),str(rom)]
    if sys.platform.startswith("linux") and not env.get("DISPLAY") and shutil.which("xvfb-run"):
        command=["xvfb-run","-a","-s","-screen 0 1024x768x24",*command]
    process=None
    with logfile.open("xb") as log:
        try:
            process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+timeout_seconds
            while time.monotonic()<deadline:
                if witness.is_file():
                    break
                if process.poll() is not None:
                    raise ValueError("FCEUX exited before terminal FM2 witness")
                time.sleep(0.25)
            else:
                raise ValueError("FCEUX did not reach terminal movie frame within watchdog")
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    if not witness.is_file() or witness.is_symlink():
        raise ValueError("missing trustworthy terminal FM2 witness")
    rows={}
    for line in witness.read_text(encoding="ascii").splitlines():
        if "=" not in line:raise ValueError("malformed FM2 terminal witness")
        k,v=line.split("=",1)
        if k in rows:raise ValueError("duplicate FM2 terminal witness key")
        rows[k]=v
    if (rows.get("format")!="private_fm2_terminal_witness_v1"
       or rows.get("movie_readonly")!="yes"
       or rows.get("movie_active_before_terminal")!="yes"
       or rows.get("movie_terminal_frame")!=str(plan["last_frame"])
       or rows.get("movie_frame_count")!=str(plan["frames"])
       or rows.get("movie_mode_at_terminal") not in ("playback","finished")
       or rows.get("original_stage_proven")!="no"
       or rows.get("game_completion_proven")!="no"):
        raise ValueError("terminal FM2 witness inconsistent with verified private input")
    report=audit_storyboard(target,require_complete=True)
    if (report["sample_count"]!=plan["sample_count"]
        or not report["complete_window_verified"]):
        raise ValueError("private FM2 storyboard incomplete")
    return {"classification":"private ROM/FM2 actual emulator terminal-frame preflight",
            "rom_identity_matched":True,
            "fceux_terminal_frame_confirmed":True,
            "frame_count":plan["frames"],
            "storyboard_frames":report["sample_count"],
            "storyboard_complete":True,
            "original_level_identity_proven":False,
            "game_completion_proven":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--movie",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--fceux",default="fceux")
    p.add_argument("--interval",type=int,default=1803)
    p.add_argument("--timeout-seconds",type=int,default=1800)
    a=p.parse_args()
    try:
        result=launch(a.rom,a.movie,a.output,fceux=a.fceux,
                      interval=a.interval,timeout_seconds=a.timeout_seconds)
    except (OSError,ValueError,UnicodeError) as exc:
        p.exit(1,"PRIVATE_FM2_REPLAY_INCONCLUSIVE: "+str(exc)+"\n")
    print("PRIVATE_FM2_REPLAY_FRAME_CAPTURE_PASS")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
