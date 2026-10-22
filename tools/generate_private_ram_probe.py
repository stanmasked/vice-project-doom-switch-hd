#!/usr/bin/env python3
"""Generate a safe FCEUX Lua probe for per-frame candidate RAM bytes.

This script emits Lua source only. It does not run ROMs or export capture data.
"""
from pathlib import Path
import argparse

ADDRESSES=(0x000F,0x0011,0x0016,0x0017,0x0094,0x013A,0x013C)

def make_lua(output_name="ram_candidates.csv", frame_limit=600):
    if Path(output_name).name != output_name:
        raise ValueError("output name must be a simple filename")
    if frame_limit < 1:
        raise ValueError("frame_limit must be positive")
    addresses=", ".join(f"0x{x:04X}" for x in ADDRESSES)
    return f'''-- Generated private diagnostic probe; never commit its output.
local addresses = {{{addresses}}}
local out = assert(io.open("{output_name}.pending", "w"))
assert(out:write("frame," .. table.concat({{"{','.join(f'ram_{x:04x}' for x in ADDRESSES)}}, ",") .. "\\n"))
local last_frame = -1
local complete = false
emu.registerafter(function()
  if complete then return end
  local frame = emu.framecount()
  if frame == last_frame then return end
  last_frame = frame
  local values = {{}}
  for i, address in ipairs(addresses) do
    values[i] = string.format("%d", memory.readbyte(address))
  end
  assert(out:write(tostring(frame) .. "," .. table.concat(values, ",") .. "\\n"))
  assert(out:flush())
  if frame >= {frame_limit} then
    assert(out:close())
    assert(os.rename("{output_name}.pending", "{output_name}"))
    complete = true
  end
end)
'''
if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--frames",type=int,default=600)
    args=parser.parse_args()
    if args.output.exists(): parser.error("refusing to overwrite existing output")
    args.output.write_text(make_lua(args.output.name, args.frames),encoding="utf-8")
    print("VPD_PRIVATE_RAM_PROBE_GENERATED addresses=7 per_frame=yes bounded_completion=yes output_private=yes")
