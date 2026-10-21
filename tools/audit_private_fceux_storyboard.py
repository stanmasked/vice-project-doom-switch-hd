#!/usr/bin/env python3
"""Validate private FCEUX storyboard files without exporting ROM/game assets.

Integrity/metadata validation does not prove real emulator playback or scene identity.
"""
import argparse
import json
from pathlib import Path
import re

WIDTH, HEIGHT = 256, 240
P6_HEADER = b'P6\n256 240\n255\n'
RGB_SIZE = len(P6_HEADER) + WIDTH*HEIGHT*3
PAL_SIZE = WIDTH*HEIGHT
MAX_STILLS = 64
META_RE = re.compile(r'^frame_([0-9]{6,9})\.meta\.txt$')
FILENAME_RE = re.compile(r'^frame_([0-9]{6,9})\.(?:ppm|pal\.bin|meta\.txt)$')
ROM_ID_RE = re.compile(r'^[0-9a-fA-F]{32}$')
DEC_RE = re.compile(r'^(?:0|[1-9][0-9]*)$')
PALETTE_ALLOWED = frozenset(range(64)) | {254}


def regular_file(path, size):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
        raise ValueError('missing, symlinked or malformed storyboard artifact')


def decimal(data, name, lower, upper):
    raw = data.get(name)
    if raw is None or not DEC_RE.fullmatch(raw):
        raise ValueError('missing or malformed storyboard metadata integer: '+name)
    value = int(raw)
    if not lower <= value <= upper:
        raise ValueError('out-of-range storyboard metadata integer: '+name)
    return value


def parse_meta(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
        raise ValueError('missing, symlinked or oversize storyboard metadata')
    fields={}
    for row in path.read_text(encoding='ascii').splitlines():
        if not row:
            continue
        if '=' not in row:
            raise ValueError('malformed storyboard metadata row')
        name, value=row.split('=',1)
        if not name or name in fields:
            raise ValueError('empty or duplicate storyboard metadata key')
        fields[name]=value
    needed={
        'format','frame','rom_md5','interval','start_frame','stop_frame',
        'capture_limit','invalid_palette_values','screen_size','source'
    }
    if set(fields)!=needed:
        raise ValueError('unsupported or missing storyboard metadata keys')
    if fields['format']!='private_fceux_storyboard_v1':
        raise ValueError('unsupported storyboard metadata format')
    if fields['screen_size']!='256x240' or fields['source']!='emu.getscreenpixel':
        raise ValueError('unsupported storyboard rendering provenance')
    if not ROM_ID_RE.fullmatch(fields['rom_md5']):
        raise ValueError('invalid private storyboard ROM identity')
    return fields


def audit(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('storyboard root must be a non-symlink directory')
    items=list(root.iterdir())
    if len(items)>3*MAX_STILLS:
        raise ValueError('too many storyboard files')
    for path in items:
        if not FILENAME_RE.fullmatch(path.name) or path.is_symlink() or not path.is_file():
            raise ValueError('unknown or linked file in private storyboard')
    metas=[p for p in items if p.name.endswith('.meta.txt')]
    if not 1 <= len(metas) <= MAX_STILLS:
        raise ValueError('expected 1..64 storyboard samples')
    metas.sort(key=lambda p:(len(p.name),p.name))
    expected=set()
    session=None
    first_frame=last_frame=None
    missing_pixels=0
    previous=-1
    for file in metas:
        m=META_RE.fullmatch(file.name)
        if not m:
            raise ValueError('invalid storyboard metadata filename')
        frame=int(m.group(1))
        if file.name!=f'frame_{frame:06d}.meta.txt':
            raise ValueError('noncanonical storyboard filename')
        if frame<=previous:
            raise ValueError('out of order or duplicate storyboard frames')
        previous=frame
        data=parse_meta(file)
        if decimal(data,'frame',0,999999999)!=frame:
            raise ValueError('frame filename/metadata mismatch')
        interval=decimal(data,'interval',1,120000)
        start=decimal(data,'start_frame',0,999999999)
        stop=decimal(data,'stop_frame',0,999999999)
        limit=decimal(data,'capture_limit',1,64)
        unavailable=decimal(data,'invalid_palette_values',0,PAL_SIZE)
        if not start<=frame<=stop or frame%interval!=0:
            raise ValueError('storyboard frame outside configured cadence or window')
        if session is None:
            session=(data['rom_md5'].lower(),interval,start,stop,limit)
        elif session!=(data['rom_md5'].lower(),interval,start,stop,limit):
            raise ValueError('mixed storyboard sessions or ROM identities')
        if len(metas)>limit:
            raise ValueError('storyboard exceeds configured capture limit')
        prefix=f'frame_{frame:06d}'
        ppm=root/(prefix+'.ppm')
        pal=root/(prefix+'.pal.bin')
        regular_file(ppm,RGB_SIZE)
        regular_file(pal,PAL_SIZE)
        with ppm.open('rb') as f:
            if f.read(len(P6_HEADER))!=P6_HEADER:
                raise ValueError('invalid storyboard P6 header')
        palette=pal.read_bytes()
        if any(byte not in PALETTE_ALLOWED for byte in palette):
            raise ValueError('invalid storyboard NES palette value')
        if palette.count(254)!=unavailable:
            raise ValueError('storyboard unavailable palette count mismatch')
        missing_pixels+=unavailable
        if first_frame is None:
            first_frame=frame
        last_frame=frame
        expected.update({file.name,ppm.name,pal.name})
    if {p.name for p in items}!=expected:
        raise ValueError('orphan or missing storyboard artifact')
    return {
       'classification':'private FCEUX storyboard structural preflight only',
       'storyboard_integrity_verified':True,
       'sample_count':len(metas),
       'first_frame':first_frame,
       'last_frame':last_frame,
       'capture_interval':session[1],
       'capture_limit':session[4],
       'unavailable_palette_pixels':missing_pixels,
       'rom_identity_consistent':True,
       'original_game_emulation_proven':False,
       'original_stage_identity_proven':False,
       'game_completion_proven':False,
       'next_step':'Privately review frames in FCEUX and independently identify scene and level boundaries.'
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('private_storyboard',type=Path)
    args=p.parse_args()
    try:
        report=audit(args.private_storyboard)
    except (OSError,ValueError,UnicodeError) as exc:
        p.exit(1,'PRIVATE_FCEUX_STORYBOARD_INCONCLUSIVE: '+str(exc)+'\n')
    print('PRIVATE_FCEUX_STORYBOARD_PREFLIGHT_PASS')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
