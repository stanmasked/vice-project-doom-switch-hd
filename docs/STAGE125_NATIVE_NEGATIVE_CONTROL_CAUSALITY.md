# Stage125 — explicit native rejection for synthetic palette controls

Stage124 already established four distinguishable FCEUX XBuf colors:
176,177,178,179, with background indices 3,7,11,15 in the
independently generated Mapper-4 ROM. The pinned source revision is
`8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8`; the source and ROM
are not from the original Vice: Project Doom game.

## Tightening the negative controls

Before Stage125, the two negative ROMs were called "clean" if no
Stage124 PASS marker appeared during a short headless session. That
was a weaker statement than observing the native PPU reject a completed
64-pixel sample. An incomplete or slow session could also lack PASS.

Stage125 now requires **one explicit native REJECTED marker** for each
enabled negative control after all 16 samples from all four quadrants
have actually been collected. The marker includes independent counters:

- `bad_attribute` counts pixels with a buffered raw attribute other
  than E4.
- `bad_color` counts pixels whose observed palette lookup or final
  XBuf output disagrees with the quadrant's expected color.

Expected behavior:

| Native run | Raw attribute errors | Color errors | Required witness |
|---|---:|---:|---|
| Correct attribute E4, distinct colors | 0 | 0 | Stage124 PASS |
| Attribute 00 | Greater than 0 | Greater than 0 | Stage124 REJECTED |
| Attribute E4, coincident palette colors | 0 | Greater than 0 | Stage124 REJECTED |
| Observer disabled | No observation | No observation | Neither marker |

Both deliberate errors must also show four identical observed XBuf
colors (176,176,176,176). Contradictory, duplicated, incomplete or
forged rejection reports fail the strict Python verifier.

The disabled-observer control continues to require a live emulator
process without either PASS or REJECTED; it is not mislabeled as a
native rejection.

## Independent tests

```bash
python -m unittest discover -s tests -p 'test_fceux_stage124_quadrants.py' -v
python -m unittest discover -s tests -p 'test_fceux_stage125_negative_controls.py' -v
```

The full CI additionally builds real upstream FCEUX, runs the
synthetic positive ROM and the two erroneous ROMs under Xvfb, and
requires an explicit `STAGE125_NATIVE_NEGATIVE_CAUSAL_PROOF` summary
before considering native build acceptance successful.

**Evidence boundary:** This exercises an instrumented emulator and
generated synthetic images only. It does not prove any original-game
palette, level geometry or Nintendo Switch rendering behavior. Public
git contains neither game ROMs nor frame captures.
