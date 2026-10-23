#!/usr/bin/env python3
"""Strict source-hash guarded extension to owner-private Stage335 FM2 Lua witness.

Only the generated owner-local Lua sees gameplay; this generator never bundles it.
All captures must remain private. No ROM, FM2, or image data in public GitHub.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path

FIRST,LAST=380,640
ANCHOR_CALLBACK='emu.registerafter(function()\n'
ANCHOR_FRAME_END="  emit(frame,finish,'frame_end',nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,'RAM0D_after')\n"
ANCHOR_COMPLETE="assert(marker:close());assert(os.rename(root..'/COMPLETE.pending',root..'/COMPLETE.txt'));complete=true"

# Original 256x240 truecolour FCEUX GD data is A,R,G,B packed, with an 11-byte header.
PRIVATE_LUA_PROBE = r'''-- VPD_STAGE343 RGB palette image witness (owner-private)
local vpd343_frames={{{FRAMES}}}
local vpd343_indexed_frames={{{PALETTES}}}
local vpd343_points={{0,0},{127,32},{128,120},{64,180},{192,200},{255,239}}
local vpd343_meta=exclusive('stage343_rgb_palette_probes.tsv')
assert(vpd343_meta:write('frame\tx\ty\tr\tg\tb\tpalette_index\n'))
local vpd343_saved=0
local function vpd343_capture(frame)
 if not vpd343_frames[frame] then return end
 assert(movie.readonly() and movie.length()==expected_frames and rom.gethash('md5'):lower()==expected_md5,
    'original FM2 source identity/read-only state differs')
 local rawpixels=gui.gdscreenshot(false) -- XBuf, not the previously published XBackBuf
 assert(type(rawpixels)=='string' and #rawpixels==11+256*240*4,'unexpected FCEUX GD native dimensions')
 local h={string.byte(rawpixels,1,6)}
 assert(h[1]==255 and h[2]==254 and h[3]==1 and h[4]==0 and h[5]==0 and h[6]==240,
    'unexpected FCEUX GD 256x240 truecolour header')
 local f=exclusive('stage343_rgb_'..string.format('%04d',frame)..'.gd')
 assert(f:write(rawpixels) and f:close())
 for _,xy in ipairs(vpd343_points) do
  local x,y=xy[1],xy[2]
  local r,g,b,p=emu.getscreenpixel(x,y,false)
  assert(p>=0 and p<=255 and r>=0 and r<=255 and g>=0 and g<=255 and b>=0 and b<=255)
  local ofs=12+(y*256+x)*4
  local a,gr,gg,gb=string.byte(rawpixels,ofs,ofs+3)
  assert(a==0 and r==gr and g==gg and b==gb,'pixel probe disagrees with original XBuf GD')
  assert(vpd343_meta:write(string.format('%d\t%d\t%d\t%d\t%d\t%d\t%d\n',frame,x,y,r,g,b,p)))
 end
 if vpd343_indexed_frames[frame] then
  local pfile=exclusive('stage343_palette_'..string.format('%04d',frame)..'.idx')
  for y=0,239 do
   local row={}
   for x=0,255 do
    local r,g,b,index=emu.getscreenpixel(x,y,false)
    assert(index>=0 and index<=255,'FCEUX palette index invalid')
    local ofs=12+(y*256+x)*4
    local _,gr,gg,gb=string.byte(rawpixels,ofs,ofs+3)
    assert(r==gr and g==gg and b==gb,'indexed original pixel differs from RGB XBuf')
    row[x+1]=string.char(index)
   end
   assert(pfile:write(table.concat(row)))
  end
  assert(pfile:close())
 end
 vpd343_saved=vpd343_saved+1
end
'''


def _selection(values:tuple[int,...], *, maximum:int)->str:
    if (not values or len(values)>maximum or values!=tuple(sorted(set(values))) or
            any(not FIRST<=f<=LAST for f in values)):
        raise ValueError('invalid owner-private frame selection')
    return ','.join('['+str(f)+']=true' for f in values)


def generate(source:bytes, *, expected_sha256:str, frames:tuple[int,...],palette_frames:tuple[int,...])->bytes:
    if len(expected_sha256)!=64 or hashlib.sha256(source).hexdigest()!=expected_sha256:
        raise ValueError('original Lua full-file SHA-256 mismatch')
    selected=_selection(frames,maximum=32)
    palette=_selection(palette_frames,maximum=16)
    if not set(palette_frames)<=set(frames):raise ValueError('palette frame not among RGB frames')
    s=source.decode('utf-8')
    if 'VPD_STAGE343' in s or any(s.count(k)!=1 for k in (ANCHOR_CALLBACK,ANCHOR_FRAME_END,ANCHOR_COMPLETE)):
        raise ValueError('Stage335 source layout differs or already instrumented')
    probe=PRIVATE_LUA_PROBE.replace('{{FRAMES}}',selected).replace('{{PALETTES}}',palette)
    s=s.replace(ANCHOR_CALLBACK,probe+'\n'+ANCHOR_CALLBACK,1)
    s=s.replace(ANCHOR_FRAME_END,ANCHOR_FRAME_END+'  vpd343_capture(frame)\n',1)
    s=s.replace(ANCHOR_COMPLETE,
        'assert(vpd343_saved=='+str(len(frames))+',"missing original RGB frame")\n '
        'assert(vpd343_meta:flush() and vpd343_meta:close())\n '+ANCHOR_COMPLETE,1)
    return s.encode('utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--source-sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--frames',default='380,387,388,389,392,396,397,400,420,480,560,640')
    p.add_argument('--palette-frames',default='380,388,397,480')
    a=p.parse_args()
    if a.source.is_symlink() or not a.source.is_file() or a.output.exists() or a.output.is_symlink():
        p.error('source must be a regular file; refuse overwriting output')
    frames=lambda s:tuple(int(x) for x in s.split(',') if x)
    payload=generate(a.source.read_bytes(),expected_sha256=a.source_sha256,
                     frames=frames(a.frames),palette_frames=frames(a.palette_frames))
    with a.output.open('xb') as f:f.write(payload)
    print('STAGE343_PRIVATE_LUA_EXTENDED_CAPTURE_PREPARED')
if __name__=='__main__':main()
