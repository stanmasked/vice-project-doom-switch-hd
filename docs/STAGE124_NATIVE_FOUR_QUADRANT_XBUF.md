# Stage124 — native FCEUX four-quadrant palette-to-XBuf experiment

## Purpose

Stage123 independently checked the NES attribute byte `$E4`, the four
quadrant shifts (0, 2, 4, 6), the palette indices (3, 7, 11, 15), and
four distinguishable fixture colors. It did **not** observe FCEUX.

Stage124 creates a **different generated Mapper-4 ROM**, rather than
changing the already-proven Stage119–121 fine-scroll fixture. On reset,
its CPU writes tile ID 1 to all 4096 bytes of logical nametable space,
then writes attribute `$E4` into each of the four 64-byte attribute
tables. It initializes all sixteen background palette slots with
synthetic colors. CHR bank0 is blank, and tile1 in CHR bank1 has both
pattern planes `FF` so its nontransparent pixel is always pattern3
after the genuine MMC3 CHR bank switch.

### Source-level observation

The pinned FCEUX `newppu` observer, injected behind
`VPD_NATIVE_SYNTHETIC_QUADRANT_COLORS` and activated by
`VPD_STAGE124_QUADRANT_PROBE=1`, accepts only source-level background
pixels after the MMC3 bank switch and scanline carry.

For each of the four **actual buffered nametable source addresses**,
it independently checks the attribute fetch address, raw byte
`E4`, selected shift, buffered palette bits, actual pattern value,
combined background index, palette lookup color, and final written
`XBuf` byte. It captures 16 samples per quadrant and requires all
four framebuffer colors to be distinct.

| Quadrant | Native background index | Palette RAM color | Expected XBuf byte |
|---|---:|---:|---:|
| Upper left | 3 | 0x30 | 176 |
| Upper right | 7 | 0x31 | 177 |
| Lower left | 11 | 0x32 | 178 |
| Lower right | 15 | 0x33 | 179 |

The output byte includes FCEUX's synthetic frame-pixel palette flags;
these numbers are not RGB values. When any check fails, Stage124 emits
a separate `VPD_STAGE124_REJECTED_QUADRANTS` marker, never PASS.

### Independent native negative controls

The runtime wrapper runs one positive ROM and three independent
negative controls under Xvfb:

1. A ROM with all attribute tables forced to 00.
2. A ROM whose four pattern3 palette colors have been made equal.
3. A ROM with the Stage124 observer disabled.

The three controls **must not emit the positive marker** and must not
exit unexpectedly. The wrapper does not accept a Python-only
certificate as a substitute for observed native pixels.

### Local/unit tests

```bash
python -m unittest discover -s tests -p 'test_fceux_stage124_quadrants.py' -v
```

The pinned native CI additionally compiles and links a full FCEUX
executable, generates ROMs privately, and runs
`tools/run_stage124_native_quadrants.py`.

## Evidence limitations

Passing unit tests checks generator, patch guards, marker parsing and
the separately compiled native observer. It is **not** equivalent to
passing the full FCEUX runtime test. Native proof is established only
by the successful pinned FCEUX workflow. Stage124 does not prove the
original game's palettes, sprites, scene geometry, frame timing, or
a working Nintendo Switch HD remake. Public git must never include
any original NES ROM, captured PPU memory, or game-derived graphics.
