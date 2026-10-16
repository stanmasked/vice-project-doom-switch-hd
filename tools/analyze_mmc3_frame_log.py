#!/usr/bin/env python3
"""Summarize FCEUX MMC3 writes by frame; not a scanline-resolution NES trace.

Original log files and derived reports are private. Synthetic CI contains
only invented bank values. Missing register writes are never guessed.
"""
import argparse,json
from pathlib import Path

def read_events(path):
    with Path(path).open(encoding='utf8') as f:
        if f.readline().strip()!='frame\taddress\tvalue':
            raise ValueError('Expected frame/address/value TSV header')
        for line_number,line in enumerate(f,2):
            if not line.strip():continue
            parts=line.strip().split('\t')
            if len(parts)!=3:raise ValueError('Invalid row at line %d'%line_number)
            try:
                frame=int(parts[0])
                address=int(parts[1],16)
                value=int(parts[2],16)
            except ValueError:
                raise ValueError('Invalid register event at line %d'%line_number) from None
            if frame<0 or not 0<=address<=65535 or not 0<=value<=255:
                raise ValueError('Out-of-range register event at line %d'%line_number)
            yield frame,address,value

def chr_1k_banks(values,inversion,count=128):
    if len(values)!=6 or any(x is None for x in values):return None
    if count<=0 or count&(count-1):
        raise ValueError('Physical CHR bank count must be a power of two')
    a,b=values[0]&0xfe,values[1]&0xfe
    slots=[a,a+1,b,b+1,values[2],values[3],values[4],values[5]]
    if inversion:slots=slots[4:]+slots[:4]
    return [x&(count-1) for x in slots]

def analyze(events,bank_count=128):
    if bank_count<=0 or bank_count&(bank_count-1):
        raise ValueError('CHR bank count must be a power of two')
    selection=None
    registers=[None]*6
    inversion=None
    prg_mode=None
    previous=None
    frames=[]
    unpaired=0
    backwards=False
    current=None
    for frame,address,value in events:
        if previous is not None and frame<previous:backwards=True
        if current is None or frame!=previous:
            current={'frame':frame,'ppu_port_writes':0,'chr_changes':[],
                     'mapper_select_writes':0,'unpaired_data_writes':0}
            frames.append(current)
        previous=frame
        if address in (0x2000,0x2001,0x2005,0x2006,0x2007):
            current['ppu_port_writes']+=1
        if address==0x8000:
            selection=value&7
            inversion=bool(value&0x80)
            prg_mode=bool(value&0x40)
            current['mapper_select_writes']+=1
        elif address==0x8001:
            if selection is None:
                unpaired+=1
                current['unpaired_data_writes']+=1
            elif selection<=5:
                registers[selection]=value
                current['chr_changes'].append({
                    'register':selection,'bank_value':value,
                    'chr_inversion':inversion})
        current['chr_registers']=list(registers)
        current['chr_inversion']=inversion
        current['prg_mode']=prg_mode
        current['ppu_1k_bank_mapping']=(
            chr_1k_banks(registers,inversion,bank_count)
            if inversion is not None else None)
    return {
        'frames':frames,'event_frame_count':len(frames),
        'total_chr_writes':sum(len(f['chr_changes']) for f in frames),
        'unpaired_bank_data_writes':unpaired,
        'out_of_order_frame_numbers':backwards,
        'mapping_available_for_frames':sum(
            f['ppu_1k_bank_mapping'] is not None for f in frames),
        'limitations':[
            'Frame-only register log has no scanline or CPU cycle positions',
            'Missing initial register writes mean unobserved state is unknown',
            'Logs with dropped_register_writes > 0 are not timing evidence',
            'Bank values are not a reconstruction of original level geometry'
        ]}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('register_log',type=Path)
    ap.add_argument('--chr-1k-banks',type=int,default=128)
    ap.add_argument('--out',type=Path,default=Path('private/mmc3_frame_summary.json'))
    args=ap.parse_args()
    report=analyze(read_events(args.register_log),args.chr_1k_banks)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'report':str(args.out),
        'frames':report['event_frame_count'],
        'chr_writes':report['total_chr_writes'],
        'fully_observed_frames':report['mapping_available_for_frames'],
        'warning':'Keep register logs and reports private'},indent=2))

if __name__=='__main__':main()
