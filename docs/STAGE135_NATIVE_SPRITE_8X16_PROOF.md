# Stage135 — Native FCEUX 8×16 sprite CHR bank and tile-half experiment

## Evidence and intent

Stage133 already established real native FCEUX 8×8 H/V flips and 32
actual XBuf pixels on the synthetic Mapper-4 ROM. Stage134 separately
generated four controlled 8×16 ROMs and verified their OAM and CHR
layout. Stage135 adds the **first actual FCEUX 8×16 runtime
instrumentation**, without changing the generated assets.

The four cases `odd_normal`, `odd_vertical`, `even_normal`,
`even_vertical` select OAM tile3 or tile2 with PPUCTRL bit5 set
(8×16 mode). In 8×16 mode the tile ID bit0, **not** PPUCTRL's
8×8 sprite table bit, selects the CHR pattern table. The tile pair
itself has deliberately different nonzero two-bit patterns for its
upper and lower eight-pixel heights:

| Case | CHR bank | Source upper XBuf | Source lower XBuf |
|---|---|---:|---:|
| odd_normal / odd_vertical | `$1000` | 154 | 170 |
| even_normal / even_vertical | `$0000` | 171 | 154 |

In vertical-flip runs, the **lower source half must appear first on
screen** and the upper source half afterward. The observer samples
one complete eight-pixel horizontal span in each half, checks their
real source row and CHR low/high plane bytes, checks the exact CHR
source address, verifies OAM tile and attribute flags and then checks
the actual `pixelcolor` and final XBuf values.

### Pinned native changes

The guarded FCEUX patch injector adds two source-site hooks to the
same pinned upstream `newppu` as Stage133:

1. At the real sprite pattern fetch, accept only genuine OAM index0,
   tile2/3, not dummy OAM slots. Observe the actual 8×16 flag,
   source row, address, both CHR bytes, palette flags and tile ID.
2. At the real final raster XBuf store, check the actual sprite CHR
   pixel index and compare color/XBuf against the observed CHR row.

The observer emits a native PASS only after eight samples in *each
distinct source half*, with a consistent rendered row and correct
vertical source-half order. The emitter produces a REJECTED witness
if any byte, row, bank, pattern, color or OAM attribute contradicts
the controlled ROM. It does not accept missing data as success.

### Causality and negative tests

The positive sweep comprises 4 × 16 = 64 actual output pixels,
subject to native execution. An unchanged **odd-normal ROM**
presented as **even-normal** must emit a native
`VPD_STAGE135_REJECTED_8X16`; a disabled-observer run must remain
alive and produce no false markers. A strict independent Python
parser demands exactly one full report per case and rejects forged,
duplicated or internally contradictory claims.

Separately compiled C++11 unit fixtures prove observer behavior for
four modeled test cases and a wrong-bank control; those fixtures are
**not** native FCEUX proof.

```bash
python -m unittest discover -s tests -p 'test_fceux_stage135_native_sprite_8x16.py' -v
```

GitHub CI extends the existing pinned FCEUX compilation and invokes
`tools/run_stage135_native_sprite_8x16.py` under Xvfb.
Only a successful job with
`STAGE135_NATIVE_SPRITE_8X16_PROOF` establishes the native result.
This stage remains **unconfirmed** until that condition holds.

All ROM data are independently generated in temporary private runner
directories. Nothing in Stage135 validates original Vice: Project Doom
sprites, a commercial gameplay capture, or a playable Nintendo Switch
remake.
