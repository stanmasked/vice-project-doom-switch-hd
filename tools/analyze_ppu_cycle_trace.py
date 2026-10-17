#!/usr/bin/env python3
"""Analyze private CPU-cycle-timestamped FCEUX MMC3/PPU events.

FCEUX debugger.getcyclescount() timestamps are elapsed CPU cycles since
power-on or explicit counter reset. They are NOT PPU dot/scanline numbers.
This tool does not assert that logged writes were visible on a given scanline.
"""
import argparse
import json
from pathlib import Path
from verify_ppu_capture_session import verify

HEADER = 'frame\tcpu_cycle\taddress\tvalue\tkind'


def parse_events(path):
    with Path(path).open('r',encoding='utf8') as stream:
        if stream.readline().rstrip('\r\n')!=HEADER:
            raise ValueError('Expected CPU-cycle trace header')
        for lineno,line in enumerate(stream,2):
            if not line.strip():
                continue
            fields=line.rstrip('\r\n').split('\t')
            if len(fields)!=5:
                raise ValueError('Invalid event column count at line %d'%lineno)
            frame_s,clock_s,addr_s,value_s,kind=fields
            try:
                frame=int(frame_s,10)
                cycle=int(clock_s,10)
                addr=int(addr_s,16)
                value=int(value_s,16)
            except ValueError:
                raise ValueError('Invalid numeric event at line %d'%lineno) from None
            if not (frame>=0 and cycle>=0 and 0<=addr<=65535
                    and 0<=value<=255 and kind in ('W','R')):
                raise ValueError('Invalid event range/kind at line %d'%lineno)
            if kind=='R' and (not 0x2000<=addr<=0x3FFF
                              or (addr-0x2000)%8!=2 or value!=0):
                raise ValueError('Unexpected read marker at line %d'%lineno)
            yield frame,cycle,addr,value,kind


def summarize(events):
    frames=[]
    # Event-frame transitions are not physical frame-boundary timestamps.
    frame_boundary_observations=[]
    unobserved_frame_labels=0
    last_frame=None
    last_cycle=None
    counter_epoch=0
    epoch_resets=0
    same_frame_regressions=0
    cross_frame_regressions=0
    equal_adjacent=0
    frame_order_error=False
    selection=None
    chr_regs=[None]*6
    inversion=None
    current=None
    total=0
    unknown_bank_writes=0
    global_chr_events=[]
    for frame,cycle,address,value,kind in events:
        if last_frame is not None and frame<last_frame:
            frame_order_error=True
        if last_cycle is not None and cycle<last_cycle:
            epoch_resets+=1
            counter_epoch+=1
        if current is None or frame!=last_frame:
            if last_frame is not None:
                frame_delta=frame-last_frame
                # The interval between two logged events is observable;
                # neither event establishes the start/end of a PPU frame.
                valid_interval=frame_delta>0 and cycle>=last_cycle
                event_gap=cycle-last_cycle if valid_interval else None
                if frame_delta>1:
                    unobserved_frame_labels+=frame_delta-1
                frame_boundary_observations.append({
                    'previous_event_frame':last_frame,
                    'current_event_frame':frame,
                    'frame_label_delta':frame_delta,
                    'last_logged_cycle_previous_frame':last_cycle,
                    'first_logged_cycle_current_frame':cycle,
                    'cycles_between_adjacent_logged_events':event_gap,
                    'cpu_counter_discontinuity':cycle<last_cycle,
                    'frame_labels_skipped_without_events':max(0,frame_delta-1),
                    'physical_frame_start_cycle':None,
                    'physical_frame_duration_cycles':None,
                })
            current={'frame':frame,'cpu_clock_first_event':cycle,
                     'cpu_clock_last_event':cycle,'event_count':0,
                     'chr_events':[],'scroll_write_count':0,
                     'ppu_status_reads':0,'mapper_writes':0,
                     'cpu_clock_equal_adjacent':0,
                     'cpu_clock_regressions_within_frame':0,
                     'cpu_clock_regressions_from_previous_frame':0}
            frames.append(current)
        if last_cycle is not None:
            if cycle<last_cycle:
                if frame==last_frame:
                    same_frame_regressions+=1
                    current['cpu_clock_regressions_within_frame']+=1
                else:
                    cross_frame_regressions+=1
                    current['cpu_clock_regressions_from_previous_frame']+=1
            elif cycle==last_cycle:
                equal_adjacent+=1
                current['cpu_clock_equal_adjacent']+=1
        current['cpu_clock_last_event']=cycle
        current['event_count']+=1
        total+=1
        relative=cycle-current['cpu_clock_first_event']
        if relative<0:
            relative=None
        point={'cpu_cycle':cycle,'counter_epoch':counter_epoch,
               'cycles_since_first_logged_event_this_frame':relative}
        if kind=='R':
            current['ppu_status_reads']+=1
        elif 0x8000<=address<=0x9FFF and address%2==0:
            selection=value&7
            inversion=bool(value&0x80)
            current['mapper_writes']+=1
        elif 0x8000<=address<=0x9FFF and address%2==1:
            current['mapper_writes']+=1
            if selection is None:
                unknown_bank_writes+=1
            elif selection<=5:
                chr_regs[selection]=value
                event={**point,'register':selection,'bank_value':value,
                       'chr_inversion':inversion}
                current['chr_events'].append(event)
                global_chr_events.append({'frame':frame,**event})
        elif 0x2000<=address<=0x3FFF and (address-0x2000)%8==5:
            current['scroll_write_count']+=1
        current['observed_chr_registers']=list(chr_regs)
        current['chr_inversion']=inversion
        current['has_all_chr_register_values']=all(v is not None for v in chr_regs)
        last_frame,last_cycle=frame,cycle

    return {
        'format':'fceux_cycle_trace_v1',
        'frames':frames,
        'total_events':total,
        'frame_boundary_observations':frame_boundary_observations,
        'frame_transition_count':len(frame_boundary_observations),
        'frame_labels_skipped_without_events':unobserved_frame_labels,
        'frame_start_cycle_proven':False,
        'ppu_scanline_position_proven':False,
        'chr_events':global_chr_events,
        'cpu_clock_resets_or_discontinuities':epoch_resets,
        'cpu_clock_decreases_same_frame':same_frame_regressions,
        'cpu_clock_decreases_between_frames':cross_frame_regressions,
        'cpu_clock_equal_adjacent':equal_adjacent,
        'counter_reset_proven':False,
        'out_of_order_frame_numbers':frame_order_error,
        'unpaired_mmc3_data_writes':unknown_bank_writes,
        'frames_with_all_six_chr_values':sum(
            frame['has_all_chr_register_values'] for frame in frames),
        'limitations':[
            'CPU cycle offset is measured relative to first *logged event*, not frame start',
            'Frame transitions are changes of event frame labels, not measured PPU frame boundaries',
            'Skipped frame labels may contain no logged register accesses and do not prove missed video frames',
            'Cross-frame logged-event intervals are not physical frame duration estimates',
            'PPU scanline/dot offset cannot be derived reliably from frame labels alone',
            'A decreasing CPU counter is a possible reset/restart or trace anomaly, not proof of an actual reset',
            'Cross-discontinuity cycle intervals cannot be certified',
            'Existing CHR state is unknown until all six registers are observed',
            'Dropped-event capture logs cannot establish full raster timing'
        ]
    }


def check_capture_meta(path):
    metadata={}
    for line in Path(path).read_text(encoding='utf8').splitlines():
        if '=' in line:
            key,value=line.split('=',1)
            metadata[key]=value
    if metadata.get('register_log_complete')!='yes':
        raise ValueError('Register log contains dropped or unverified events')
    if metadata.get('cycle_trace_available')!='yes':
        raise ValueError('No FCEUX debugger CPU-cycle timestamps available')
    if metadata.get('mmc3_write_coverage')!='full_8000_ffff_even_odd':
        raise ValueError('Incomplete MMC3 mirrored register coverage')
    if metadata.get('callback_errors')!='0':
        raise ValueError('Unverified callback integrity')
    if (metadata.get('ppu_register_write_coverage')!='full_2000_3fff_mod8'
            or metadata.get('ppu_status_read_coverage')!='full_2000_3fff_mod8'):
        raise ValueError('Incomplete PPU register mirror observation')
    return metadata


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('cycle_log',type=Path)
    p.add_argument('--metadata',type=Path,required=True,
                   help='Per-frame metadata (frame prefix only)')
    p.add_argument('--session-meta',type=Path,required=True,
                   help='Finalized PPU session manifest required for cycle trace')
    p.add_argument('--out',type=Path,default=Path('private/ppu_cycles_report.json'))
    args=p.parse_args()
    check_capture_meta(args.metadata)
    if args.cycle_log.resolve()!=(args.session_meta.parent/'mmc3_ppu_cycles.tsv').resolve():
        p.error('Cycle trace path does not belong to selected session')
    session=verify(args.session_meta,require_cycle=True)
    frame_metas={(args.session_meta.parent/f'frame_{frame:06d}.meta.txt').resolve()
                 for frame in session['capture_frames']}
    if args.metadata.resolve() not in frame_metas:
        p.error('Selected per-frame metadata is not in this session')
    result=summarize(parse_events(args.cycle_log))
    result['session_verified']=session['complete']
    result['frame_callback_span']=session['frame_callback_span']
    result['cpu_cycle_order_verified']=session['cpu_cycle_order_verified']
    result['cpu_clock_equal_adjacent_verified']=session['cpu_cycle_equal_adjacent']
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'report':str(args.out),
         'events':result['total_events'],
         'chr_writes':len(result['chr_events']),
         'cpu_cycle_epoch_resets':result['cpu_clock_resets_or_discontinuities'],
         'warning':'CPU cycle timeline only; actual NES scanline timing not proven'},indent=2))


if __name__=='__main__':
    main()
