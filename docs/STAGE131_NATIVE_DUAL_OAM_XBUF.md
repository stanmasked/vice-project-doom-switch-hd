# Stage131 — two overlapping OAM sprites observed in native newppu

## Experiment and required evidence

Stage130 verified the pinned FCEUX sprite source order, while Stage129
proved one genuine OAM sprite and a background in real FCEUX. Stage131
creates five distinct, **generated-only Mapper-4 ROMs** with **two**
overlapping OAM entries at X=64, Y=120 and two independently different
sprite palettes. Both CHR bitplanes in tile2 are FF; tile3 is blank.

Each ROM writes the two entries sequentially using CPU writes to
`$2003/$2004`. Sprite palette group0 color3 at `$3F13` is `$2A`
(XBuf 170). Sprite palette group1 color3 at `$3F17` is `$38`
(XBuf 184). Normal background pattern is opaque, with XBuf color
176–179 determined by its observed attribute quadrant. The transparent
background control omits only background tile1 CHR.

## Cases and expected real framebuffer behavior

| Case | OAM0 | OAM1 | Background | Winner / XBuf | Sprite-0 hit |
|---|---|---|---|---|---|
| First front | Palette0 opaque | Palette1 opaque | Opaque | OAM0 / 170 | Yes |
| Palettes swapped | Palette1 opaque | Palette0 opaque | Opaque | OAM0 / 184 | Yes |
| First transparent | CHR tile3 blank | Palette1 opaque | Opaque | OAM1 / 184 | No |
| First behind | Palette0 behind background | Palette1 front | Opaque | Background / 176–179 | Yes |
| First behind, BG transparent | Palette0 behind background | Palette1 front | Transparent | OAM0 / 170 | No |

The key ordering rule under test: the first nontransparent OAM sprite
claims the pixel **before** checking its background priority. Therefore
OAM0 may hide behind opaque background, still block OAM1 and set
sprite-0 hit.

A new guarded raster hook captures *both* OAM records, their actual
raster CHR patterns, the identity of the first sprite claiming the
pixel, the background pattern and buffered nametable source, the PPU
sprite-0 status bit and final XBuf pixel. It samples eight real
consecutive pixel positions on one overlapped scanline in the pinned
FCEUX `newppu`. A single PASS is emitted only if every sampled
component matches the scenario.

## Negative controls

One separate ROM makes **both** overlapping sprites transparent but
requests the first-transparent/second-opaque scenario. The native
observer must sample eight pixels and explicitly emit
`VPD_STAGE131_REJECTED_DUAL_SPRITES`; absence of a marker does
not count as a passed rejection.

Another run uses the original first-front ROM with the Stage131
observer disabled. It must produce neither PASS nor REJECTED and
must remain alive during the observation window.

The Python report parser rejects missing, duplicated, mismatched or
fabricated pass/reject markers. Independent tests additionally compile
and exercise the observer as C++11, verify byte changes in all 8 KiB
PRG banks, and test the guarded FCEUX source injector. These test
fixtures are **not** substitutes for the full native FCEUX experiment.

## Reproduction and limits

```bash
python -m unittest discover -s tests -p 'test_fceux_stage131_dual_sprite.py' -v
```

CI runs the full `tools/run_stage131_native_dual_sprite.py` on the
pinned original FCEUX revision via Xvfb, after prior PPU tests, and
requires `STAGE131_NATIVE_DUAL_OAM_PRIORITY_PROOF`.

The stage remains **unconfirmed** until that complete native CI is
green; a code commit or C++ unit test alone does not prove live
dual-sprite behavior.

No original Vice: Project Doom ROM, character art, enemy sprite,
PPU dump, or copyrighted assets are stored in public GitHub. This
experiment does not establish original-game graphics or a functional
Nintendo Switch HD renderer.
