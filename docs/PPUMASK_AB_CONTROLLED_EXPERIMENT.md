# Stage 156 — private PPUMASK A/B raster experiment

This is a **controlled, temporary emulator intervention**, not an unmodified
original-game replay, a camera-speed measurement, or a ready Switch driving
stage. It uses only an owner-held NES ROM, matching read-only FM2 and private
FCEUX 2.6.5 outputs. **Do not commit** ROM, FM2, screenshots, palette arrays,
save states or raw emulator logs.

## Proven experimental observations

Two independent experiments replayed the same original USA ROM/FM2 twice:
a baseline with the original CPU program, and a diagnostic session where
**only at CPU PC $E38E on one chosen original FM2 frame** the accumulator
value immediately before STA $2001 was temporarily changed from $0E to
$06, which clears PPUMASK's background rendering enable bit.

A stricter repeat then registered the *next actual CPU instruction*, RTS
at **$E391**, and restored accumulator A back to **$0E before RTS**.
The original ROM, FM2 and all preceding movie frames remained unchanged.
Both strict repeats preserved exactly the same RGB/palette differences
as the initial experiments; the strict local Lua script refused to save
a terminal witness unless restoration was observed.

| Controlled CPU intervention | Original frame BEFORE | Target frame | Frame AFTER | Following frame |
|---|---|---|---|---|
| $E38E on FM2 frame 600 | 599: 0 changed px | 600: 0 | **601: 1,607 changed px** | 602: 0 |
| $E38E on FM2 frame 800 | 799: 0 changed px | 800: 0 | **801: 1,619 changed px** | 802: 0 |

In both pairs, **only rows Y=201–223** differ in the affected framebuffer.
RGB differences and NES palette-index differences affect the same number of
pixels. Each unmodified baseline capture's target frame (both P6 RGB and
palette bytes) is **byte-identical** to the independent earlier original
FCEUX Stage 1-1 road capture for frames 600 and 800.

These facts establish a **repeatable counterfactual screen-region effect**
of the late PPUMASK instruction after restoring A. They do **not** prove:
- That the $E38E CPU instruction itself executes on scanline 201, or any
  specific PPU scanline/dot; the FCEUX after-frame screenshot for an
  intervention on frame N first differs on its labelled frame N+1.
- That rows outside Y=201–223 could not be affected in a different stage or
  visible content state. An unchanged pixel is not proof of unmodified PPU
  state on its scanline.
- That original PPUMASK=$0E yields the diagnostic behaviour: the changed
  branch is deliberately **not original gameplay**.
- That the PPU raster split comes specifically from MMC3 IRQ, or that
  scroll X/Y, parallax, camera speed, car physics or collision were recovered.

## Reproduce privately

Prepare two new, separate empty directories and supply your local
owner-held ROM and matching FM2. **Never pass these into public CI.**
Run from the repo checkout using the same verified FCEUX binary:

    export VPD_PRIVATE_ROM_PAYLOAD_MD5='<owner ROM payload md5>'
    export VPD_PRIVATE_FRAME_COUNT='43652'
    export VPD_PRIVATE_FM2_PATH='/private/taotao-viceprojectdoom.fm2'
    export VPD_PRIVATE_AB_FRAME='600'
    export VPD_PRIVATE_AB_MODE='original'
    export VPD_PRIVATE_AB_DIR='/private/ab_600_original'
    fceux --no-config 1 --sound 0 \
        --loadlua tools/capture_private_ppumask_ab.lua /private/original.nes

Repeat with a new directory, VPD_PRIVATE_AB_MODE=probe_bg_off and
VPD_PRIVATE_AB_DIR=/private/ab_600_probe. The probe uses
memory.registerexec for original PC $E38E and $E391 and
memory.setregister for the diagnostic A update/restoration. It requires
the original read-only FM2 timeline to remain contiguous through N+2.
Some headless FCEUX builds may keep the GUI alive after emu.exit() even after
COMPLETE.txt was emitted; the completed witness, not GUI shutdown, is the
capture completion criterion.

Analyze the two **private** directories:

    python3 tools/audit_private_ppumask_ab.py \
        /private/ab_600_original /private/ab_600_probe \
        --target-frame 600 --out /private/stage156_ab_summary.json

The Python audit validates control/diagnostic provenance, original ROM and
FM2 conservation witnesses, exact 4-frame RGB + palette sizes, and agreement
of the pre-intervention images. It outputs **only numeric row and pixel
difference counts**, never content or source file paths. The current
accumulator-restoring tool writes an explicit restoration witness. Older
pre-restoration captures can be read for comparison but **must not** claim
the stronger restored-register control.

Synthetic-only public CI coverage:
- tools/capture_private_ppumask_ab.lua
- tests/test_private_ppumask_ab.lua
- tools/audit_private_ppumask_ab.py
- tests/test_audit_private_ppumask_ab.py

## Next authentic-game research step

We have shown a region's **sensitivity to the late PPUMASK control write**
under a specifically altered CPU execution. Recover the underlying
visible raster timing using an independent PPU dot/scanline source or
cycle-calibrated subframe trace, and determine which background/CHR states
apply during the driving road's display. Do not infer exact scanline
activation or world velocity just from the row-diff region.


## Stage 157 — four-frame PPUMASK response repeatability

New **owner-local original ROM + matching read-only FM2** tests were run in
FCEUX 2.6.5 with the same one-instruction diagnostic PPUMASK intervention
and CPU accumulator restoration before original RTS $E391 as Stage 156.
Two additional control/probe pairs targeted original movie frames **700 and
900**. Each run produced a valid private completion marker and all four
256×240 RGB/PAL frames; the emulator GUI remained open in this FCEUX build
after the finished capture, so the completion markers and actual files, not
the GUI process exit code, were treated as the capture witnesses.

Across all four original Stage 1-1 frame targets:

| Target CPU frame | First modified screenshot | Changed RGB pixels | Changed palette pixels |
|---:|---:|---:|---:|
| 600 | 601 | 1,607 | 1,607 |
| 700 | 701 | 1,630 | 1,630 |
| 800 | 801 | 1,619 | 1,619 |
| 900 | 901 | 1,618 | 1,618 |

In each case, screenshots N−1, N and N+2 were **byte-identical** between
unmodified and diagnostic captures. RGB and NES indexed-palette **pixel
change masks coincide at every pixel**, not merely by total counts.
The changed **row set is identical in all four independent cases**:

    Y = 201,202,203,204,205,206,207,209,210,211,212,213,
        214,215,216,217,218,219,220,221,222,223

This is a 22-row observed response extending over Y=201–223, with **row
208 unaffected** in every captured frame. This does not mean that the
original PPUMASK write occurs on row 201 or that it cannot affect other
pixels in different scenes.

### Independent CPU-clock correlation

Private original-game PC execution records, aligned with independently
captured after-frame CPU timestamps, locate original instruction **$E38E**
at the following *CPU-cycle phase relative to the previous FCEUX
after-frame callback*:

| Target frame | Cycles after preceding frame callback |
|---:|---:|
| 600 | 24,333 |
| 700 | 24,332 |
| 800 | 24,333 |
| 900 | 24,332 |

The spread is **one CPU cycle** across these samples. This demonstrates
stable callback-relative CPU timing and stable image response, **not an
absolute PPU scanline**: no independently calibrated PPU dot or scanline
origin for emu.registerafter was established. The CPU timestamps are from
separate genuine-ROM replay sessions, assuming the same CPU-cycle reset
epoch; exact cross-session alignment is checked numerically.

### Automated checks and evidence quality

New source-only tools/audit_private_ppumask_series.py reads a private JSON
manifest of three to twenty A/B capture pairs and runs the existing
single-pair witness/size/difference validator on every pair. It then
compares exact RGB and palette changed-pixel masks, enforces one changed
next-frame screenshot and an identical changed-row set, and optionally
joins private frame-clock and original-PC execution traces. Its public
output contains **no raw pixels, capture paths, ROM, FM2 or palettes**.

Synthetic-only tests/test_audit_private_ppumask_series.py exercises four
independent invented captures, optional CPU clocks and error cases for
different row sets, mismatched RGB/palette masks, target-frame errors,
invalid CPU epochs, missing witnesses and reused folders.

**Witness distinction:** the older private capture harness used for these
four completed sessions included a runtime assertion restoring CPU A before
RTS, but its completion marker did **not explicitly encode the restoration
field** now emitted by the newer reusable GitHub script. Consequently the
multi-case auditor does not mark restoration as explicitly witnessed for
these legacy captures unless the actual new witness field is present.
The published source-free numerical report distinguishes these claims.

Still required: an independent PPU dot/scanline timestamp source, exact
visible effect of CHR updates, original road scroll/camera reconstruction,
and actual integration of the driving mode into the Switch renderer.
