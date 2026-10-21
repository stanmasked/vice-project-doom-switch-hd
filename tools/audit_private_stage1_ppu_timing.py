#!/usr/bin/env python3
"""Audit PRIVATE FCEUX CPU $2005 writes vs private road RGB measurements.

This script and its public tests contain no original ROM, FM2 or screenshots.
CPU video register writes do NOT establish effective on-screen PPU scroll.
"""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re

HEX4=re.compile(r'[0-9A-Fa-f]{4}\Z')
HEX2=re.compile(r'[0-9A-Fa-f]{2}\Z')
NUM=re.compile(r'(?:0|[1-9][0-9]*)\Z')
EVENT_COLS=['frame','cycles','address','value','kind']
RAM_COLS=['frame','ram_0b','ram_0c','ram_0d','video_event_count']
MAX_SIZE=64*1024*1024


def _input_file(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or not 0<p.stat().st_size<=MAX_SIZE:
        raise ValueError('private data input missing, linked or oversized')
    return p


def _decimal(value,name):
    if type(value) is not str or not NUM.fullmatch(value):
        raise ValueError('invalid numeric '+name)
    return int(value)


def _hex(value,pattern,name):
    if type(value) is not str or not pattern.fullmatch(value):
        raise ValueError('invalid '+name)
    return int(value,16)


def read_events(path,start,stop):
    events=defaultdict(list)
    counts=Counter()
    last_frame=-1
    last_cycles=None
    cycle_available=True
    with _input_file(path).open('r',encoding='ascii',newline='') as file:
        rows=csv.DictReader(file,delimiter='\t')
        if rows.fieldnames!=EVENT_COLS:
            raise ValueError('invalid FCEUX event TSV schema')
        for n,row in enumerate(rows,1):
            if n>2_000_000 or None in row or any(v is None for v in row.values()):
                raise ValueError('oversized or malformed event trace')
            frame=_decimal(row['frame'],'frame')
            if frame<last_frame:
                raise ValueError('FCEUX events out of frame order')
            last_frame=frame
            cycle_text=row['cycles']
            cycles=None if cycle_text=='unknown' else _decimal(cycle_text,'CPU cycle')
            if cycles is None:
                cycle_available=False
            elif last_cycles is not None and cycles<last_cycles:
                raise ValueError('CPU cycle count went backwards; epoch not resolved')
            if cycles is not None:last_cycles=cycles
            address=_hex(row['address'],HEX4,'address')
            value=_hex(row['value'],HEX2,'value')
            kind=row['kind']
            if kind not in ('R','W'):
                raise ValueError('invalid event kind')
            if kind=='R' and address!=0x2002:
                raise ValueError('unrecognized CPU-read marker')
            if start<=frame<=stop:
                counts[(address,kind)]+=1
                if address in (0x2000,0x2002,0x2005,0x2006):
                    events[frame].append((cycles,address,value,kind))
    return events,counts,cycle_available


def read_ram(path,start,stop):
    samples={}
    previous_frame=-1
    previous_index=-1
    with _input_file(path).open('r',encoding='ascii',newline='') as file:
        rows=csv.DictReader(file,delimiter='\t')
        if rows.fieldnames!=RAM_COLS:
            raise ValueError('invalid FCEUX RAM sample TSV schema')
        for n,row in enumerate(rows,1):
            if n>10000 or None in row or any(v is None for v in row.values()):
                raise ValueError('oversized or malformed RAM samples')
            frame=_decimal(row['frame'],'RAM frame')
            if frame<=previous_frame:
                raise ValueError('RAM samples not strictly ordered')
            previous_frame=frame
            index=_decimal(row['video_event_count'],'event index')
            if index<previous_index:
                raise ValueError('RAM event index went backwards')
            previous_index=index
            values=tuple(_hex(row[k],HEX2,k) for k in RAM_COLS[1:4])
            if start<=frame<=stop:
                samples[frame]=values
    return samples


def read_road(path,start,stop):
    if path is None:return {}
    report=json.loads(_input_file(path).read_text('utf-8'))
    if report.get('schema')!='vice-stage1-private-road-mask-scan-v1':
        raise ValueError('unexpected private road observation schema')
    found={}
    for obj in report.get('frames',[]):
        frame=obj.get('frame')
        if type(frame)is not int or frame in found:
            raise ValueError('invalid or duplicate roadway frame')
        if start<=frame<=stop and obj.get('roi_valid'):
            width=obj.get('observed_width')
            center=obj.get('observed_center_x')
            if (type(width)is not int or not 1<=width<=256
                or type(center) not in (int,float) or not 0<=center<=255):
                raise ValueError('invalid road pixel measurement')
            found[frame]=(width,center)
    return found


def audit(events_path,ram_path,*,start=600,stop=920,road_path=None,
          require_four=True,selected_frames=(600,744,800,920)):
    if (type(start)is not int or type(stop)is not int or start<0 or
        stop<start or stop-start>1200):
        raise ValueError('invalid private sampling window')
    events,counts,cycle_available=read_events(events_path,start,stop)
    ram=read_ram(ram_path,start,stop)
    road=read_road(road_path,start,stop)
    pattern_count=0
    pair_gaps=[]
    per_frame={}
    for frame in range(start,stop+1):
        writes=[(cy,val) for cy,addr,val,kind in events.get(frame,[])
                if addr==0x2005 and kind=='W']
        values=[val for cy,val in writes]
        if require_four and len(writes)!=4:
            raise ValueError('incomplete or unexpected $2005 write count')
        if len(writes)==4 and values[0]==0 and values[2:]==[0,0]:
            pattern_count+=1
        elif require_four:
            raise ValueError('original Stage 1-1 $2005 sequence differs from observed contract')
        if cycle_available and len(writes)>=2:
            gap=writes[1][0]-writes[0][0]
            if gap<0:raise ValueError('reversed first scroll write pair')
            pair_gaps.append(gap)
        per_frame[frame]={'scroll_writes':len(writes),
                          'candidate_second_value':values[1] if len(values)>1 else None}
    if not ram:
        raise ValueError('no matching RAM samples')
    if road_path is not None and not road:
        raise ValueError('no valid road observations in sampling window')
    observations=[]
    for frame in selected_frames:
        if frame not in per_frame or frame not in ram:continue
        item={'frame':frame,
              'raw_2005_second_write':per_frame[frame]['candidate_second_value'],
              'postframe_ram_0b':ram[frame][0],
              'postframe_ram_0c':ram[frame][1],
              'postframe_ram_0d':ram[frame][2]}
        if frame in road:
            item['observed_road_width_pixels']=road[frame][0]
            item['observed_road_center_x']=road[frame][1]
        observations.append(item)
    return {
        'classification':'PRIVATE FCEUX CPU video write / road RGB correlation, not rendered-scroll proof',
        'frame_start':start,'frame_stop':stop,'frames_checked':stop-start+1,
        'scroll_2005_write_count':counts[(0x2005,'W')],
        'ppu_control_write_count':counts[(0x2000,'W')],
        'ppu_address_write_count':counts[(0x2006,'W')],
        'ppu_data_write_count':counts[(0x2007,'W')],
        'frames_with_four_zero_value_pattern':pattern_count,
        'ram_postframe_sample_count':len(ram),
        'road_rgb_valid_sample_count':len(road),
        'cpu_cycle_counter_available':cycle_available,
        'first_2005_gap_cycles_unique':sorted(set(pair_gaps)),
        'read_2002_events_recorded':counts[(0x2002,'R')],
        'status_read_markers_present':counts[(0x2002,'R')]>0,
        'ppu_latch_origin_verified':False,
        'display_effective_scroll_proven':False,
        'camera_speed_proven':False,
        'roadway_collision_width_proven':False,
        'source_files_copied_to_repository':False,
        'representative_observations':observations,
        'limitations':[
          'Original FCEUX Lua lacked memory.registerread; no PPUSTATUS latch-reset witness',
          'CPU $2005 writes and postframe RAM values do not prove effective rendered scroll',
          'Raster splits, MMC3 IRQ and PPUADDR writes may change visible scroll',
          'Road RGB segmentation measures displayed pixels, not camera velocity',
          'Keep original ROM/FM2/screenshots and raw event/RAM TSV private'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('private_cpu_events',type=Path)
    p.add_argument('private_ram_samples',type=Path)
    p.add_argument('--private-road-observations',type=Path)
    p.add_argument('--start-frame',type=int,default=600)
    p.add_argument('--stop-frame',type=int,default=920)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    try:
        result=audit(a.private_cpu_events,a.private_ram_samples,
                     start=a.start_frame,stop=a.stop_frame,
                     road_path=a.private_road_observations)
        if a.out is not None:
            if a.out.is_symlink() or a.out.exists() or not a.out.parent.is_dir():
                raise ValueError('private report output must be a NEW local file')
            with a.out.open('x',encoding='utf-8') as file:
                json.dump(result,file,indent=2)
                file.write('\n')
    except (ValueError,OSError,UnicodeError) as exc:
        p.exit(1,'PRIVATE_STAGE1_PPU_INCONCLUSIVE: '+str(exc)+'\n')
    print('PRIVATE_STAGE1_PPU_CPU_EVENT_AUDIT_PASS')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
