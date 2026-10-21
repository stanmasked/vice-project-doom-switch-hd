#!/usr/bin/env python3
"""Strict, ROM-private validation of FCEUX register and CPU-cycle TSV logs.

Return only counts/booleans; NEVER serialize raw events, hashes, RAM or ROM data.
All limits follow tools/capture_fceux_ppu.lua (250000 emitted events per run).
"""
from itertools import zip_longest
from pathlib import Path
import re

ALLOWED_ADDRESSES={
    0x2000,0x2001,0x2002,0x2005,0x2006,0x2007,
    0x8000,0x8001,0xA000,0xC000,0xC001,0xE000,0xE001
}
VIDEO_HEADER="frame\taddress\tvalue"
CYCLE_HEADER="frame\tcpu_cycle\taddress\tvalue\tkind"
MAX_EVENTS=250000
MAX_EVENTS_PER_FRAME=12000
MAX_VIDEO_BYTES=16*1024*1024
MAX_CYCLE_BYTES=24*1024*1024
DECIMAL=re.compile(r"0|[1-9][0-9]*\Z")
HEX4=re.compile(r"[0-9A-F]{4}\Z")
HEX2=re.compile(r"[0-9A-F]{2}\Z")


def safe_lines(path,expected_header,max_bytes):
    if path.is_symlink() or not path.is_file():
        raise ValueError("required register trace is missing or linked: "+path.name)
    if path.stat().st_size>max_bytes:
        raise ValueError("register trace exceeds size limit: "+path.name)
    with path.open("r",encoding="ascii",newline="") as stream:
        if stream.readline().rstrip("\r\n")!=expected_header:
            raise ValueError("invalid register trace header: "+path.name)
        for line in stream:
            yield line.rstrip("\r\n")


def decimal(value,upper):
    if not DECIMAL.fullmatch(value):
        raise ValueError("invalid numeric register trace field")
    parsed=int(value)
    if parsed>upper:
        raise ValueError("register trace field exceeds supported bound")
    return parsed


def video_events(path):
    previous=-1
    per_frame_events=0
    for i,line in enumerate(safe_lines(path,VIDEO_HEADER,MAX_VIDEO_BYTES),start=1):
        if i>MAX_EVENTS:
            raise ValueError("register trace exceeds FCEUX capture event cap")
        columns=line.split("\t")
        if len(columns)!=3 or not HEX4.fullmatch(columns[1]) or not HEX2.fullmatch(columns[2]):
            raise ValueError("malformed register trace event")
        frame=decimal(columns[0],999999999)
        addr=int(columns[1],16)
        if addr not in ALLOWED_ADDRESSES:
            raise ValueError("unexpected register address in private trace")
        if addr==0x2002 and columns[2]!="00":
            raise ValueError("PPUSTATUS synthetic read marker must have zero value")
        if frame<previous:
            raise ValueError("register trace frame ordering regressed")
        if frame!=previous:
            per_frame_events=0
        per_frame_events+=1
        if per_frame_events>MAX_EVENTS_PER_FRAME:
            raise ValueError("register trace exceeds FCEUX per-frame event cap")
        previous=frame
        yield (frame,columns[1],columns[2])


def verify_trace_alignment(root,samples,cycle_available):
    """samples are pairs (captured_frame, cumulative_logged_register_writes)."""
    root=Path(root)
    if cycle_available is None:
        raise ValueError("trace provenance requires capture schema v4")
    video_path=root/"mmc3_video_writes.tsv"
    cycles_path=root/"mmc3_ppu_cycles.tsv"
    # Fully validate ordering, syntax and event budget before checking
    # sampled cumulative counters. Otherwise an out-of-order trace can
    # produce a misleading count mismatch before the regression is detected.
    # video_events is bounded to 250000 rows, already held for cycle matching.
    observed=list(video_events(video_path))
    seen=0
    sample_index=0
    for frame,addr,value in observed:
        while sample_index<len(samples) and frame>samples[sample_index][0]:
            if seen!=samples[sample_index][1]:
                raise ValueError("cumulative register event count differs from capture metadata")
            sample_index+=1
        seen+=1
    while sample_index<len(samples):
        if seen!=samples[sample_index][1]:
            raise ValueError("cumulative register event count differs from capture metadata")
        sample_index+=1
    if cycle_available:
        previous_frame=-1
        previous_cycle=0
        count=0
        for actual,record in zip_longest(
            observed,safe_lines(cycles_path,CYCLE_HEADER,MAX_CYCLE_BYTES)
        ):
            if actual is None or record is None:
                raise ValueError("CPU-cycle and register trace row counts differ")
            fields=record.split("\t")
            if len(fields)!=5 or not HEX4.fullmatch(fields[2]) or not HEX2.fullmatch(fields[3]):
                raise ValueError("malformed CPU-cycle trace event")
            frame=decimal(fields[0],999999999)
            cpu_cycle=decimal(fields[1],10**16)
            kind=fields[4]
            if (frame,fields[2],fields[3])!=actual:
                raise ValueError("CPU-cycle and register event mismatch")
            if kind!=("R" if fields[2]=="2002" else "W"):
                raise ValueError("CPU-cycle trace has inconsistent read/write kind")
            if frame==previous_frame and cpu_cycle<previous_cycle:
                raise ValueError("CPU-cycle order regressed within one frame")
            previous_frame=frame
            previous_cycle=cpu_cycle
            count+=1
        if count!=seen:
            raise ValueError("CPU-cycle and register trace row counts differ")
    elif cycles_path.exists() or cycles_path.is_symlink():
        raise ValueError("unexpected CPU-cycle trace despite disabled clock")
    return {"register_trace_verified":True,"cpu_cycle_trace_verified":bool(cycle_available),
            "verified_register_events":seen}
