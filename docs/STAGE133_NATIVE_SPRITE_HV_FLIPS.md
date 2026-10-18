# Stage133 — Native sprite horizontal/vertical reflection witness

## Experiment

Stage132 checks the pinned newppu source code for horizontal bit reversal, vertical row reflection and 8×16 pattern addressing. **Stage133 goes further:** it runs the actual instrumented FCEUX PPU on four separately generated Mapper-4 ROMs, each with an asymmetrical, fully opaque 8×8 sprite.

The tile pattern is deterministic and has no transparent pixels:

```text
pattern(row, column) = 1 + ((2*row + column) % 3)
```

Each ROM sets OAM sprite0 at X=64, Y=120 with tile2. The only variation between the four positive ROMs is the OAM attribute flag: `00`, `40` (horizontal), `80` (vertical), or `C0` (both). Program flow and CHR bytes are identical; four copies of one 6502 immediate differ in repeated PRG banks.

The sprite uses background-independent palette entries: pattern1 → `0x1A` (XBuf 154), pattern2 → `0x2B` (XBuf 171), pattern3 → `0x2A` (XBuf 170). This distinguishes each source column and makes mirrored outputs observable.

## Palette-slot fault isolation (18 October 2026)

A native run established the correct CHR source address `$1020`,
matching low/high CHR bytes and correct eight two-bit sprite patterns.
However, three pattern-2 pixels were emitted as XBuf `129` (palette
value `$01`), not XBuf `171` (the requested `$2B`), while pattern-1
and pattern-3 colors were correct. This is a *palette-slot mismatch*,
not evidence of a failed H/V flip.

For Stage133 **only**, the generator now explicitly writes `$2B` to
PPU palette address `$3F12` using a fresh pair of writes to `$2006`
followed by one `$2007` write. It then restores `$2006` to the
initial nametable address `$2000` and writes both `$2005` scroll
coordinates, avoiding an unintended palette-address rendering start.
This directly tests whether address-bound initialization repairs the
mismatch without changing the display's nametable or scroll state. Earlier synthetic
ROMs (Stages129–131) are byte-for-byte unchanged. ROM regression tests
require the explicit-address sequence in all four replicated PRG banks,
and all four flip modes use identical PRG instructions except OAM flags.

This is a controlled hypothesis, **not** a confirmed repair until the
pinned native CI proves the expected eight output bytes in all four
modes. Negative controls and the exact XBuf expectations remain enabled.

## Actual pinned-FCEUX evidence

The guarded injector records the genuine fetched sprite CHR low/high planes **before** FCEUX's horizontal bit reversal, plus the actual CHR address, row, OAM flip flags, and scan slot. A second hook observes the real raster pixel's chosen two-bit pattern, palette color, and final XBuf byte.

For eight consecutive pixels on the same sprite scanline, the observer independently verifies:

- Sprite tile2, X position 64, and the expected OAM H/V attribute bits.
- Low/high CHR bytes and source address `$1020 + source_row` read by FCEUX.
- A valid fetched row 0–7; horizontal reflection selects source column `7 − x` instead of `x`.
- Each actual pattern value and palette/XBuf byte matches the generated asymmetrical tile.
- The four runs share the same observed scanline; the V-flipped source row complements the baseline row to seven.

The positive marker `STAGE133_NATIVE_SPRITE_HV_FLIP_PROOF` is produced by the strict Python auditor **only after all four native runs have matched**.

An unchanged non-flipped ROM presented as horizontally flipped must produce an explicit native rejection after eight pixels; absence of evidence is not accepted as success. A disabled-observer control must emit neither PASS nor REJECTED and remain alive.

## Regressions and limitations

```bash
python -m unittest discover -s tests -p 'test_fceux_stage133_native_sprite_flips.py' -v
```

Unit tests verify byte differences between all four ROMs, each CHR pattern pixel, source-hook guards, fake/duplicated markers and separately compiled C++ observer behavior. They do not substitute for the full native FCEUX experiment.

CI builds the same pinned FCEUX revision as earlier stages and runs `tools/run_stage133_native_sprite_flips.py` under Xvfb. Stage133 is **not complete until the full pinned FCEUX CI is green**.

The current Stage133 experiment covers 8×8 sprites. Stage132's 8×16 mapping is only source/reference-model checked. Original Vice: Project Doom graphics, sprite identities, game timing and Nintendo Switch rendering remain unverified. Generated NES ROMs and captured PPU contents are never published.
