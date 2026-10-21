#!/usr/bin/env python3
"""Private 8x8 CHR provenance audit for two owner-supplied NES cartridges.

Never serialize raw source tiles, artwork, ROM bytes, ROM identities or hashes.
Same-offset tile comparison is not proof of stage or animation identity.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from audit_private_nes_variant_banks import read_layout, BANK_BYTES

TILE_BYTES=16
TILES_PER_BANK=BANK_BYTES//TILE_BYTES
ZERO_TILE=bytes(TILE_BYTES)


def inventory(first_path,second_path):
    a=read_layout(first_path)
    b=read_layout(second_path)
    if a["mapper"]!=b["mapper"]:
        raise ValueError("incompatible NES cartridge mappers")
    if len(a["prg"])!=len(b["prg"]) or len(a["chr"])!=len(b["chr"]):
        raise ValueError("incompatible PRG/CHR bank layouts")
    if len(a["chr"])%TILE_BYTES:
        raise ValueError("unaligned CHR tile data")
    first=[a["chr"][i:i+TILE_BYTES] for i in range(0,len(a["chr"]),TILE_BYTES)]
    second=[b["chr"][i:i+TILE_BYTES] for i in range(0,len(b["chr"]),TILE_BYTES)]
    counts_first=Counter(first)
    counts_second=Counter(second)
    different=[i for i,(x,y) in enumerate(zip(first,second)) if x!=y]
    changed_banks=sorted({i//TILES_PER_BANK for i in different})
    details=[]
    for bank in changed_banks:
        lo=bank*TILES_PER_BANK
        hi=lo+TILES_PER_BANK
        ids=[i for i in different if lo<=i<hi]
        details.append({
            "bank_index":bank,
            "modified_tile_count":len(ids),
            "identical_tile_count":TILES_PER_BANK-len(ids),
            "modified_global_tile_indices":ids,
            "first_version_zero_tiles":sum(x==ZERO_TILE for x in first[lo:hi]),
            "second_version_zero_tiles":sum(x==ZERO_TILE for x in second[lo:hi]),
            "first_changed_patterns_absent_anywhere_in_second":sum(
                counts_second[first[i]]==0 for i in ids),
            "second_changed_patterns_absent_anywhere_in_first":sum(
                counts_first[second[i]]==0 for i in ids)
        })
    return {
        "classification":"private static CHR tile origin and bank positioning only",
        "mapper":a["mapper"],
        "tile_format":"NES 2-bit planar 8x8, 16 bytes per tile",
        "total_chr_tiles":len(first),
        "same_offset_identical_tiles":len(first)-len(different),
        "same_offset_modified_tiles":len(different),
        "modified_chr_bank_count":len(changed_banks),
        "modified_banks":details,
        "first_modified_patterns_absent_anywhere_in_second":sum(
            counts_second[first[i]]==0 for i in different),
        "second_modified_patterns_absent_anywhere_in_first":sum(
            counts_first[second[i]]==0 for i in different),
        "gameplay_equivalence_proven":False,
        "tile_usage_in_actual_ppu_proven":False,
        "level_geometry_proven":False,
        "movie_replay_proven":False,
        "next_step":"Use private FCEUX PPU/CHR switch events to identify when each bank is displayed."
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--first-rom",type=Path,required=True)
    p.add_argument("--second-rom",type=Path,required=True)
    p.add_argument("--private-summary",type=Path)
    args=p.parse_args()
    try:
        report=inventory(args.first_rom,args.second_rom)
        if args.private_summary:
            dest=args.private_summary.expanduser()
            if dest.is_symlink() or dest.exists():
                raise ValueError("refusing to replace private CHR provenance report")
            parent=dest.parent.resolve(strict=True)
            if not parent.is_dir() or any((d/".git").exists() for d in (parent,*parent.parents)):
                raise ValueError("private report folder cannot be within a Git checkout")
            with dest.open("x",encoding="utf-8") as f:
                json.dump(report,f,ensure_ascii=False,indent=2)
                f.write("\n")
    except (ValueError,OSError,UnicodeError) as exc:
        p.exit(1,"PRIVATE_CHR_TILE_ORIGIN_INCONCLUSIVE: "+str(exc)+"\n")
    print("PRIVATE_CHR_TILE_ORIGIN_AUDIT_PASS")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
