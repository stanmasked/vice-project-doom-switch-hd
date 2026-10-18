# Stage106 — native MMC3 CHR register writes relative to FCEUX source frame windows

Prior stages 102–105 independently instrumented the pinned FCEUX PPU
source-level VBlank assignments and CPU reads of $2002. Stage106
extends the same **internal FCEUX PPU tick clock** to one mapper
write path: MMC3 CPU register-data writes to $8001 when the selector
points to CHR registers 0–5.

## Pinned source and scope

The original `src/boards/mmc3.cpp` of FCEUX revision
`8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8` has Git blob
`f0eb52d2a862c87e1617974de0d0c486aac6c240`.
The exact original bytes must match. The opt-in source hook appears
inside `DECLFW(MMC3_CMDWrite)`, *after* its $8001 register-data
dispatch and before the case break. It excludes PRG selectors 6–7
and does not observe unrelated mapper implementations.

The project adds no FCEUX fork, no original game assets, and no
per-event register logs. The hook is compiled only when
`VPD_NATIVE_SYNTHETIC_MMC3_CHR` and
`VPD_NATIVE_SYNTHETIC_EVENT_ORDER` are explicitly defined, and
its aggregate sink is enabled only with environment variable
`VPD_STAGE106_MMC3_CHR_PROBE=1`. The existing Stage104
`VPD_STAGE104_EVENT_ORDER_PROBE=1` is used to maintain source
window state. Without these flags there is no new output.

## Original synthetic mapper-4 test program

The Stage106 NROM-like **MMC3 mapper-4** iNES image is created
entirely in an ephemeral GitHub Actions runner and is not committed.
It has 32 KiB of independently authored 6502 PRG in four identical
8 KiB banks, 16 KiB of zero-valued CHR, and a valid MMC3 header.
The CPU loops over:

    LDA $2002
    LDA #$02
    STA $8000
    LDA $00
    EOR #$01
    STA $00
    STA $8001
    JMP $C000

The test intentionally alternates CHR register 2 values while also
polling PPUSTATUS. This exercises the **source-level mapping command**
but deliberately contains no meaningful tile pixels to render.

## Native gated evidence

After 4096 MMC3 CHR register writes, a one-shot marker contains:

- Counts of writes with changed CHR register values
- Counts inside and outside FCEUX source VBlank windows
- Counts in a source window after a high-bit CPU $2002 read
- Minimum/maximum elapsed **internal emulator tick units**
  since the source window entry, plus invalid-event count

The verifier rejects malformed, missing, duplicated or contradicting
markers. A second real-FCEUX run turns off Stage106's opt-in and
requires the emulator to survive a control window without a marker.
The C++11 and Python tests exercise the isolated hook and its
negative cases independently of the emulator build.

## What is NOT established

Even an actual native MMC3 source register write does **not** prove
that a different CHR bank was fetched by the PPU for visible
background pixels. Stage106 contains no PPU fetch or pixel evidence.
Source windows are FCEUX-internal events; they do not independently
measure NES VBlank edges or original game's camera and level geometry.
All original game ROM data, PPU captures and binary artifacts remain
private. HD background replacement stays **disabled**.

Run local source and C++ acceptance checks without a ROM:

    python3 -m unittest discover -s tests -p 'test_fceux_stage106_mmc3_chr.py' -v

Upstream pinned sources:
https://github.com/TASEmulators/fceux/blob/8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8/src/boards/mmc3.cpp
