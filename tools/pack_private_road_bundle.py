#!/usr/bin/env python3
"""Privately pack 37 audited source-image numeric road intervals for Switch.

Never push the output VPRD binary or its input report to public GitHub.
The 41-slot report has no original ROM/FM2 hash; success does not prove
camera physics, original game rendering, or cross-session file identity.
"""
from __future__ import annotations
import argparse
import json
import struct
import zlib
from pathlib import Path
from audit_private_legacy_road_geometry import validate_legacy_report

MAGIC=b"VPDROAD1"
HEADER=struct.Struct("<8sHHI")
RECORD=struct.Struct("<HBB")
EXPECTED_VALID=37
EXPECTED_BYTES=HEADER.size+EXPECTED_VALID*RECORD.size
REJECTED={712,720,728,736}


def pack_numeric_report(report:dict)->bytes:
    validate_legacy_report(report) # independent strict 41-frame provenance
    items=[row for row in report["frames"] if row["roi_valid"]]
    if len(items)!=EXPECTED_VALID:
        raise ValueError("complete audited source 37/4 window required")
    expected=[frame for frame in range(600,921,8) if frame not in REJECTED]
    if [row["frame"] for row in items]!=expected:
        raise ValueError("private reference movie-frame chronology changed")
    body=b"".join(RECORD.pack(
        row["frame"],row["observed_left_edge"],row["observed_right_edge"]
    ) for row in items)
    packet=HEADER.pack(MAGIC,1,EXPECTED_VALID,zlib.crc32(body))+body
    assert len(packet)==EXPECTED_BYTES
    return packet


def output_private_only(path:Path)->None:
    source_root=Path(__file__).resolve().parents[1]
    candidate=path.expanduser().resolve()
    if candidate==source_root or source_root in candidate.parents:
        raise ValueError("private original numeric bundle cannot be written inside public source checkout")


def main()->None:
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--numeric-report",required=True,type=Path,
                     help="owner-private FCEUX numeric JSON, never uploaded")
    cli.add_argument("--output",required=True,type=Path,
                     help="local SD VPRD file path outside public repo")
    args=cli.parse_args()
    output_private_only(args.output)
    raw=json.loads(args.numeric_report.read_text(encoding="utf8"))
    bundle=pack_numeric_report(raw)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(bundle)
    print("VPD_PRIVATE_NUMERIC_ROAD_BUNDLE_PASS"
          " count=37 ambiguous_excluded=4"
          f" bytes={len(bundle)}"
          " source_images_included=no"
          " original_rom_fm2_hash_proven=no"
          " collision_camera_physics_proven=no")
if __name__=="__main__":
    main()
