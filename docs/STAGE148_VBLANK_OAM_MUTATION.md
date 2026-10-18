# Stage148 — CPU-written OAM mutation during VBlank

## Scope

Stage146 proved the pre-render status reset, selected OAM and two-frame
XBuf on a fixed synthetic ROM. Stage148 prepares a different experiment:
the *same executable ROM* changes its OAM entries between frames through
actual CPU writes to PPU registers $2003 and $2004. This milestone is
**ROM creation and static regression testing only**, not native proof.

## Independently generated synthetic Mapper4 fixtures

The ROM generator starts from the Stage144 eight_visible fixture with
eight on-row sprites. OAM0–6 are at X160, OAM7 at X64, and OAM8 is
disabled (Y=$FF). The original terminal self-JMP is replaced with
6502 CPU code in previously unused NOP padding, identically in each
mirrored 8-KiB PRG bank:

1. BIT $2002; BPL -5 — repeatedly poll bit7 until VBlank is signaled.
2. LDA #$1F; STA $2003 — point OAMADDR at the X coordinate of OAM7.
3. Five LDA immediate / STA $2004 pairs write OAM7 X and then OAM8
   Y, tile, attribute and X, with automatic address increments.
4. JMP to itself — a one-shot update, not repeated every frame.

| CPU write | activate_ninth | preserve_eight |
|---|---:|---:|
| OAM7 X | 160 | 64 |
| OAM8 Y | 120 | 255 |
| OAM8 tile | 2 | 255 |
| OAM8 attributes | 0 | 255 |
| OAM8 X | 64 | 255 |

Both ROMs use the same number of instructions, same write addresses,
and same CPU timing. The control rewrites the unchanged original OAM;
the intervention activates the ninth sprite at X64 while moving OAM7
from X64 to X160. Only five immediate bytes differ per PRG bank
(20 bytes across the four mirrored banks).

## Predictions requiring native validation

A fully initialized frame before the VBlank mutation should have
eight selected sprites, no overflow, and XBuf 170 at X64. After the
VBlank write, the activate_ninth case should have overflow $20 and
XBuf 143 because the ninth sprite at X64 is rejected, while the
preserve_eight control should stay clear with XBuf 170.

These are *predictions*, not measurements. The next native stage must
capture actual PPU $2003/$2004 CPU writes, the frame boundary, OAM
selection, overflow and real XBuf for both generated ROMs. FCEUX startup
frames and the exact timing of the VBlank write must be accounted for;
the first PPU reset and a real dynamic OAM transition are not the same.

## Regression & evidence boundary

Run the explicit test suite:

    python -m unittest discover -s tests -p 'test_fceux_stage148_vblank_oam_rom.py' -v

Tests validate 6502 opcode sequences, the signed -5 branch, exact
terminal self-loop address, five OAM data writes, identical CPU
instruction timing, four mirrored executable banks, interrupt vectors,
unchanged iNES header and CHR, strict immediate-byte differences, and
fail-closed rejection on malformed ROMs.

The ROMs are created in ephemeral test directories. This work includes
no original Vice: Project Doom assets, gameplay graphics, copyrighted
ROM image or playable Nintendo Switch build. The stage is not a native
FCEUX proof until independently confirmed by a later pinned native run.
