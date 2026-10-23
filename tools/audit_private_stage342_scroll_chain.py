#!/usr/bin/env python3
"""Stage342: authenticate CPU clock, RAM $0D -> $2005 -> classic FCEUX PPU t.

Owner-private inputs only. No original register values/timestamps/ROM identifiers
are included in the emitted aggregate. Legacy renderer line 0 is NOT a PPU dot.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

CPU_HEADER = ('frame','sequence','cycle','event','pc','opcode','operand','value',
    'old_value','new_value','a','x','y','ppu_ordinal','ppu_toggle_before',
    'ppu_toggle_after','writer_cycle','writer_pc','writer_opcode','writer_operand',
    'ram0d_before','ram0d_live','bank_context','note')
NATIVE_HEADER = ('core_frame_ordinal','cpu_timestamp','event','legacy_scanline',
    'renderer_pixel_not_dot','refresh_addr','temp_addr','write_toggle','fine_x','ppu_mask')
MAX_BYTES = 80000000


def checked(path: Path, sha: str) -> None:
    if (path.is_symlink() or not path.is_file() or
            not 0 < path.stat().st_size <= MAX_BYTES):
        raise ValueError('missing, symlinked or oversize private witness')
    if len(sha) != 64 or any(k not in '0123456789abcdef' for k in sha):
        raise ValueError('invalid expected witness digest')
    with path.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != sha:
            raise ValueError('authenticated private witness SHA-256 mismatch')


def load_rows(path: Path, header: tuple[str, ...], frame_field: str,
              first: int, last: int) -> dict[int, list[dict[str, str]]]:
    records: dict[int, list[dict[str,str]]] = defaultdict(list)
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r = csv.DictReader(f, delimiter='\t')
        if r.fieldnames != list(header):
            raise ValueError('unsupported private witness schema')
        prev_frame = first
        for row in r:
            if None in row or any(x is None for x in row.values()):
                raise ValueError('broken original source event row')
            frame = int(row[frame_field])
            if not first <= frame <= last or frame < prev_frame:
                raise ValueError('source event frame order/coverage invalid')
            prev_frame = frame
            records[frame].append(row)
    if set(records) != set(range(first,last+1)):
        raise ValueError('incomplete original source frame coverage')
    return records


def byte_hex(value: str) -> int:
    if len(value) != 2 or any(ch not in '0123456789abcdefABCDEF' for ch in value):
        raise ValueError('malformed original CPU byte')
    return int(value,16)


def word_hex(value: str) -> int:
    if len(value) != 4 or any(ch not in '0123456789abcdefABCDEF' for ch in value):
        raise ValueError('malformed classic PPU address')
    return int(value,16)


def audit(cpu:Path, native:Path, *, cpu_sha:str, native_sha:str,
          first:int=380, last:int=640, require_sealed:bool=True)->dict:
    if not (0 <= first <= last <= 100000 and last-first <= 1000):
        raise ValueError('unsupported original frame interval')
    checked(cpu,cpu_sha)
    checked(native,native_sha)
    if require_sealed and (first,last)!=(380,640):
        raise ValueError('original Stage335/341 capture interval differs')
    cc=load_rows(cpu,CPU_HEADER,'frame',first,last)
    nn=load_rows(native,NATIVE_HEADER,'core_frame_ordinal',first,last)
    counts=Counter(); no_reload=[]; no_scroll=[]
    for frame in range(first,last+1):
        cr=cc[frame]; nr=nn[frame]
        begins=[x for x in cr if x['event']=='frame_begin']
        ends=[x for x in cr if x['event']=='frame_end']
        if len(begins)!=1 or len(ends)!=1 or cr[0] is not begins[0]:
            raise ValueError('CPU movie frame boundaries invalid')
        cpu_start=int(begins[0]['cycle'])
        if cpu_start<0:raise ValueError('negative CPU clock')
        if sum(x['event']=='core_frame_start' for x in nr)!=1 or nr[0]['event']!='core_frame_start':
            raise ValueError('classic core frame anchor invalid')
        if int(nr[0]['cpu_timestamp'])!=0:raise ValueError('classic core frame clock origin invalid')
        prev_ts=-1
        for x in nr:
            ts=int(x['cpu_timestamp'])
            if ts < prev_ts or not 0<=ts<=0xffffffff or int(x['renderer_pixel_not_dot'])!=-1:
                raise ValueError('native event timing not monotonic or falsely labeled PPU dot')
            prev_ts=ts
        cpu_low=[]; high=None; first_scroll=None; scroll_phases=0
        for x in cr:
            e=x['event']
            if e=='W2006':
                phase=x['ppu_toggle_before']
                val=byte_hex(x['value'])
                if phase=='0':
                    if high is not None: raise ValueError('nested CPU $2006 high write')
                    high=val
                elif phase=='1':
                    if high is None: raise ValueError('unpaired low $2006')
                    cpu_low.append((int(x['cycle'])-cpu_start,((high & 0x3f)<<8)|val))
                    high=None
                else:raise ValueError('invalid CPU $2006 write phase')
            if e=='ppu_bus_write':
                phase=x['ppu_toggle_before']
                if phase=='1':
                    scroll_phases+=1
                    if first_scroll is None:first_scroll=x
                elif phase!='0':raise ValueError('invalid $2005 write phase')
            if e=='ram0d_bus_write':counts['ram0d_writes']+=1
        if high is not None:raise ValueError('unpaired CPU $2006 high write')
        ns=[x for x in nr if x['event']=='cpu_second_2006']
        if len(ns)!=len(cpu_low):raise ValueError('CPU/native $2006 event count differs')
        for (cpu_ts,address),y in zip(cpu_low,ns):
            if cpu_ts!=int(y['cpu_timestamp']):
                raise ValueError('same-session CPU/classic PPU timestamp mismatch')
            if address!=(word_hex(y['refresh_addr']) & 0x3fff):
                raise ValueError('same-session CPU/classic PPU full address differs')
        counts['matched_cpu_native_second_2006']+=len(ns)
        reloads=[x for x in nr if x['event']=='legacy_horizontal_reload']
        vertical=[x for x in nr if x['event']=='legacy_vertical_increment']
        if len(reloads)!=len(vertical):raise ValueError('horizontal/vertical classic PPU transition count differs')
        if require_sealed and len(reloads) not in (0,240):
            raise ValueError('original render core transition coverage invalid')
        if not reloads:no_reload.append(frame)
        counts['horizontal_reload']+=len(reloads)
        counts['vertical_increment']+=len(vertical)
        lines=[x for x in nr if x['event']=='legacy_line_start' and x['legacy_scanline']=='0']
        if len(lines)!=1: raise ValueError('missing or duplicated native renderer line zero')
        if first_scroll is None:
            no_scroll.append(frame)
            if scroll_phases:raise ValueError('second-phase $2005 without first scroll')
        else:
            counts['frames_with_first_second_2005']+=1
            if byte_hex(first_scroll['value'])!=byte_hex(first_scroll['ram0d_live']):
                raise ValueError('RAM $0D does not match first second-phase $2005 write')
            counts['first_2005_matches_live_ram0d']+=1
            instant=int(first_scroll['cycle'])-cpu_start
            line0=lines[0]
            if not 0<=instant<int(line0['cpu_timestamp']):
                raise ValueError('first vertical scroll does not precede renderer line zero')
            line_cpu_end=cpu_start+int(line0['cpu_timestamp'])
            # CPU writes that could change t before the sample invalidate causal attribution.
            interventions=[x for x in cr if x['event'] in ('W2006','ppu_bus_write') and
                           int(first_scroll['cycle'])<int(x['cycle'])<line_cpu_end]
            if interventions:
                raise ValueError('intervening PPU temporary-address writes before line zero')
            value=byte_hex(first_scroll['value'])
            predicted_y=((value & 0xf8)<<2)|((value & 7)<<12)
            if (word_hex(line0['temp_addr'])&0x73e0)!=predicted_y:
                raise ValueError('classic PPU temporary vertical bits differ from original $2005')
            counts['first_scroll_vertical_temp_y_matched']+=1
        counts['second_scroll_phases']+=scroll_phases
        counts['native_rows']+=len(nr)
        counts['cpu_rows']+=len(cr)
    if require_sealed:
        expected={'matched_cpu_native_second_2006':3048,'horizontal_reload':60480,
                  'vertical_increment':60480,'first_2005_matches_live_ram0d':253,
                  'first_scroll_vertical_temp_y_matched':253,'native_rows':312189,
                  'cpu_rows':21398,'second_scroll_phases':505,'ram0d_writes':619}
        if any(counts[k]!=v for k,v in expected.items()) or len(no_reload)!=9 or len(no_scroll)!=8:
            raise ValueError('original sealed Stage335/341 aggregate baseline mismatch')
    return {
        'format':'vpd_stage342_original_classic_ppu_scroll_chain_aggregate_v1',
        'stage':342,'source_frame_count':last-first+1,
        'same_session_cpu_ppu_event_clock_matches':counts['matched_cpu_native_second_2006'],
        'same_session_cpu_ppu_event_clock_mismatches':0,
        'first_second_phase_scroll_matches_live_ram0d':counts['first_2005_matches_live_ram0d'],
        'first_scroll_to_classic_line0_temp_vertical_bit_matches':counts['first_scroll_vertical_temp_y_matched'],
        'native_horizontal_reload_events':counts['horizontal_reload'],
        'native_vertical_increment_events':counts['vertical_increment'],
        'frames_with_render_transitions':last-first+1-len(no_reload),
        'frames_without_render_transitions':len(no_reload),
        'frames_without_scroll_writes':len(no_scroll),
        'private_native_rows_verified':counts['native_rows'],
        'private_cpu_rows_verified':counts['cpu_rows'],
        'source_authentication_sha256_verified':True,
        'classic_renderer_internal_address_observed':True,
        'exact_ppu_hardware_dot_observed':False,
        'per_pixel_road_scroll_proven':False,
        'road_geometry_or_collision_proven':False,
        'private_ppu_or_controller_values_disclosed':False
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cpu',required=True,type=Path)
    p.add_argument('--native',required=True,type=Path)
    p.add_argument('--cpu-sha256',required=True)
    p.add_argument('--native-sha256',required=True)
    p.add_argument('--first',type=int,default=380)
    p.add_argument('--last',type=int,default=640)
    p.add_argument('--synthetic-baseline',action='store_true')
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        obj=audit(a.cpu,a.native,cpu_sha=a.cpu_sha256,native_sha=a.native_sha256,
                  first=a.first,last=a.last,require_sealed=not a.synthetic_baseline)
        data=json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n'
        if a.output:
            if a.output.is_symlink() or a.output.exists():raise ValueError('refusing overwrite')
            with a.output.open('x',encoding='utf8') as f:f.write(data)
        else:print(data,end='')
    except (OSError,ValueError,UnicodeError,KeyError):
        p.exit(1,'VPD_STAGE342_ORIGINAL_SCROLL_CHAIN_INCONCLUSIVE\n')
if __name__=='__main__':main()
