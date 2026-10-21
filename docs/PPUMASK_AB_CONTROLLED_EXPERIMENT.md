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
