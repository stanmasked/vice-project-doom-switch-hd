#!/usr/bin/env python3
"""Real FCEUX/Xvfb smoke with an exclusively fabricated 6502 NES program.

No owner ROM, FM2, sprites or screenshots are ever read or exported.
A live FCEUX Lua callback must observe emulated frame/cycle/RGB/CPU
functions and a true 6502 execution at $8000 before reporting PASS.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from build_fceux_smoke_rom import build_rom

LUA=r'''
local output=assert(os.getenv("VPD_SYNTHETIC_REAL_FCEUX_WITNESS"))
for _,api in ipairs({
    emu.registerbefore,emu.registerafter,emu.getscreenpixel,
    debugger.getcyclescount,memory.registerexec,
    memory.registerwrite,rom.gethash,movie.play
})do assert(type(api)=="function","native FCEUX Lua API missing") end
local executed=0
memory.registerexec(0x8000,function() executed=executed+1 end)
memory.registerwrite(0x2005,function()end)
local first_cycle=nil
emu.registerbefore(function()
 if first_cycle==nil then first_cycle=debugger.getcyclescount() end
end)
local complete=false
emu.registerafter(function()
 if complete then return end
 local frame=emu.framecount()
 if frame<20 then return end
 assert(executed>=1,"6502 source execution at 0x8000 missing")
 assert(type(first_cycle)=="number")
 local last_cycle=debugger.getcyclescount()
 assert(type(last_cycle)=="number" and last_cycle>first_cycle)
 local r,g,b=emu.getscreenpixel(0,120,true)
 assert(type(r)=="number" and type(g)=="number" and type(b)=="number")
 assert(r>=0 and r<=255 and g>=0 and g<=255 and b>=0 and b<=255)
 local rom_md5=rom.gethash("md5")
 assert(type(rom_md5)=="string" and #rom_md5==32)
 local file=assert(io.open(output,"wb"))
 assert(file:write(
  "VPD_REAL_FCEUX_EXECUTABLE_API_PASS\n"..
  "frame="..frame.."\n"..
  "real_cpu_exec=yes\n"..
  "real_cpu_cycle_clock=yes\n"..
  "real_ppu_rgb_api=yes\n"..
  "source=synthetic_rom_only\n"))
 assert(file:close())
 complete=true
end)
'''

def verify(executable:Path,timeout:int=40)->dict:
    if shutil.which("xvfb-run") is None:
        raise ValueError("xvfb-run is required for headless native FCEUX")
    exe=executable.expanduser()
    if not exe.is_file():
        found=shutil.which(str(executable))
        if not found:raise ValueError("native FCEUX executable missing")
        exe=Path(found)
    with tempfile.TemporaryDirectory(prefix="vice-fceux-romfree-") as td:
        folder=Path(td)
        rom=folder/"fabricated.nes"
        lua=folder/"probe.lua"
        witness=folder/"guest-result.txt"
        logfile=folder/"emulator.log"
        rom.write_bytes(build_rom())
        lua.write_text(LUA,encoding="ascii")
        env={**os.environ,"SDL_AUDIODRIVER":"dummy",
             "QT_QPA_PLATFORM":"xcb",
             "VPD_SYNTHETIC_REAL_FCEUX_WITNESS":str(witness)}
        command=["xvfb-run","-a","-s","-screen 0 1024x768x24",
                 str(exe),"--no-config","1","--sound","0",
                 "--loadlua",str(lua),str(rom)]
        with logfile.open("wb") as log:
            p=subprocess.Popen(command,env=env,stdout=log,
                               stderr=subprocess.STDOUT)
            try:
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    if witness.is_file():
                        break
                    if p.poll() is not None:
                        raise ValueError("real FCEUX exited before native proof")
                    time.sleep(0.1)
                else:
                    raise ValueError("native FCEUX never executed fabricated ROM")
            finally:
                if p.poll() is None:
                    p.terminate()
                    try:p.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.wait(timeout=4)
        actual=witness.read_text("ascii").splitlines()
        if len(actual)!=6 or actual[0]!="VPD_REAL_FCEUX_EXECUTABLE_API_PASS":
            raise ValueError("native FCEUX Lua guest proof malformed")
        if not re.fullmatch(r"frame=[2-9][0-9]+",actual[1]):
            raise ValueError("emulator never advanced to frame 20")
        if actual[2:]!=[
            "real_cpu_exec=yes","real_cpu_cycle_clock=yes",
            "real_ppu_rgb_api=yes","source=synthetic_rom_only"
        ]:
            raise ValueError("actual original-free FCEUX APIs not proven")
        return {"real_fceux_executable":True,
                "actual_cpu_frame_count":int(actual[1].split("=")[1]),
                "actual_6502_cpu_execution":True,
                "real_ppu_rgb_lua_api":True,
                "original_ROM_or_FM2_used":False}

if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--fceux",default="fceux",type=Path)
    cli.add_argument("--timeout",default=40,type=int)
    args=cli.parse_args()
    result=verify(args.fceux,args.timeout)
    print("VPD_REAL_FCEUX_EXECUTABLE_API_PASS"
          " frame_count="+str(result["actual_cpu_frame_count"])+
          " cpu_6502_execution=yes native_lua_hooks=yes"
          " source=synthetic_only original_assets=no")
