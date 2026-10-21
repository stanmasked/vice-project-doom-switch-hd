#!/usr/bin/env python3
"""Join two locally audited original Stage 1-1 *numeric-only* FCEUX reports.

No source ROM, FM2, RGB, PPU snapshots, CHR, memory dumps or absolute
private file paths belong in the returned public summary.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

# Previously published reference anchors; do not infer missing source frames.
ANCHORS = {
    600: (66,188,79,79),
    744: (66,188,136,134),
    800: (100,155,144,139),
    920: (116,203,24,19),
}
WRITER_PCS = ["E8EC", "E8F1", "E369", "E36C"]
ROAD_KEYS = {"frame", "left", "right"}
PPU_KEYS = {
    "frame", "writer_pcs", "written_values",
    "cpu_cycles_after_previous_frame", "ram_0d_postframe",
}
DOC_KEYS = {"schema", "rom_sha256", "fm2_sha256",
            "movie_frame_origin", "samples"}

def strict_int(x: object, low: int, high: int, field: str) -> int:
    if type(x) is not int or not low <= x <= high:
        raise ValueError(f"invalid {field}: integer range")
    return x

def numeric_samples(document: dict, kind: str) -> dict[int, dict]:
    if type(document) is not dict or set(document) != DOC_KEYS:
        raise ValueError(f"{kind}: invalid source document shape")
    if document["schema"] != kind+"_v1" or document["movie_frame_origin"] != "zero_based_FM2":
        raise ValueError(f"{kind}: evidence provenance missing")
    for key in ("rom_sha256", "fm2_sha256"):
        hash_value = document[key]
        if type(hash_value) is not str or len(hash_value) != 64 or (
            any(c not in "0123456789abcdef" for c in hash_value)
        ):
            raise ValueError(f"{kind}: invalid {key}")
    rows = document["samples"]
    if type(rows) is not list or not rows:
        raise ValueError(f"{kind}: missing numeric source samples")
    result: dict[int, dict] = {}
    last = 599
    for row in rows:
        expected = ROAD_KEYS if kind == "road_image_cross_sections" else PPU_KEYS
        if type(row) is not dict or set(row) != expected:
            raise ValueError(f"{kind}: unexpected sample schema")
        frame = strict_int(row["frame"], 600, 920, "FM2 frame")
        if frame <= last:
            raise ValueError(f"{kind}: frame order, duplication or regression")
        last=frame
        if kind == "road_image_cross_sections":
            left = strict_int(row["left"],0,255,"road left")
            right = strict_int(row["right"],0,255,"road right")
            if left>right:
                raise ValueError("invalid road image-space interval")
        else:
            if row["writer_pcs"] != WRITER_PCS:
                raise ValueError("PPU writer PC origin or order wrong")
            values = row["written_values"]
            cycles = row["cpu_cycles_after_previous_frame"]
            if type(values) is not list or len(values)!=4 or (
                type(cycles) is not list or len(cycles)!=4
            ):
                raise ValueError("missing four source-backed CPU writes")
            for value in values:
                strict_int(value,0,255,"raw $2005 write")
            for cycle in cycles:
                strict_int(cycle,0,30000,"CPU-cycle frame phase")
            if values[0]!=0 or values[2:]!=[0,0]:
                raise ValueError("original four-write order altered")
            if cycles[1]-cycles[0]!=7 or cycles[3]-cycles[2]!=4:
                raise ValueError("original observed CPU writer cycle spacing wrong")
            if not (793<=cycles[0]<=2212 and 24283<=cycles[2]<=24291):
                raise ValueError("writer CPU-frame phase unsupported")
            strict_int(row["ram_0d_postframe"],0,255,"postframe RAM $0D")
        result[frame]=row
    return result

def audit(road: dict, ppu: dict) -> dict:
    rs = numeric_samples(road,"road_image_cross_sections")
    ps = numeric_samples(ppu,"ppu_cpu_writer_phases")
    if (road["rom_sha256"] != ppu["rom_sha256"] or
        road["fm2_sha256"] != ppu["fm2_sha256"]):
        raise ValueError("image and PPU evidence belong to different ROM/movie identities")
    if not rs.keys() <= ps.keys():
        raise ValueError("road frame has no matching CPU writer record")
    if not ANCHORS.keys() <= rs.keys():
        raise ValueError("missing previously independently published original anchor")
    for frame,(left,right,second,post) in ANCHORS.items():
        if ((rs[frame]["left"],rs[frame]["right"],
             ps[frame]["written_values"][1],
             ps[frame]["ram_0d_postframe"]) != (left,right,second,post)):
            raise ValueError("published original cross-source frame anchor altered")
    if len(rs)<4 or len(ps)<4:
        raise ValueError("insufficient independent evidence")
    return {
        "joined_frames": len(rs),
        "published_anchor_frames": sorted(ANCHORS),
        "matching_source_identity": True,
        "native_writer_pc_order_verified": True,
        "source_raw_writes_per_frame": 4,
        "display_effective_scroll_proven": False,
        "camera_speed_proven": False,
        "road_collision_proven": False,
        "original_images_in_report": False,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--road",type=Path,required=True,
                        help="private *numeric-only* road report JSON")
    parser.add_argument("--ppu",type=Path,required=True,
                        help="private *numeric-only* CPU write report JSON")
    parser.add_argument("--output",type=Path,
                        help="optional sanitized numeric summary path")
    args=parser.parse_args()
    road=json.loads(args.road.read_text(encoding="utf8"))
    ppu=json.loads(args.ppu.read_text(encoding="utf8"))
    summary=audit(road,ppu)
    print("VPD_PRIVATE_ROAD_PPU_NUMERIC_ALIGNMENT_PASS"
          f" joined_frames={summary['joined_frames']}"
          " original_movie_identity_matched=yes"
          " effective_scroll_proven=no camera_speed_proven=no")
    if args.output:
        args.output.write_text(json.dumps(summary,sort_keys=True,indent=2)+"\n",
                               encoding="utf8")

if __name__ == "__main__":
    main()
