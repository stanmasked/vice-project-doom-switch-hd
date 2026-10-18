# Stage126 — Native single-palette-entry counterfactual on pinned FCEUX

## What Stage124–125 established

Pinned native FCEUX run 39079450354 confirmed actual four-color
background XBuf output (176,177,178,179) on a generated Mapper-4 ROM,
with an observed attribute byte E4, buffered quadrant bits and CHR
pattern3. Stage125 adds explicit native REJECTED witnesses when
attribute tables or palette colors are intentionally corrupted.

Stage126 tests the sharper, independent causal question: **if exactly
one byte of palette initialization changes and the nametable, attribute
bytes, CHR, scroll timing and rest of the palette do not, will only its
corresponding XBuf quadrant change?**

## Paired ROM construction

The Stage124 ROM generator now has a guarded
`targeted_quadrant=0|1|2|3` option. It changes only the immediate byte
of one 6502 `LDA #color` before the corresponding `STA $2007`. PRG
bank repetition causes four changed bytes in the complete iNES image,
at the same bank-relative offset. The ROM header, CPU timing (same
instruction count), all CHR bytes, the attribute byte E4 and the other
15 palette values remain identical. Unit tests compare the complete
generated images byte for byte.

The baseline XBuf colors and expected target interventions are:

| Target quadrant | Baseline | Expected native XBuf |
|---|---|---|
| 0, upper left | 176,177,178,179 | **180**,177,178,179 |
| 1, upper right | 176,177,178,179 | 176,**181**,178,179 |
| 2, lower left | 176,177,178,179 | 176,177,**182**,179 |
| 3, lower right | 176,177,178,179 | 176,177,178,**183** |

The observer rechecks each actual buffered nametable source address,
attribute-fetch address, E4 byte, quadrant shift, decoded palette bits,
CHR pattern, background index, palette lookup and final written XBuf
value. It requires 16 pixel samples for each of four quadrants per
variant (256 intervention samples total) and that exactly one quadrant
changes in each run. The unmodified baseline is captured in a separate
real FCEUX process by the Stage124 native runner, not generated as a
fake marker.

An additional negative control presents the unchanged baseline ROM
with a request to observe target0's changed color. FCEUX must complete
all 64 pixel samples and produce
`VPD_STAGE126_REJECTED_PALETTE_DELTA`. An absent marker, duplicated
marker or false PASS causes the native runner to fail.

## Scope and execution

```bash
python -m unittest discover -s tests -p 'test_fceux_stage126_palette_delta.py' -v
```

CI builds the pinned FCEUX revision, checks previous stages, and then
runs `tools/run_stage126_palette_delta.py` under Xvfb. The exact
success marker is `STAGE126_NATIVE_SINGLE_PALETTE_ENTRY_DELTA_PROOF`,
issued **only after real emulator output** and the negative control
have passed. Python and C++ mock tests alone are not the native proof.

Nothing here confirms original Vice: Project Doom palette bytes,
sprites, level geometry or a running Nintendo Switch HD renderer.
No game ROMs or screenshots are published.
