#!/usr/bin/env python3
"""Compare two privately owned NES ROMs without exporting ROM bytes or artwork.

Only mapper/layout evidence; CHR equality does not prove equal scenes/stages.
All report fields are numeric or boolean; no filenames, hashes, strings from
ROM data, original tiles, CPU code or proprietary assets are serialized.
"""
import argparse
import json
from pathlib import Path

MAX_ROM_BYTES=16*1024*1024
PRG_UNIT=16384
CHR_UNIT=8192
BANK_BYTES=1024


def read_layout(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing or symlinked private NES ROM")
    length=path.stat().st_size
    if length<16 or length>MAX_ROM_BYTES:
        raise ValueError("private NES ROM size outside supported bounds")
    data=path.read_bytes()
    h=data[:16]
    if h[:4]!=b"NES\x1a":
        raise ValueError("not an NES cartridge image")
    if h[6]&0x04:
        raise ValueError("trained NES ROM unsupported: provenance ambiguous")
    nes2=(h[7]&0x0c)==0x08
    if h[7]&0x0c not in (0,0x08):
        raise ValueError("unsupported or malformed NES header")
    mapper=(h[6]>>4)|(h[7]&0xf0)
    if nes2:
        mapper|=(h[8]&0x0f)<<8
        prg_upper=h[9]&0x0f
        chr_upper=h[9]>>4
        if prg_upper==0x0f or chr_upper==0x0f:
            raise ValueError("NES2 exponent-size coding not supported")
        prg_units=h[4]|prg_upper<<8
        chr_units=h[5]|chr_upper<<8
    else:
        prg_units=h[4]
        chr_units=h[5]
    if prg_units<1 or chr_units<1:
        raise ValueError("ROM must have fixed PRG and CHR banks")
    prg_length=prg_units*PRG_UNIT
    chr_length=chr_units*CHR_UNIT
    if len(data)!=16+prg_length+chr_length:
        raise ValueError("private NES ROM data length is not canonical")
    prg=data[16:16+prg_length]
    chr_=data[16+prg_length:]
    return {"mapper":mapper,"nes2":nes2,"prg":prg,"chr":chr_}


def compare_region(a,b):
    if len(a)!=len(b) or len(a)%BANK_BYTES:
        raise ValueError("bank region sizes differ or are not 1KB aligned")
    changed=[]
    mismatched_bytes=0
    for i in range(len(a)//BANK_BYTES):
        lo=i*BANK_BYTES
        x=a[lo:lo+BANK_BYTES]
        y=b[lo:lo+BANK_BYTES]
        n=sum(left!=right for left,right in zip(x,y))
        if n:
            changed.append({"index":i,"different_bytes":n})
            mismatched_bytes+=n
    return {
        "total_1kb_banks":len(a)//BANK_BYTES,
        "identical_1kb_banks":len(a)//BANK_BYTES-len(changed),
        "different_1kb_banks":len(changed),
        "different_byte_count":mismatched_bytes,
        "different_banks":changed
    }


def compare_roms(us_path,jp_path):
    first=read_layout(us_path)
    second=read_layout(jp_path)
    if first["mapper"]!=second["mapper"]:
        raise ValueError("ROM mapper differs; versions not directly bank-aligned")
    if len(first["prg"])!=len(second["prg"]) or len(first["chr"])!=len(second["chr"]):
        raise ValueError("ROM PRG/CHR layout differs; bank indices not aligned")
    return {
        "classification":"private static cartridge cross-version bank comparison only",
        "mapper":first["mapper"],
        "first_rom_uses_nes2":first["nes2"],
        "second_rom_uses_nes2":second["nes2"],
        "prg_comparison":compare_region(first["prg"],second["prg"]),
        "chr_comparison":compare_region(first["chr"],second["chr"]),
        "shared_chr_proven_at_equal_offsets":True,
        "shared_original_gameplay_proven":False,
        "shared_level_geometry_proven":False,
        "shared_stage_order_proven":False,
        "real_fceux_movie_replay_proven":False,
        "next_step":"Validate original stage/scroll timing through private FCEUX PPU and gameplay captures."
    }


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--first-rom",type=Path,required=True)
    cli.add_argument("--second-rom",type=Path,required=True)
    cli.add_argument("--private-summary",type=Path,
                     help="optional output JSON strictly for a private directory")
    args=cli.parse_args()
    try:
        report=compare_roms(args.first_rom,args.second_rom)
        if args.private_summary:
            dest=args.private_summary
            if dest.exists() or dest.is_symlink():
                raise ValueError("refusing to overwrite variant audit")
            if any((directory/".git").exists()
                   for directory in [dest.parent,*dest.parent.parents]):
                raise ValueError("refusing to save private report inside Git")
            with dest.open("x",encoding="utf-8") as f:
                json.dump(report,f,indent=2,ensure_ascii=False)
                f.write("\n")
    except (OSError,ValueError,UnicodeError) as exc:
        cli.exit(1,"PRIVATE_NES_VARIANT_INCONCLUSIVE: "+str(exc)+"\n")
    print("PRIVATE_NES_VARIANT_BANK_AUDIT_PASS")
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
