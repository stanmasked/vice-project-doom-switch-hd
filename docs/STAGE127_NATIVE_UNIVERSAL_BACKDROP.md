# Stage127 — transparent background CHR and universal palette color in native FCEUX

## Purpose

Stages124–126 linked the buffered nametable source, attribute byte
`E4`, selected 2-bit palette group, CHR pattern3, palette lookup and
final XBuf output in the pinned, instrumented FCEUX renderer. Stage127
tests an NES-specific edge case: when **both CHR pattern bitplanes are
zero**, the pixel still carries the buffered attribute palette bits
(0,4,8,12), but the palette entries in each group resolve to the same
universal background color.

This distinction matters in an HD renderer: selecting a palette group
does not imply that a transparent background pixel should render
a different color for each quadrant.

## Controlled Mapper-4 ROMs

The Stage124 generator now supports opt-in `transparent_chr=True` and
a restricted `backdrop_color` (`0x0F` or `0x1D`).
It preserves all CPU instructions, $E4 nametable attribute data,
horizontal scroll behavior and non-universal palette colors. It leaves
the CHR pattern tile blank, then initializes the four universal-color
palette entries ($3F00/$3F04/$3F08/$3F0C) together.

Three ROMs are generated at test time in private temporary storage:

| Run | CHR pattern | Universal background | Expected real XBuf |
|---|---|---|---|
| Baseline | 0 | 0x0F | 143,143,143,143 |
| Changed backdrop | 0 | 0x1D | 157,157,157,157 |
| Opaque negative | 3 | 0x0F | 176,177,178,179; native rejection |

Each positive run requires 16 real buffered background pixel observations
in each of four quadrants, with the attribute byte E4 and actual PPU
attribute source address/shift intact. The observed combined background
indices must be 0,4,8,12, not 3,7,11,15.

The contrast is **the actual stored XBuf byte** after FCEUX palette
lookup, not a synthetic calculation masquerading as native evidence.

An opaque-CHR negative control uses the original Stage124 ROM with the
transparent-background observer active. It must render the distinct
previously proven colors and emit a single
`VPD_STAGE127_REJECTED_TRANSPARENT_BG` after sampling all four groups.
A missing/duplicate marker or a false success fails the strict audit.

## Test requirements and limitations

```bash
python -m unittest discover -s tests -p 'test_fceux_stage127_transparent_bg.py' -v
```

The pinned native GitHub Actions build separately runs
`tools/run_stage127_transparent_bg.py` under Xvfb and requires
`STAGE127_NATIVE_UNIVERSAL_BACKDROP_PROOF`. Passing stand-alone C++ or
Python tests does not prove native emulator behavior.

This is a new synthetic ROM, not Vice: Project Doom art or a captured
original gameplay frame. No copyrighted image data, memory dumps or
original ROMs are committed. NES hardware dot timing and native
Nintendo Switch rendering remain unproven.
