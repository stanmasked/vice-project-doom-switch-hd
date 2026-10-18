# Stage129 — Native OAM sprite0 vs background priority and XBuf

## New evidence target

Stage128 audited the pinned FCEUX `src/ppu.cpp` sprite compositor
source. It was not a sprite-rendering runtime proof. Stage129 generates
a separate synthetic Mapper-4 NES ROM whose CPU directly writes one
OAM sprite0 entry to `$2003/$2004`, sets both sprite and background
pattern tables to `$1000`, and enables sprite and background rendering.

Its generated background fills all nametables with tile1 and E4
attribute bytes, while CHR tile2 supplies a separate filled sprite
pattern. Both pattern bitplanes of the filled tile equal FF. Sprite0
has coordinates Y=120, X=64 and selects tile2, or blank tile3 in the
transparent-sprite control. The sprite palette uses a dedicated entry
`$3F13=0x2A` (expected XBuf byte 170). This leaves the
universal backdrop and four independently checked background palettes
from Stage124 intact.

The runtime observes a single eight-pixel overlap row in the **real
pinned FCEUX newppu process**, including the sprite0 CHR pattern
read from the OAM render buffer, OAM Y/tile/attribute/X, the
background pattern, the sprite-0 status bit, buffered nametable
quadrant and final written XBuf byte.

## Native test matrix

The intended six distinct cases are:

| Case | BG | Sprite | Sprite priority | Expected output |
|---|---|---|---|---|
| Opaque / front | pattern3 | pattern3 | front | sprite color 170, sprite0 hit |
| Opaque / behind | pattern3 | pattern3 | behind | background color 176–179, sprite0 hit |
| Transparent / front | pattern0 | pattern3 | front | sprite color 170, no hit |
| Transparent / behind | pattern0 | pattern3 | behind | sprite color 170, no hit |
| Zero sprite | pattern3 | pattern0 | front | background color 176–179, no hit |
| Sprite mask disabled | pattern3 | pattern3 | front | background color 176–179, no hit |

Source nametable addresses are observed, not assumed to come from
page $2000; the native observer derives the expected BG color from
the actual two-bit attribute quadrant. A separate disabled-observer
control must produce **neither** a PASS nor a REJECTED marker.

A sprite marked *behind the background* may still set the sprite0
hit bit when both sprite and background CHR pixels are nonzero. This
is measured independently from whether the sprite is visible.

The generator validates boolean controls and never checks in a ROM,
captured OAM, original game art or a framebuffer. The Python auditor
requires exactly one full 8-pixel native marker per scenario; empty,
duplicated, contradictory or malformed evidence fails closed.

## Verification

```bash
python -m unittest discover -s tests -p 'test_fceux_stage129_sprite_oam.py' -v
```

GitHub Actions additionally compiles the pinned FCEUX revision with
a guarded sprite raster hook, generates all six ROMs and the disabled
observer control in a private runner directory, and runs
`tools/run_stage129_native_sprite_oam.py` under Xvfb. The
`STAGE129_NATIVE_SPRITE0_BG_PRIORITY_PROOF` marker is contingent
on real upstream emulator observations and is **not** accepted from
the separately compiled C++ test fixture.

A passing source audit or C++ mock does not establish native OAM
sprite rendering. Nor does any synthetic evidence establish an
original Vice: Project Doom character, enemy, sprite, palette or
running Nintendo Switch HD renderer.
