#!/usr/bin/env python3
"""Render only differing CHR banks from two privately owned cartridge images.

This is a local 2-bit CHR pattern-table reference, NOT an authentic PPU
screen, stage map, palette, animation, or level-boundary identification.
No game bytes/artwork are uploaded or checked into public GitHub.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw
from audit_private_nes_variant_banks import read_layout, compare_region, BANK_BYTES

TONES=(20,94,165,236)
MAX_BANKS=16


def decode_chr_bank(raw):
    if len(raw)!=BANK_BYTES:
        raise ValueError("CHR bank must contain exactly 1KB")
    image=Image.new("L",(64,64))
    for tile in range(64):
        offset=tile*16
        ox=8*(tile%8)
        oy=8*(tile//8)
        for y in range(8):
            a,b=raw[offset+y],raw[offset+8+y]
            for x in range(8):
                bit=7-x
                index=((a>>bit)&1)|(((b>>bit)&1)<<1)
                image.putpixel((ox+x,oy+y),TONES[index])
    return image


def render_difference_atlas(first,second,output,*,scale=4):
    if not 1<=scale<=8:
        raise ValueError("scale must be between 1 and 8")
    output=Path(output).expanduser()
    if output.exists() or output.is_symlink():
        raise ValueError("refusing to overwrite private CHR atlas")
    parent=output.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("output parent is not a directory")
    if output.parent.is_symlink():
        raise ValueError("symlinked private output parent not accepted")
    if any((item/".git").exists() for item in (parent,*parent.parents)):
        raise ValueError("do not save original CHR-derived artwork inside Git")
    a=read_layout(first)
    b=read_layout(second)
    if a["mapper"]!=b["mapper"] or len(a["prg"])!=len(b["prg"]) or len(a["chr"])!=len(b["chr"]):
        raise ValueError("ROM variants have incompatible mapper or PRG/CHR dimensions")
    diffs=compare_region(a["chr"],b["chr"])["different_banks"]
    if not diffs:
        raise ValueError("CHR patterns identical: no difference atlas needed")
    if len(diffs)>MAX_BANKS:
        raise ValueError("too many different CHR banks for a compact atlas")
    count=len(diffs)
    cell=64*scale
    pitch=cell+32
    canvas=Image.new("RGB",(12+count*pitch,12+2*(pitch+14)),(22,25,33))
    draw=ImageDraw.Draw(canvas)
    for row,(name,blob) in enumerate((("First ROM",a["chr"]),("Second ROM",b["chr"]))):
        draw.text((12,12+row*(pitch+14)),name,fill=(250,250,250))
        for column,item in enumerate(diffs):
            i=item["index"]
            tile=decode_chr_bank(blob[i*BANK_BYTES:(i+1)*BANK_BYTES])
            tile=tile.resize((cell,cell),Image.Resampling.NEAREST).convert("RGB")
            x=12+column*pitch
            y=30+row*(pitch+14)
            canvas.paste(tile,(x,y))
            draw.text((x,y+cell+3),"CHR 1KB bank "+str(i),fill=(230,230,230))
    with output.open("xb") as stream:
        canvas.save(stream,format="PNG")
    return {"private_atlas_created":True,"different_chr_banks":[item["index"] for item in diffs],
            "pixel_dimensions":list(canvas.size),
            "actual_palette_or_stage_proven":False,
            "source_game_bytes_exported_into_repository":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-rom",type=Path,required=True)
    parser.add_argument("--second-rom",type=Path,required=True)
    parser.add_argument("--private-output",type=Path,required=True)
    parser.add_argument("--scale",type=int,default=4)
    args=parser.parse_args()
    try:
        summary=render_difference_atlas(
            args.first_rom,args.second_rom,args.private_output,scale=args.scale)
    except (OSError,ValueError,UnicodeError) as exc:
        parser.exit(1,"PRIVATE_CHR_ATLAS_INCONCLUSIVE: "+str(exc)+"\n")
    print("PRIVATE_CHR_BANK_DIFFERENCE_ATLAS_PASS")
    print(summary)


if __name__=="__main__":
    main()
