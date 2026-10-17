#!/usr/bin/env python3
"""Conservative PPU scroll latch reconstruction from private FCEUX event log.

The log includes PPUSTATUS reads ($2002, dummy value 00) and PPU
$2000/$2005/$2006 writes. The output is a *last observed CPU register
state*, not an effective rendered-frame scroll or a scanline-level trace.
"""
import argparse
import json
from pathlib import Path
from analyze_mmc3_frame_log import read_events


def analyze(events):
    latch=None  # $2005/$2006 share w; unknown until first observed $2002 read
    pending_x=None
    chosen_nt=None
    last_pair=None
    previous=-1
    frames=[]
    current=None
    out_of_order=False
    for frame,address,value in events:
        if frame<previous:out_of_order=True
        if current is None or frame!=previous:
            current={'frame':frame,'status_reads':0,'scroll_writes':0,
                     'address_writes':0,'completed_scroll_pairs':0,
                     'unresolved_scroll_writes':0}
            frames.append(current)
        previous=frame
        # CPU PPU register mirrors use the low three address bits.
        port=0x2000+(address-0x2000)%8 if 0x2000<=address<=0x3FFF else address
        if port==0x2002:  # CPU read of PPUSTATUS resets shared write toggle
            latch=0
            pending_x=None
            current['status_reads']+=1
        elif port==0x2000:
            chosen_nt=value&3
        elif port==0x2006:
            current['address_writes']+=1
            if latch is None:
                pending_x=None
            else:
                latch=1-latch
                pending_x=None
        elif port==0x2005:
            current['scroll_writes']+=1
            if latch is None:
                current['unresolved_scroll_writes']+=1
            elif latch==0:
                pending_x=value
                latch=1
            else:
                if pending_x is not None:
                    last_pair=(pending_x,value)
                    current['completed_scroll_pairs']+=1
                else:
                    current['unresolved_scroll_writes']+=1
                pending_x=None
                latch=0
        current['last_observed_nametable']=chosen_nt
        current['last_complete_scroll_pair']=(
            {'x':last_pair[0],'y':last_pair[1],
             'normal_vertical_range':last_pair[1]<=239}
            if last_pair is not None else None)
        current['write_toggle_synchronized']=latch is not None
    return {
        'frames':frames,
        'number_of_frames_with_events':len(frames),
        'total_complete_scroll_pairs':sum(x['completed_scroll_pairs'] for x in frames),
        'out_of_order_frame_numbers':out_of_order,
        'limitations':[
            'Last observed scroll is not necessarily effective rendered-frame scroll',
            'CPU frame numbers do not identify scanline/cycle timing or raster splits',
            'Write toggle is unknown until first logged $2002 read',
            'PPUADDR writes share and can interrupt PPUSCROLL write pairs',
            'Y=240..255 requires attribute-byte fetch behavior, not simple 2x2 mapping',
            'Register log with dropped events is unsuitable for timing conclusions'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('log',type=Path,help='Private FCEUX MMC3/PPU event TSV')
    p.add_argument('--metadata',type=Path,
                   help='Capture .meta.txt to reject incomplete register logging')
    p.add_argument('--out',type=Path,default=Path('private/ppu_scroll_summary.json'))
    args=p.parse_args()
    if args.metadata is not None:
        metadata={}
        for line in args.metadata.read_text(encoding='utf8').splitlines():
            if '=' in line:
                k,v=line.split('=',1)
                metadata[k]=v
        if metadata.get('register_log_complete')!='yes':
            p.error('Incomplete or unverified register log; no trustworthy scroll trace')
        if (metadata.get('mmc3_write_coverage')!='full_8000_ffff_even_odd'
                or metadata.get('callback_errors')!='0'):
            p.error('Missing full MMC3 write coverage or callback integrity')
        if (metadata.get('ppu_register_write_coverage')!='full_2000_3fff_mod8'
                or metadata.get('ppu_status_read_coverage')!='full_2000_3fff_mod8'):
            p.error('Incomplete PPU register mirror observation')
    report=analyze(read_events(args.log))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'output':str(args.out),
        'complete_pairs':report['total_complete_scroll_pairs'],
        'warning':'Observed CPU writes; NOT actual per-scanline scroll'},indent=2))


if __name__=='__main__':main()
