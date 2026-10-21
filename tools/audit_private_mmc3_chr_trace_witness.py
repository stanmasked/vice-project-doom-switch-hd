#!/usr/bin/env python3
"""Validate PRIVATE MMC3 mapper trace closure without exposing ROM resources.

The emitter intentionally deduplicates matching MMC3 R0..R5 writes within
a time bucket. Report both raw matching selection events and retained pairs
instead of falsely presenting deduplicated records as all CPU writes.
"""
import re
from pathlib import Path

FORMAT="private_mmc3_chr_trace_witness_v1"
REQUIRED={
    "format","movie_terminal_frame","raw_matching_mapping_writes",
    "retained_deduplicated_mapping_pairs","suppressed_repeated_mapping_writes",
    "trace_closed","ppu_rendering_proven"
}
NUMBER=re.compile(r"(?:0|[1-9][0-9]*)\Z")


def audit_trace_witness(path,*,expected_terminal_frame,parsed_pair_count):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>2048:
        raise ValueError("closed private MMC3 trace witness missing or invalid")
    contents=path.read_text(encoding="ascii")
    rows={}
    for line in contents.splitlines():
        if "=" not in line:
            raise ValueError("malformed MMC3 trace witness row")
        key,val=line.split("=",1)
        if not key or key in rows:
            raise ValueError("duplicate or empty MMC3 witness key")
        rows[key]=val
    if rows.keys()!=REQUIRED or rows["format"]!=FORMAT:
        raise ValueError("missing, extra or unsupported MMC3 witness keys")
    if rows["trace_closed"]!="yes" or rows["ppu_rendering_proven"]!="no":
        raise ValueError("unclosed trace or ungrounded PPU rendering claim")
    values={}
    for key in ("movie_terminal_frame","raw_matching_mapping_writes",
                "retained_deduplicated_mapping_pairs","suppressed_repeated_mapping_writes"):
        if not NUMBER.fullmatch(rows[key]):
            raise ValueError("invalid numeric MMC3 trace witness field")
        values[key]=int(rows[key])
    if not isinstance(expected_terminal_frame,int) or not 1<=expected_terminal_frame<=100000000:
        raise ValueError("invalid expected terminal frame")
    if not isinstance(parsed_pair_count,int) or not 0<=parsed_pair_count<=80000:
        raise ValueError("invalid parsed MMC3 trace pair count")
    if values["movie_terminal_frame"]!=expected_terminal_frame:
        raise ValueError("private MMC3 trace did not reach last movie frame")
    if values["retained_deduplicated_mapping_pairs"]!=parsed_pair_count:
        raise ValueError("MMC3 emitted trace pair count differs from closed witness")
    if values["raw_matching_mapping_writes"]!= (
        values["retained_deduplicated_mapping_pairs"]+
        values["suppressed_repeated_mapping_writes"]
    ):
        raise ValueError("inconsistent raw and suppressed MMC3 mapping events")
    if values["raw_matching_mapping_writes"]>100000000:
        raise ValueError("unreasonably large private MMC3 mapping event count")
    return {
        **values,
        "trace_closed":True,
        "event_budget_verified":True,
        "actual_ppu_rendering_proven":False,
        "original_level_identity_proven":False
    }
