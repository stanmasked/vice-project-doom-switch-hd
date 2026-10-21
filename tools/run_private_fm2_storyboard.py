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
from audit_private_mmc3_chr_mapping import analyze_trace
from audit_private_nes_variant_banks import read_layout

SCRIPT_DIR=Path(__file__).resolve().parent


def private_target(directory):
    requested=Path(directory).expanduser()
    # Check the caller's path before resolving it. resolve() erases the
    # lexical symlink, including a dangling symlink to a not-yet-created
    # directory, which would otherwise silently redirect private captures.
    if requested.is_symlink():
        raise ValueError("private capture destination must not be a symlink")
    directory=requested.resolve(strict=False)
    if directory.exists():
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
    # Lua after-frame hooks may register after the power-on frame 0.
    # Do not demand an unobservable frame-0 image for a complete audit.
    samples=(frames-1)//interval
    if samples<1:
        raise ValueError("movie shorter than the first reliable capture interval")
    if samples>64:
        raise ValueError("movie requires more than 64 storyboard samples")
    return {"frames":frames,"last_frame":frames-1,
            "interval":interval,"sample_count":samples}


def parse_chr_targets(spec,bank_count):
    if not spec:
        return ()
    parts=spec.split(",")
    if len(parts)>64 or any(not p.isdecimal() or p.startswith("+") for p in parts):
        raise ValueError("invalid comma-separated CHR target bank list")
    result=tuple(sorted({int(p) for p in parts}))
    if not result or any(x>=bank_count for x in result):
        raise ValueError("CHR focus bank outside owner ROM layout")
    return result


def launch(rom,movie,directory,fceux="fceux",timeout_seconds=1800,
           interval=1803,trace_chr_banks=""):
    rom=Path(rom).expanduser()
    movie=Path(movie).expanduser()
    if rom.is_symlink() or movie.is_symlink():
        raise ValueError("private ROM/movie symlinks are not accepted")
    rom=rom.resolve(strict=True)
    movie=movie.resolve(strict=True)
    summary=audit_movie(movie,rom=rom)
    plan=capture_plan(summary,interval=interval)
    bank_count=0
    if trace_chr_banks:
        cartridge=read_layout(rom)
        if cartridge["mapper"]!=4:
            raise ValueError("private MMC3 CHR trace requires a Mapper 4 cartridge")
        bank_count=len(cartridge["chr"])//1024
    focus=parse_chr_targets(trace_chr_banks,bank_count)
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
    witness=target.parent/(target.name+".terminal_witness.txt")
    logfile=target.parent/(target.name+".fceux.log")
    trace_path=target.parent/(target.name+".mmc3_chr_focus.tsv")
    # Validate all destinations before creating the capture folder. A stale
    # witness must not cause a partial or ambiguous new private session.
    if witness.exists() or logfile.exists() or witness.is_symlink() or logfile.is_symlink():
        raise ValueError("private witness or log filename already exists")
    if focus and (trace_path.exists() or trace_path.is_symlink()):
        raise ValueError("private MMC3 trace filename already exists")
    target.mkdir(mode=0o700)
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
    if focus:
        chr_capture=SCRIPT_DIR/"capture_private_mmc3_chr_focus.lua"
        if not chr_capture.is_file():
            raise ValueError("private CHR capture Lua script missing")
        env.update({
            "VPD_PRIVATE_MMC3_TRACE_SCRIPT":str(chr_capture.resolve()),
            "VPD_PRIVATE_MMC3_TRACE_PATH":str(trace_path),
            "VPD_PRIVATE_MMC3_TARGETS":",".join(str(x) for x in focus),
            "VPD_PRIVATE_MMC3_BANK_COUNT":str(bank_count)
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
    result={"classification":"private ROM/FM2 actual emulator terminal-frame preflight",
            "rom_identity_matched":True,
            "fceux_terminal_frame_confirmed":True,
            "frame_count":plan["frames"],
            "storyboard_frames":report["sample_count"],
            "storyboard_complete":True,
            "original_level_identity_proven":False,
            "game_completion_proven":False}
    if focus:
        evidence=analyze_trace(trace_path,bank_count=bank_count,
                               focus_banks=focus,frame_interval=interval)
        result["mmc3_chr_mapper_write_evidence"]=evidence
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--movie",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--fceux",default="fceux")
    p.add_argument("--interval",type=int,default=1803)
    p.add_argument("--timeout-seconds",type=int,default=1800)
    p.add_argument("--trace-chr-banks",default="",
                   help="opt-in numeric CHR bank list; mapper writes only, not PPU display")
    a=p.parse_args()
    try:
        result=launch(a.rom,a.movie,a.output,fceux=a.fceux,
                      interval=a.interval,timeout_seconds=a.timeout_seconds,
                      trace_chr_banks=a.trace_chr_banks)
    except (OSError,ValueError,UnicodeError) as exc:
        p.exit(1,"PRIVATE_FM2_REPLAY_INCONCLUSIVE: "+str(exc)+"\n")
    print("PRIVATE_FM2_REPLAY_FRAME_CAPTURE_PASS")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
