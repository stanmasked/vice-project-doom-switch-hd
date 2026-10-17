#!/usr/bin/env python3
"""Fail-closed verification of FCEUX PPU capture session consistency.

Does not authenticate original ROM identity or prove frame timing, game stage,
or PPU scanline accuracy. Uses only private local capture files.
"""
import argparse
import json
import re
from pathlib import Path

HEX4 = re.compile(r'[0-9A-F]{4}\Z')
HEX2 = re.compile(r'[0-9A-F]{2}\Z')
SESSION = re.compile(r'[0-9a-f]{16}\Z')
DEC = re.compile(r'(0|[1-9][0-9]*)\Z')


class SessionError(ValueError):
    pass


def metadata(path):
    path = Path(path)
    try:
        contents = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        raise SessionError(f'Missing/unreadable metadata {path.name}: {exc}') from exc
    if not contents.endswith('\n'):
        raise SessionError(f'Truncated metadata {path.name}')
    props = {}
    for line in contents.splitlines():
        if line.count('=') != 1:
            raise SessionError(f'Invalid metadata row in {path.name}')
        key, value = line.split('=', 1)
        if not key or key in props:
            raise SessionError(f'Duplicate/empty metadata key in {path.name}')
        props[key] = value
    return props


def required(d, key, expected):
    if d.get(key) != expected:
        raise SessionError(f'{key} must be {expected!r}')


def integer(d, key, minimum=0):
    text = d.get(key, '')
    if DEC.fullmatch(text) is None:
        raise SessionError(f'Invalid integer for {key}')
    value = int(text)
    if value < minimum:
        raise SessionError(f'{key} below minimum {minimum}')
    return value


def check_tsv(path, header, columns):
    try:
        stream = Path(path).open('r', encoding='utf-8', newline='')
    except (OSError, UnicodeError) as exc:
        raise SessionError(f'Missing event stream {Path(path).name}: {exc}') from exc
    with stream:
        if stream.readline() != header + '\n':
            raise SessionError(f'Incorrect event header in {Path(path).name}')
        for lineno, line in enumerate(stream, 2):
            if not line.endswith('\n'):
                raise SessionError(f'Truncated event record at line {lineno}')
            fields = line[:-1].split('\t')
            if len(fields) != columns:
                raise SessionError(f'Wrong event column count at line {lineno}')
            yield lineno, fields


def read_frame_events(path):
    events = []
    previous = -1
    for lineno, row in check_tsv(path, 'frame\taddress\tvalue', 3):
        frame_s, addr_s, value_s = row
        if DEC.fullmatch(frame_s) is None or HEX4.fullmatch(addr_s) is None or HEX2.fullmatch(value_s) is None:
            raise SessionError(f'Invalid frame event at line {lineno}')
        frame, addr, value = int(frame_s), int(addr_s, 16), int(value_s, 16)
        if frame < previous:
            raise SessionError('Out-of-order event frame')
        if 0x2000 <= addr <= 0x3FFF:
            if ((addr - 0x2000) % 8) not in (0, 1, 2, 5, 6, 7):
                raise SessionError(f'Unexpected PPU read-only/unused port at line {lineno}')
            if (addr-0x2000) % 8 == 2 and value != 0:
                raise SessionError('PPUSTATUS marker cannot contain bus byte')
        elif not 0x8000 <= addr <= 0xFFFF:
            raise SessionError(f'Unrecognized captured register at line {lineno}')
        events.append((frame, addr, value))
        previous = frame
    return events


def check_cycle_events(path, events):
    count = 0
    for lineno, row in check_tsv(path, 'frame\tcpu_cycle\taddress\tvalue\tkind', 5):
        frame_s, cycle_s, addr_s, value_s, kind = row
        if (DEC.fullmatch(frame_s) is None or DEC.fullmatch(cycle_s) is None
                or HEX4.fullmatch(addr_s) is None or HEX2.fullmatch(value_s) is None):
            raise SessionError(f'Invalid CPU-cycle event at line {lineno}')
        if count >= len(events) or (int(frame_s), int(addr_s,16), int(value_s,16)) != events[count]:
            raise SessionError(f'Frame/cycle event streams diverge at line {lineno}')
        addr = int(addr_s, 16)
        expected_kind = 'R' if 0x2000 <= addr <= 0x3FFF and (addr-0x2000) % 8 == 2 else 'W'
        if kind != expected_kind:
            raise SessionError(f'Unexpected CPU-cycle R/W kind at line {lineno}')
        count += 1
    if count != len(events):
        raise SessionError('Cycle trace row count does not match frame trace')
    return count


def verify(session_meta, *, require_cycle=False):
    manifest = Path(session_meta)
    props = metadata(manifest)
    required(props, 'format', 'fceux_ppu_session_v1')
    required(props, 'complete', 'yes')
    required(props, 'events_dropped', '0')
    required(props, 'callback_errors', '0')
    required(props, 'capture_failures', '0')
    required(props, 'frame_callback_gaps', '0')
    required(props, 'mmc3_write_coverage', 'full_8000_ffff_even_odd')
    required(props, 'ppu_register_write_coverage', 'full_2000_3fff_mod8')
    required(props, 'ppu_status_read_coverage', 'full_2000_3fff_mod8')
    token = props.get('session_id', '')
    if not SESSION.fullmatch(token):
        raise SessionError('Invalid session_id')
    cycle = props.get('cycle_trace_available')
    if cycle not in ('yes','no'):
        raise SessionError('Invalid cycle_trace_available')
    if require_cycle and cycle != 'yes':
        raise SessionError('CPU-cycle trace unavailable')
    first, last = integer(props, 'first_callback_frame'), integer(props, 'last_callback_frame')
    callbacks = integer(props, 'frame_callbacks', 1)
    snapshots = integer(props, 'frames_captured', 1)
    expected = integer(props, 'events_recorded')
    if last < first or callbacks != last-first+1:
        raise SessionError('Missing callback frame(s)')
    frame_text = props.get('capture_frames','')
    if not frame_text or any(DEC.fullmatch(part) is None for part in frame_text.split(',')):
        raise SessionError('Invalid capture_frames list')
    frames = [int(part) for part in frame_text.split(',')]
    if len(frames) != snapshots or not all(first <= f <= last for f in frames):
        raise SessionError('Capture frame count/range mismatch')
    if any(x>=y for x,y in zip(frames,frames[1:])):
        raise SessionError('Duplicate or unordered capture frames')
    folder = manifest.parent
    events = read_frame_events(folder/'mmc3_video_writes.tsv')
    if len(events) != expected:
        raise SessionError('Truncated or extra frame events')
    last_checkpoint = -1
    for index, frame in enumerate(frames, 1):
        prefix = folder / f'frame_{frame:06d}'
        m = metadata(str(prefix)+'.meta.txt')
        required(m, 'format', 'fceux_ppu_snapshot_v4')
        required(m, 'session_id', token)
        required(m, 'capture_scope', 'frame_prefix_only')
        required(m, 'session_snapshot_index', str(index))
        required(m, 'frame', str(frame))
        required(m, 'register_log_complete', 'yes')
        required(m, 'dropped_register_writes', '0')
        required(m, 'callback_errors', '0')
        required(m, 'mmc3_write_coverage', 'full_8000_ffff_even_odd')
        required(m, 'ppu_register_write_coverage', 'full_2000_3fff_mod8')
        required(m, 'ppu_status_read_coverage', 'full_2000_3fff_mod8')
        required(m, 'cycle_trace_available', cycle)
        count = integer(m, 'logged_register_writes')
        if count < last_checkpoint or count > expected:
            raise SessionError('Invalid per-frame event count checkpoint')
        last_checkpoint = count
        for suffix, size in (('.ppu.bin', 0x4000), ('.ram.bin', 0x800)):
            try:
                actual_size = Path(str(prefix)+suffix).stat().st_size
            except OSError as exc:
                raise SessionError(f'Missing snapshot {prefix.name}{suffix}') from exc
            if actual_size != size:
                raise SessionError(f'Incorrect snapshot size {prefix.name}{suffix}')
        screen = m.get('screen_reference')
        if screen not in ('yes','no'):
            raise SessionError('Invalid screen_reference flag')
        if screen == 'yes':
            for suffix,size in (('.screen.rgb.bin',256*240*3),('.screen.pal.bin',256*240)):
                try:
                    actual_size = Path(str(prefix)+suffix).stat().st_size
                except OSError as exc:
                    raise SessionError(f'Missing screen data {prefix.name}{suffix}') from exc
                if actual_size != size:
                    raise SessionError('Invalid screen data size')
    cycles_checked = False
    if cycle == 'yes':
        check_cycle_events(folder/'mmc3_ppu_cycles.tsv', events)
        cycles_checked = True
    return {'format':'fceux_ppu_verified_session_v1',
            'session_id':token, 'frames_captured':snapshots,
            'capture_frames':frames,
            'frame_callback_span':[first,last], 'frames_observed':callbacks,
            'events_checked':len(events), 'cycles_checked':cycles_checked,
            'complete':True, 'game_identity_authenticated':False,
            'scanline_timing_proven':False, 'stage_geometry_proven':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session_meta',type=Path)
    parser.add_argument('--require-cycle',action='store_true')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    report=verify(args.session_meta,require_cycle=args.require_cycle)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
