#!/usr/bin/env python3
"""Generated original Mapper 4 ROM: select blank CHR then optionally switch mid-frame.

All generated .nes files live in a private ephemeral test directory.
"""
import argparse
import hashlib
from pathlib import Path


def program(*, switch=True, delay_outer=11, phase_nops=0, fine_scroll=0,
            dynamic_fine_scroll=None, second_dynamic_scroll=None):
    if not 1 <= delay_outer <= 32:
        raise ValueError("Invalid bounded delay")
    if type(phase_nops) is not int or not 0 <= phase_nops <= 64:
        raise ValueError("Phase NOP count outside bounded 6502 raster sweep")
    if type(fine_scroll) is not int or not 0 <= fine_scroll <= 7:
        raise ValueError("Fine horizontal scroll must be integer 0..7")
    if dynamic_fine_scroll is not None and (
            type(dynamic_fine_scroll) is not int or
            dynamic_fine_scroll not in (1, 3, 5, 7) or fine_scroll != 0):
        raise ValueError("Midframe $2005 requires initial X=0, target 1/3/5/7")
    if second_dynamic_scroll is not None and (
            type(second_dynamic_scroll) is not int or
            second_dynamic_scroll not in (9, 11, 13, 15) or
            dynamic_fine_scroll is None or
            second_dynamic_scroll != 16-dynamic_fine_scroll):
        raise ValueError("Second $2005 X must increment coarse and change fine")
    result = bytearray()
    def lda(v):
        result.extend((0xa9, v))
    def sta(addr):
        result.extend((0x8d, addr & 255, addr >> 8))
    lda(0); sta(0x2000); sta(0x2001)
    lda(0x3f); sta(0x2006); lda(0); sta(0x2006)
    for color in (0x0f, 0x16, 0x27, 0x30):
        lda(color); sta(0x2007)
    lda(0x10); sta(0x2000)
    # Stage116: write $2005 X and Y before rendering. Preserve all previous
    # generated ROM bytes when fine_scroll=0 (legacy negative controls).
    if fine_scroll:
        lda(fine_scroll); sta(0x2005)
        lda(0); sta(0x2005)
    lda(0x0a); sta(0x2001)
    lda(2); sta(0x8000)
    lda(0); sta(0x8001)
    # Wait for VBlank high (the BIT $2002 read clears the flag), then
    # spend a bounded CPU delay which targets active visible scanlines.
    result.extend((0x2c, 0x02, 0x20, 0x10, 0xfb))
    result.extend((0xa2, delay_outer, 0xa0, 255, 0x88, 0xd0, 0xfd,
                   0xca, 0xd0, 0xf8))
    # 2 CPU cycles per NOP: controlled sub-scanline bank-switch phase.
    # No PPU state, nametable, CHR, or palette differences between variants.
    result.extend((0xea,) * phase_nops)
    lda(1 if switch else 0)
    sta(0x8001)
    # Stage117: first $2005 write changes X fine scroll during active
    # raster. Second write resets the X/Y toggle without altering fh.
    if dynamic_fine_scroll is not None:
        lda(dynamic_fine_scroll); sta(0x2005)
        lda(0); sta(0x2005)
    if second_dynamic_scroll is not None:
        # 28 times 5 cycles moves the next X write to the next visible row.
        result.extend((0xa2, 28, 0xca, 0xd0, 0xfd))
        lda(second_dynamic_scroll); sta(0x2005)
        lda(0); sta(0x2005)
    loop = 0xc000 + len(result)
    result.extend((0x4c, loop & 255, loop >> 8))
    return bytes(result)


def make_rom(destination, *, switch=True, delay_outer=11, phase_nops=0,
             fine_scroll=0, dynamic_fine_scroll=None, second_dynamic_scroll=None):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = b"NES\x1a" + bytes((2, 2, 0x40, 0)) + bytes(8)
    prg_bank = bytearray(b"\xea" * 8192)
    p = program(switch=switch, delay_outer=delay_outer, phase_nops=phase_nops,
                fine_scroll=fine_scroll, dynamic_fine_scroll=dynamic_fine_scroll,
                second_dynamic_scroll=second_dynamic_scroll)
    prg_bank[:len(p)] = p
    prg = bytearray(prg_bank * 4)
    prg[-6:] = b"\x00\xc0" * 3
    chr_data = bytearray(16384)
    chr_data[1024:2048] = b"\xff" * 1024
    image = header + prg + chr_data
    assert len(image) == 49168
    destination.write_bytes(image)
    return hashlib.sha256(image).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--fixed", action="store_true")
    parser.add_argument("--delay-outer", type=int, default=11)
    parser.add_argument("--phase-nops", type=int, default=0)
    parser.add_argument("--fine-scroll", type=int, default=0)
    parser.add_argument("--dynamic-fine-scroll", type=int, default=None)
    parser.add_argument("--second-dynamic-scroll", type=int, default=None)
    args = parser.parse_args()
    print("Stage110 original synthetic mapper4 SHA256=" +
          make_rom(args.destination, switch=not args.fixed,
                   delay_outer=args.delay_outer,
                   phase_nops=args.phase_nops,
                   fine_scroll=args.fine_scroll,
                   dynamic_fine_scroll=args.dynamic_fine_scroll,
                   second_dynamic_scroll=args.second_dynamic_scroll))
