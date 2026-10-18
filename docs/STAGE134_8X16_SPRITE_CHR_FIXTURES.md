# Stage134 — generated Mapper-4 8×16 sprite bank-and-tile controls

Stage133 is **natively confirmed** on pinned FCEUX, run
[39119182305](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39119182305):
four asymmetric 8×8 flip modes, 32 observed XBuf pixels, explicit
wrong-flag rejection and disabled-observer control.

Stage134 prepares a stronger **future native 8×16 fixture**, but the
Stage134 implementation in this commit is a **ROM-generator and
reference-model verification only**. It does not claim actual native
8×16 pixels.

The ROM uses PPUCTRL `$38`: bit 5 selects 8×16 sprites; bit 4
keeps the background pattern table at `$1000`. The OAM sprite has
X=64 and Y=120. Under 8×16 mode, OAM tile bit 0 selects the sprite
CHR pattern table: even tile ID 2 selects `$0000`; odd tile ID 3
selects `$1000`. The remaining tile bit selects an adjacent
upper/lower pair, tile2 and tile3.

Four synthetic controls differ only in the OAM tile-ID immediate
and vertical-reflection attribute immediate:

| Mode | OAM tile | CHR table | Upper source tile | Lower source tile |
|---|---:|---|---|---|
| odd_normal | 3 | `$1000` | pattern 1 | pattern 3 |
| odd_vertical | 3 | `$1000` | pattern 1 | pattern 3 |
| even_normal | 2 | `$0000` | pattern 2 | pattern 1 |
| even_vertical | 2 | `$0000` | pattern 2 | pattern 1 |

In the vertically reflected ROM, the raster's top half must sample
the *lower* source tile, and its bottom half the *upper* source tile.
These patterns use independently distinguishable sprite palette
colors from the previously established 8×8 fixtures. A direct write
to palette address `$3F12` includes PPUADDR and scroll restoration;
other background and sprite init bytes are identical.

`tools/make_stage134_sprite_8x16_rom.py` writes generated 49,168-byte
Mapper-4 files only into user-selected transient folders. The
`tests/test_fceux_stage134_sprite_8x16_rom.py` suite checks iNES
headers, CHR tile contents in both banks, the exact repeated PRG
immediate changes, strict PPUCTRL selection, and every input row
against the existing Stage132 independent 8×16 address model.

Reproduce generator/regressions:

```bash
python -m unittest discover -s tests -p 'test_fceux_stage134_sprite_8x16_rom.py' -v
python tools/make_stage134_sprite_8x16_rom.py /tmp/odd_vertical.nes --mode odd_vertical
```

**Evidence boundary:** no Stage134 native XBuf assertion is installed
yet. The next native experiment must observe real FCEUX OAM tile
parity, both fetched CHR source addresses, vertical source rows, final
two-bit pattern indices and actual XBuf across the upper/lower
eight-row boundary, including negative controls. It must reject any
missing or contradictory native marker. Original *Vice: Project Doom*
graphics and Nintendo Switch gameplay remain unverified; no original
game ROM or private capture is committed.
