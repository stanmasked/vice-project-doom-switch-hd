# Stage150 — Native dynamic CPU OAM writes → selected sprite → XBuf

## Distinction from prior proof

Stage149 confirmed ten actual CPU OAM register writes across two
separate synthetic Mapper4 ROMs in pinned FCEUX, including a high $2002
CPU read and native masking of OAM sprite attribute bytes.

Stage150 investigates a **different claim**: whether the same running
synthetic ROM's OAM writes during VBlank cause the next rendered frame
to show a changed sprite evaluation and real XBuf pixels. This stage
must not be called natively confirmed until its own strict marker is
present in a fully successful pinned-FCEUX GitHub Actions run.

## Native source observations

The Stage150 injector adds two further guarded hooks after the existing
Stage149 real CPU register, Stage141 pre-render/OAM and raster hooks:

1. At the pinned newppu OAM evaluation statement
   \`oamcounts[scanslot] = oamcount;\`: record the actual evaluation for
   source row 124, including eight original OAM indices, overflow bit20,
   the selected count, the X coordinate of OAM7, and the Y/X of OAM8.
2. At \`*ptr = PaletteAdjustPixel(pixelcolor);\`: sample actual final
   XBuf at X64..71 on output row126, with raw palette color,
   \`havepixel\`, 8x8 sprite mode and background pattern bits.

The state machine partitions observations by the actual Stage149 CPU
OAM write counter (zero before the VBlank change, five afterward).
It must collect eight pre-change and eight post-change raster pixels
inside each native process. Partially initialized startup frames are
not accepted as the pre-change reference.

## Expected native experiment

| Property | Before CPU writes | activate_ninth after | preserve_eight after |
|---|---:|---:|---:|
| OAM selected | 8 | 8 | 8 |
| Overflow bit20 | Clear | Set | Clear |
| OAM7 X | 64 | 160 | 64 |
| OAM8 Y | 255 | 120 | 255 |
| XBuf at X64..71 | 170 | 143 | 170 |
| Raw color | 42 | 15 | 42 |
| Selected sprite pixel | Yes | No | Yes |

A correct native result connects VBlank CPU writes to subsequent
real OAM evaluation and XBuf, not just a source-code model. The same
intervention ROM falsely labelled \`preserve_eight\` must be rejected
by **both** the Stage149 CPU observer and Stage150 PPU observer.
A separate observer-off test must produce no PASS or REJECT markers.

## Strict evidence boundary

The Stage150 acceptance marker is:

\`STAGE150_NATIVE_DYNAMIC_OAM_TO_XBUF_PROOF\`

It may only be emitted after two positive independent native ROM
runs, 32 verified raster pixel samples, the wrong-label rejection and
observer-off control. Python parsing rejects contradictory, malformed,
missing or noncanonical certificates. C++ regressions inject a
corrupted second-frame XBuf pixel and must cause rejection.

All ROMs are generated from self-authored 6502 code. No original
Vice: Project Doom ROM, proprietary assets, gameplay footage, or
Nintendo Switch binaries are required or published. This isolated
emulator test still does not prove that the original game graphics,
HD remake graphics, or Switch runtime work.

**Current stage state:** instrumentation and regression harness are
implemented; only a fully successful pinned FCEUX CI with the marker
above confirms native behavior.
