# Stage141 — native FCEUX overflow status reset across two real frames

Stage140 established a **source/model-only** contract that the pinned
FCEUX `newppu` renderer resets `PPU_status = 0` after VBlank and
before the next pre-render period. Stage141 adds real native hooks
that observe the PPU status **immediately before and after the exact
reset assignment** and verify subsequent OAM selection and XBuf
after the frame boundary.

## Native diagnostic and frame-stable background isolation

The first pinned native run [39129250720](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39129250720)
confirmed first-frame overflow, before-reset overflow, after-reset clearing
and second-frame overflow in the nine-sprite fixture. Its framebuffer
comparison rejected, however: frame 1 emitted XBuf `143`, whereas the
same X64 position in frame 2 emitted `164`. This **does not** qualify
as the full two-frame XBuf proof.

Stage141 now uses a dedicated fixture generator derived from the proven
Stage137 OAM ROM. It changes **only** the four mirrored CPU PRG
`PPUMASK` immediate values from `$1E` (BG + sprites) to `$14`
(sprites enabled, background disabled, left-edge sprite rendering).
The sprite attributes, CHR banks, initial palette, complete OAM,
MMC3 transition, instruction sequence, and vector table remain
unchanged. Turning off background rendering makes X64 unambiguously
the universal backdrop when ninth OAM is rejected, even across the
subsequent frame, removing the background/scroll confound.

A ROM regression rejects any mutation beyond those four bytes.
This is a **controlled candidate fix**, not native validation
until a new pinned-FCEUX run succeeds.

## Native fixture and observation

Use two independently generated Stage141 sprite-only Mapper-4 ROMs derived from the Stage137 fixtures,
whose OAM slots are fully initialized and have already produced
native Stage137 evidence. Both fixtures retain their OAM layouts
across consecutive frames:

| ROM | 1st rendered row-124 overflow | Pre-reset status $20 | Just after reset $20 | Next frame row-124 overflow | XBuf both frames, X64..71 |
|---|---|---|---|---|---|
| `eight_visible` | no | no | no | no | 170 |
| `nine_overflow` | yes | yes | no | yes | 143 |

All four counted raster spans are taken from real FCEUX final XBuf,
for **2 × 2 × 8 = 32 native pixels**. The observer rejects
incorrect original OAM indices, ninth-slot Y/X, sprite-size mode,
counts, status values or actual pixel colors.

The native guard `VPD_NATIVE_SYNTHETIC_OVERFLOW_FRAME_RESET`
instruments the pinned source sites:

1. Immediately **before and after** the single source assignment
   `PPU_status = 0;` (not an arbitrary simulated reset).
2. After native OAM evaluation at source row 124.
3. At the real final XBuf write on raster row 126.

An ordered observer state machine requires eight first-frame XBuf
pixels, a subsequent true pre-render status reset, eight
second-frame XBuf pixels, and internally consistent OAM evidence.
It emits exactly one native PASS or explicit REJECT per scenario.
The native report marks `original_game_frame_reset_proven=no`.

An unchanged `nine_overflow` ROM falsely labelled
`eight_visible` must produce a rejection with genuine first-
and second-frame overflow and wrong XBuf values. An observer-off
control must produce no evidence while FCEUX keeps running.

## Independent tests and CI

```bash
python -m unittest discover -s tests -p 'test_fceux_stage141_native_frame_reset.py' -v
```

The suite validates the source patch anchors, exact hook count,
compiled C++ state machine for two frames, valid native certificates
and rejection of forged or noncanonical values. GitHub CI compiles
the instrumented upstream FCEUX and runs both ROMs under Xvfb.
Only the resulting native marker

`STAGE141_NATIVE_FRAME_OVERFLOW_RESET_PROOF`

on a fully successful pinned-FCEUX job supports claiming that
the real pre-render reset and subsequent output were observed.

**Evidence limits:** Stage141's two controls are *separate fixed-OAM
runs over two frames*, not a CPU-controlled change of sprite count
within one continuous run. It verifies before/after status and next-
frame rendering, without claiming an actual ROM update between
frames. A later experiment can test an NMI-driven OAM change without
weakening these controls. No commercial Vice: Project Doom ROM,
gameplay screenshot or Switch binary is part of this work.
