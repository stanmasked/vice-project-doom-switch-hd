#!/usr/bin/env python3
"""Prepare one owner-only consecutive Stage346 RGB replay from sealed Stage344 Lua.

This script contains no ROM/FM2 pixels or owner SHA values. It refuses unknown
Lua source, changed instrumentation layout, old selections and overwrite.
The generated Lua and captures must remain exclusively owner-private.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path

from audit_private_stage346_scroll_windows import WINDOWS

OLD_FIRST,OLD_LAST=420,444
OLD_PALETTES=(420,432,444)
FRAME_PREFIX='local vpd343_frames='
PALETTE_PREFIX='local vpd343_indexed_frames='
COUNT_OLD='assert(vpd343_saved==25,"missing original RGB frame")'


def selection(frames:range|tuple[int,...])->str:
    return '{'+','.join('['+str(f)+']=true' for f in frames)+'}'


def replace_once(source:str,old:str,new:str)->str:
    if source.count(old)!=1:
        raise ValueError('sealed private Lua instrumentation layout unexpected')
    return source.replace(old,new,1)


def prepare(source:bytes, *, source_sha256:str,first:int,last:int)->bytes:
    if (first,last) not in WINDOWS:
        raise ValueError('unsupported original adjacent RGB capture window')
    if (not isinstance(source_sha256,str) or len(source_sha256)!=64 or
        any(ch not in '0123456789abcdef' for ch in source_sha256) or
        hashlib.sha256(source).hexdigest()!=source_sha256):
        raise ValueError('sealed source Lua checksum does not match')
    if not 1024<=len(source)<=100_000:
        raise ValueError('sealed owner-private Lua source length differs')
    s=source.decode('utf-8')
    old=FRAME_PREFIX+selection(range(OLD_FIRST,OLD_LAST+1))
    new=FRAME_PREFIX+selection(range(first,last+1))
    s=replace_once(s,old,new)
    old=PALETTE_PREFIX+selection(OLD_PALETTES)
    new=PALETTE_PREFIX+selection((first,(first+last)//2,last))
    s=replace_once(s,old,new)
    s=replace_once(s,COUNT_OLD,
                   f'assert(vpd343_saved=={last-first+1},"missing original RGB frame")')
    for required in ("movie.readonly()", "gui.gdscreenshot(false)",
                     "emu.getscreenpixel(x,y,false)", "rom.gethash('md5')",
                     "emu.registerafter(function()", "COMPLETE.pending",
                     "vpd343_capture(frame)"):
        if required not in s:
            raise ValueError('required sealed private FCEUX source contract absent')
    if s.count(FRAME_PREFIX)!=1 or s.count(PALETTE_PREFIX)!=1:
        raise ValueError('unexpected repeated capture selector')
    return s.encode('utf-8')


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--source-sha256',required=True)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--first',required=True,type=int)
    p.add_argument('--last',required=True,type=int)
    a=p.parse_args()
    try:
        if a.source.is_symlink() or not a.source.is_file():
            raise ValueError('no owner-private sealed Lua source')
        if a.output.is_symlink() or a.output.exists():
            raise ValueError('refusing overwrite of owner-private Lua')
        if a.output.parent.is_symlink() or not a.output.parent.is_dir():
            raise ValueError('invalid private output directory')
        payload=prepare(a.source.read_bytes(),
            source_sha256=a.source_sha256,first=a.first,last=a.last)
        with a.output.open('xb') as f:f.write(payload)
        print('VPD_STAGE346_PRIVATE_LUA_CAPTURE_PREPARED')
    except (OSError,ValueError,UnicodeError):
        p.exit(1,'VPD_STAGE346_PRIVATE_LUA_CAPTURE_INCONCLUSIVE\n')

if __name__=='__main__':main()
