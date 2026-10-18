#!/usr/bin/env python3
"""Stage148: controlled CPU-written OAM transition across VBlank.

Extends the validated Stage144 synthetic Mapper4 eight-sprite ROM with a
one-shot CPU polling loop: BIT $2002 / BPL waits for VBlank, then writes
OAM7 X and all four bytes of OAM8 through the genuine CPU $2003/$2004
registers. A timing-identical no-op control writes their original values.
No NMI timing or hardware accuracy is claimed. No original game content.
"""
import argparse
import hashlib
from pathlib import Path

from make_stage144_stable_frame_rom import (
    BANK_SIZE, LOAD_ADDR, PRG_BANKS, PRG_END, PRG_START,
    make_rom as make_stage144_rom)

MODES=("activate_ninth", "preserve_eight")
POLL_VBLANK=bytes((0x2C,0x02,0x20,0x10,0xFB))
STA_OAMADDR=bytes((0x8D,0x03,0x20))
STA_OAMDATA=bytes((0x8D,0x04,0x20))


def _tail_site(image):
    if not isinstance(image,bytes) or len(image)!=49168:
        raise ValueError("Only synthetic 49,168-byte Mapper4 images")
    if image[:16] != b"NES\x1a\x02\x02\x40"+bytes(9):
        raise ValueError("Nonstandard synthetic Mapper4 header")
    locations=[]
    reference=image[PRG_START:PRG_START+BANK_SIZE]
    for bankno in range(PRG_BANKS):
        start=PRG_START+bankno*BANK_SIZE
        bank=image[start:start+BANK_SIZE]
        pad_end=BANK_SIZE-6 if bankno==PRG_BANKS-1 else BANK_SIZE
        if bank[:pad_end]!=reference[:pad_end]:
            raise ValueError("Inconsistent mirrored 8-KiB PRG executable")
        if bankno==PRG_BANKS-1 and bank[-6:]!=b"\x00\xc0"*3:
            raise ValueError("Unexpected IRQ, reset or NMI vectors")
        candidates=[]
        for position in range(8,pad_end-3):
            if (bank[position]==0x4C and
                    int.from_bytes(bank[position+1:position+3],
                                   "little")==LOAD_ADDR+position and
                    bank[position+3:pad_end]==
                        b"\xEA"*(pad_end-position-3)):
                candidates.append(position)
        if len(candidates)!=1:
            raise ValueError("Missing or ambiguous Stage144 stable idle JMP")
        locations.append((start,candidates[0],pad_end))
    if len({pos for _,pos,_ in locations})!=1:
        raise ValueError("Stage144 JMP position differs across PRG mirrors")
    return locations


def _program(mode, position):
    if mode not in MODES:
        raise ValueError("Unsupported controlled VBlank OAM scenario")
    # OAM7 [Y,tile,attr,X] lives at OAMADDR $1C..$1F.
    # OAM8 starts at $20. Incrementing $2004 writes it automatically.
    # preserve_eight writes the exact old values, keeping instruction
    # count, PPU register addresses, and CPU timing identical.
    data = (160,120,2,0,64) if mode=="activate_ninth" else (
        64,255,255,255,255)
    result=bytearray(POLL_VBLANK)
    result.extend((0xA9,31))
    result.extend(STA_OAMADDR)
    for value in data:
        result.extend((0xA9,value))
        result.extend(STA_OAMDATA)
    # One-shot mutation: self-loop after all six CPU register writes.
    tail_pc=LOAD_ADDR+position+len(result)
    if not LOAD_ADDR <= tail_pc < LOAD_ADDR+BANK_SIZE:
        raise ValueError("VBlank handler JMP target outside PRG bank")
    result.extend((0x4C,tail_pc&255,tail_pc>>8))
    return bytes(result)


def transform(image,mode):
    sites=_tail_site(image)
    position=sites[0][1]
    replacement=_program(mode,position)
    mutated=bytearray(image)
    for start,at,pad_end in sites:
        if at+len(replacement)>=pad_end:
            raise ValueError("Synthetic CPU program would overwrite vectors")
        mutated[start+at:start+at+len(replacement)]=replacement
        if mutated[start+at+len(replacement):start+pad_end]!=(
                b"\xEA"*(pad_end-at-len(replacement))):
            raise ValueError("Non-NOP contents after one-shot CPU program")
    if mutated[:PRG_START]!=image[:PRG_START] or mutated[PRG_END:]!=image[PRG_END:]:
        raise ValueError("Mutation affected iNES header or CHR data")
    # Only the pre-existing terminal JMP and its NOP padding are replaced.
    permitted={
        start+i for start,at,_ in sites
        for i in range(at,at+len(replacement))}
    actual={i for i,(old,new) in enumerate(zip(image,mutated)) if old!=new}
    if not actual or not actual<=permitted:
        raise ValueError("CPU mutation escaped original terminal NOP tail")
    return bytes(mutated)


def make_rom(destination,mode):
    if mode not in MODES:
        raise ValueError("Only two controlled CPU-written OAM fixtures")
    path=Path(destination)
    make_stage144_rom(path,"eight_visible")
    try:
        edited=transform(path.read_bytes(),mode)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    path.write_bytes(edited)
    return hashlib.sha256(edited).hexdigest()


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output",type=Path)
    cli.add_argument("--mode",choices=MODES,required=True)
    args=cli.parse_args()
    print("STAGE148_SYNTHETIC_VBLANK_OAM_ROM sha256="+
          make_rom(args.output,args.mode))
