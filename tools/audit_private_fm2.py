#!/usr/bin/env python3
"""ROM-private FCEUX FM2 input audit and candidate capture window planner.

Outputs aggregated timings and boolean ROM identity only. A matched hash is
not proof of deterministic emulation, successful playback, or stage identity.
Do not upload copyrighted ROM, original movie inputs or private captures.
"""
import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

FPS_NTSC=60.09982293844223
FPS_PAL=50.00697796826829
BUTTONS="RLDUTSBA"
MAX_SIZE=100_000_000


def rom_payload(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_SIZE:
        raise ValueError("missing, linked or oversized private ROM")
    with path.open('rb') as file:
        header=file.read(16)
        if len(header)!=16 or header[:4]!=b'NES\x1a':
            raise ValueError("invalid iNES header")
        if (header[7]&0x0c)==0x08:
            raise ValueError("NES2 unsupported by this conservative ROM checker")
        if header[6]&0x04:
            raise ValueError("trainer ROM unsupported by this conservative ROM checker")
        prg=header[4]*16384
        chr_=header[5]*8192
        if not prg:
            raise ValueError("empty PRG ROM")
        raw=file.read()
    if len(raw)!=prg+chr_:
        raise ValueError("ROM byte count differs from iNES header")
    return hashlib.md5(raw).digest(), ((header[6]>>4)|(header[7]&0xf0))


def audit_movie(path, rom=None, threshold=1200, interval=8, frames_per_window=96):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=MAX_SIZE:
        raise ValueError("missing, linked or oversized private FM2")
    if not 1<=threshold<=100_000 or not 1<=interval<=1200 or not 1<=frames_per_window<=512:
        raise ValueError("invalid capture planning parameters")
    header={}
    state='header'
    total=0
    commands=Counter()
    keys=Counter()
    active=0
    first_active=last_active=None
    prev_t=False
    start_edges=[]
    pauses=[]
    quiet_from=0
    port1_active=0
    candidates=[]
    with path.open('r',encoding='ascii',newline='') as source:
        for line in source:
            line=line.rstrip('\r\n')
            if line.startswith('|'):
                state='records'
                fields=line.split('|')
                if len(fields)!=6 or fields[0] or fields[-1] or fields[4]:
                    raise ValueError("unsupported FM2 text input row")
                if not re.fullmatch(r'[0-9]+',fields[1]):
                    raise ValueError("invalid FM2 command")
                command=int(fields[1])
                if command & ~31:
                    raise ValueError("unsupported FM2 command bits")
                p1,p2=fields[2],fields[3]
                if len(p1)!=8 or len(p2)!=8:
                    raise ValueError("invalid FM2 controller width")
                if not all((c=='.' or c==' ' or c==BUTTONS[i]) for i,c in enumerate(p1)):
                    raise ValueError("unexpected player-one controller alphabet")
                if not all((c=='.' or c==' ' or c==BUTTONS[i]) for i,c in enumerate(p2)):
                    raise ValueError("unexpected player-two controller alphabet")
                if command:
                    commands[str(total)]=command
                if any(c not in '. ' for c in p2):
                    port1_active+=1
                pressed=[ch for i,ch in enumerate(BUTTONS) if p1[i] not in '. ']
                if pressed:
                    keys.update(pressed)
                if 'T' in pressed and not prev_t:
                    start_edges.append(total)
                prev_t='T' in pressed
                is_active=bool(pressed or any(c not in '. ' for c in p2))
                if is_active:
                    active+=1
                    if first_active is None:first_active=total
                    last_active=total
                    if quiet_from is not None:
                        idle_length=total-quiet_from
                        if idle_length>=threshold:
                            pauses.append({'from_frame':quiet_from,'to_frame':total-1,'frames':idle_length})
                            if len(candidates)<48:
                                candidates.append((total,idle_length))
                        quiet_from=None
                else:
                    if quiet_from is None:quiet_from=total
                total+=1
            else:
                if state=='records':
                    if line:
                        raise ValueError("non-input bytes after FM2 input log")
                elif line:
                    if ' ' not in line:
                        raise ValueError("invalid FM2 header row")
                    k,v=line.split(' ',1)
                    if k in header and k!='comment':
                        raise ValueError("duplicate FM2 header key")
                    if k!='comment':header[k]=v
    if not total:
        raise ValueError("empty FM2 input log")
    required={"version":"3","fourscore":"0","port0":"1","port1":"1","port2":"0","FDS":"0"}
    for name,expected in required.items():
        if header.get(name)!=expected:
            raise ValueError("unsupported FM2 header value: "+name)
    if header.get('binary','0')!='0':
        raise ValueError("binary FM2 input log not supported")
    if header.get('palFlag','0') not in ('0','1') or header.get('NewPPU','0') not in ('0','1'):
        raise ValueError("invalid FM2 emulation configuration")
    if header.get('length') is not None and int(header['length'])!=total:
        raise ValueError("FM2 declared length differs from input records")
    raw=header.get('romChecksum','')
    if not raw.startswith('base64:'):
        raise ValueError("missing FM2 ROM MD5 digest")
    try:
        checksum=base64.b64decode(raw.split(':',1)[1],validate=True)
    except (ValueError,base64.binascii.Error) as e:
        raise ValueError("invalid FM2 ROM digest") from e
    if len(checksum)!=16:
        raise ValueError("invalid FM2 ROM MD5 digest length")
    matches=None
    mapper=None
    if rom is not None:
        digest,mapper=rom_payload(rom)
        matches=digest==checksum
        if not matches:
            raise ValueError("FM2 ROM identity mismatch; do not attempt authoritative playback")
    if quiet_from is not None:
        idle_length=total-quiet_from
        if idle_length>=threshold:
            pauses.append({'from_frame':quiet_from,'to_frame':total-1,'frames':idle_length})
    fps=FPS_PAL if header.get('palFlag','0')=='1' else FPS_NTSC
    windows=[]
    for n,(resume,quiet) in enumerate(candidates,1):
        aligned=max(0,((resume-64)//interval)*interval)
        windows.append({"candidate":n,"reason":"input resumes after long idle; stage not identified",
                        "idle_frames_before":quiet,"resume_frame":resume,
                        "capture_start_frame":aligned,
                        "capture_end_frame":aligned+(frames_per_window-1)*interval,
                        "capture_interval":interval,"capture_limit":frames_per_window,
                        "approx_resume_second":round(resume/fps,2)})
    return {
        "classification":"private FM2 input provenance and candidate window planning; no emulator replay",
        "format":"FM2 v3","emulator_build":header.get('emuVersion'),
        "ntsc":header.get('palFlag','0')=='0',"new_ppu":header.get('NewPPU','0')=='1',
        "frames":total,"duration_seconds":round(total/fps,2),"rerecord_count":int(header.get('rerecordCount','0')),
        "starts_from_power_on":commands.get('0')==2 and 'savestate' not in header,
        "rom_identity_matched":matches,"mapper_if_rom_checked":mapper,
        "active_input_frames":active,"first_active_frame":first_active,"last_active_frame":last_active,
        "player_two_active_frames":port1_active,"button_frame_counts":dict(keys),
        "start_button_press_frames":start_edges,"commands":dict(commands),
        "long_idle_periods":pauses,"candidate_capture_windows":windows,
        "original_stage_proven":False,"final_boss_completion_proven":False,
        "video_or_ppu_captured":False,
        "next_step":"Replay exact private ROM+FM2 read-only in FCEUX, capture stage screenshots/PPU/RAM privately and validate stage identities."
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('movie',type=Path)
    p.add_argument('--rom',type=Path,help='private owned ROM used only for in-memory digest verification')
    p.add_argument('--summary',type=Path,help='save aggregate JSON in a PRIVATE/ignored location')
    p.add_argument('--idle-threshold',type=int,default=1200)
    a=p.parse_args()
    try:
        result=audit_movie(a.movie,rom=a.rom,threshold=a.idle_threshold)
    except (OSError,ValueError,UnicodeError) as exc:
        p.exit(1,'PRIVATE_FM2_INCONCLUSIVE: '+str(exc)+'\n')
    if a.summary:
        a.summary.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('PRIVATE_FM2_INPUT_PREFLIGHT_PASS')
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
