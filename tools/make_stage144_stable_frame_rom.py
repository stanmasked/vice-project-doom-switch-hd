#!/usr/bin/env python3
"""Stage144: correct the relocated terminal 6502 JMP in Stage141 Mapper4 ROMs.

Stage137 inserted initialization/OAM instructions before the Stage110 JMP
but retained its original absolute CPU address. On subsequent frames the
CPU could execute the middle of initialization instead of an idle loop,
changing PPU palette state. This repairs ONLY its two address operands,
once in each of four mirrored 8 KiB PRG banks. No commercial assets.
"""
import argparse
import hashlib
from pathlib import Path

from make_stage110_synthetic_midframe_rom import program
from make_stage141_frame_reset_rom import MODES, make_rom as stage141_make_rom

PRG_START = 16
BANK_SIZE = 8192
PRG_BANKS = 4
PRG_END = PRG_START + PRG_BANKS * BANK_SIZE
LOAD_ADDR = 0xC000


def relocation_sites(image):
    """Validate original Stage110 JMP copied into all four Stage137 banks."""
    if not isinstance(image, bytes) or len(image) != 49168 or image[:16] != (
            b"NES\x1a\x02\x02\x40" + bytes(9)):
        raise ValueError("Require unmodified synthetic Mapper4 iNES layout")
    original_program = program()
    old_jmp = original_program[-3:]
    old_pc = LOAD_ADDR + len(original_program) - 3
    if (old_jmp[0] != 0x4C or
            int.from_bytes(old_jmp[1:], "little") != old_pc):
        raise ValueError("Stage110 absolute idle JMP source changed")
    sites = []
    reference = image[PRG_START:PRG_START + BANK_SIZE]
    if reference[:8] != original_program[:8]:
        raise ValueError("Stage110 CPU reset/PPU-disable prologue changed")
    for bankno in range(PRG_BANKS):
        start = PRG_START + bankno * BANK_SIZE
        bank = image[start:start + BANK_SIZE]
        # Stage137 repeats the exact same executable bank four times;
        # only the last six vector bytes differ in the fourth bank.
        mirror_end = BANK_SIZE - 6 if bankno == PRG_BANKS - 1 else BANK_SIZE
        if bank[:mirror_end] != reference[:mirror_end]:
            raise ValueError("Synthetic PRG bank content diverged")
        if bank.count(old_jmp) != 1:
            raise ValueError("Missing or ambiguous relocated JMP in PRG bank")
        relative = bank.index(old_jmp)
        if not len(original_program) < relative < BANK_SIZE - 9:
            raise ValueError("Relocated JMP not inside injected 6502 program")
        # Stage137 pads all remaining instructions with NOPs and stores
        # interrupt vectors only at the end of the final mirrored bank.
        pad_end = BANK_SIZE - 6 if bankno == PRG_BANKS - 1 else BANK_SIZE
        if bank[relative + 3:pad_end] != bytes([0xEA]) * (pad_end - relative - 3):
            raise ValueError("Non-NOP code after terminal JMP")
        if bankno == PRG_BANKS - 1 and bank[-6:] != b"\x00\xC0" * 3:
            raise ValueError("Synthetic interrupt/reset vectors changed")
        if bankno and relative != sites[0][1]:
            raise ValueError("Mirrored PRG banks disagree on JMP location")
        sites.append((start, relative))
    return sites


def relocate(image):
    sites = relocation_sites(image)
    target = LOAD_ADDR + sites[0][1]
    if not LOAD_ADDR <= target < LOAD_ADDR + BANK_SIZE:
        raise ValueError("Terminal CPU jump outside 8 KiB mapped PRG bank")
    patched = bytearray(image)
    new_operand = target.to_bytes(2, "little")
    for start, relative in sites:
        patched[start + relative + 1:start + relative + 3] = new_operand
    differences = [i for i, (a, b) in enumerate(zip(image, patched)) if a != b]
    permitted = {start + relative + offset for start, relative in sites
                 for offset in (1, 2)}
    if not differences or set(differences) != permitted:
        raise ValueError("Unexpected JMP relocation footprint")
    if (patched[:PRG_START] != image[:PRG_START] or
            patched[PRG_END:] != image[PRG_END:]):
        raise ValueError("Header or CHR data changed")
    return bytes(patched)


def make_rom(destination, mode):
    if mode not in MODES:
        raise ValueError("Only Stage141 two-frame OAM modes are allowed")
    path = Path(destination)
    stage141_make_rom(path, mode)
    original = path.read_bytes()
    try:
        stable = relocate(original)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    path.write_bytes(stable)
    return hashlib.sha256(stable).hexdigest()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument("--mode", choices=MODES, required=True)
    a = cli.parse_args()
    print("STAGE144_SYNTHETIC_JMP_RELOCATED_ROM sha256=" +
          make_rom(a.output, a.mode))
