#!/usr/bin/env python3
"""Run the generated RAM probe in native FCEUX against a fabricated ROM only."""
import argparse
import csv
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from build_fceux_smoke_rom import build_rom
from generate_private_ram_probe import make_lua
from private_ram_probe_validate import analyze

FIELDS=("ram_000f","ram_0011","ram_0016","ram_0017","ram_0094","ram_013a","ram_013c")

def run(fceux, frames=321, timeout=60):
    if not 1 <= frames <= 10000:
        raise ValueError("frames must be between 1 and 10000")
    xvfb=shutil.which("xvfb-run")
    if not xvfb:
        raise ValueError("xvfb-run is required")
    exe=shutil.which(str(fceux)) or str(Path(fceux).expanduser())
    if not Path(exe).is_file():
        raise ValueError("FCEUX executable not found")
    with tempfile.TemporaryDirectory(prefix="vpd-ram-probe-synthetic-") as td:
        root=Path(td); rom=root/"synthetic.nes"; lua=root/"probe.lua"
        csv_path=root/"capture.csv"; pending=root/"capture.csv.pending"
        witness=root/"probe-complete.txt"
        rom.write_bytes(build_rom())
        lua_source=make_lua(csv_path.name,frames)
        lua_source=lua_source.replace("local complete = false", "local complete = false\\nlocal witness = assert(io.open(\\"probe-complete.txt\\", \\"w\\"))")
        lua_source=lua_source.replace("complete = true", "assert(witness:write(\\"RAM_PROBE_COMPLETE\\\\nframes={frames}\\\"))\\n    assert(witness:close())\\n    complete = true")
        lua.write_text(lua_source,encoding="ascii")
        env={**os.environ,"SDL_AUDIODRIVER":"dummy","QT_QPA_PLATFORM":"xcb"}
        log_path=root/"fceux.log"
        with log_path.open("wb") as log:
            proc=subprocess.Popen([xvfb,"-a","-s","-screen 0 1024x768x24",exe,
                                   "--no-config","1","--sound","0","--loadlua",str(lua),str(rom)],
                                  stdout=log,stderr=subprocess.STDOUT,env=env)
            try:
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    if witness.exists(): break
                    if proc.poll() is not None:
                        raise RuntimeError("FCEUX exited before completing RAM probe")
                    time.sleep(0.1)
                else:
                    raise TimeoutError("RAM probe did not finish before timeout")
                if not witness.is_file() or f"frames={frames}" not in witness.read_text(encoding="ascii"):
                if report["frames"] != frames:
                    raise AssertionError("unexpected sample count")
                with csv_path.open(newline="",encoding="utf-8") as stream:
                    rows=list(csv.DictReader(stream))
                if len(rows) != frames or len(rows[0]) != 8:
                    raise AssertionError("CSV must contain exactly one header and requested data rows")
                if list(rows[0]) != ["frame",*FIELDS]:
                    raise AssertionError("CSV header does not match candidate address schema")
                if pending.exists():
                    raise AssertionError("pending output remained after completion")
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill(); proc.wait(timeout=5)
        return {"frames":report["frames"],"first_frame":report["first_frame"],
                "last_frame":report["last_frame"],"addresses":len(report["signals"]),
                "synthetic_rom_only":True}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fceux",required=True)
    parser.add_argument("--frames",type=int,default=321)
    parser.add_argument("--timeout",type=int,default=60)
    args=parser.parse_args()
    print("VPD_PRIVATE_RAM_NATIVE_PROBE_PASS "+str(run(args.fceux,args.frames,args.timeout)))
