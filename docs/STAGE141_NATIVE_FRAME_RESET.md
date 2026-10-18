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
The subsequent pinned native run
[39131085609](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39131085609)
**still failed** with the same second-frame XBuf value: first=143,
second=164, invalid=8. Therefore background isolation did not explain
the discrepancy. Python regressions and C++/ROM checks passed, while
native FCEUX rejected the two-frame proof.

Stage143 adds *diagnostic-only* provenance to the existing native XBuf
hook: `pixelcolor` before palette adjustment, `havepixel` from the
sprite compositor, and `pixel & 3` from the background pixel. These
fields are captured from the first inspected pixel of each frame,
printed only on a native REJECT and forwarded to the CI failure summary.
They are not model values or accepted as a substitute for matching
every actual XBuf pixel in both frames. The observer still emits no
native PASS unless the full strict Stage141 gate succeeds. A compiled
fault-injection regression verifies that corruption of the last pixel
in the second frame still fails even when the first-pixel colors and
recorded diagnostics match.

The pinned native Stage143 diagnostic in
[39132581374](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39132581374)
settled the previously open ambiguity: first/second raw palette colors
were 15/36, both sprite-pixel flags were zero and both background
pattern bits were zero. The second-frame color change was not caused by
the ninth sprite becoming visible.

## Stage144–145: verified terminal JMP relocation fixes the two-frame ROM

The Stage137/141 fixture added OAM/PPU setup before the original Stage110
terminal absolute 6502 `JMP`, but retained its old destination address.
Because the program now occupied more bytes, the CPU repeatedly executed
injected instructions instead of idling, changing palette state after
the first frame.

Stage144's `make_stage144_stable_frame_rom.py` independently regenerates
each Stage141 synthetic ROM, validates all four 8-KiB mirrored PRG banks
and their interrupt vectors, and fixes exactly the two absolute-JMP
operand bytes in **each** bank (eight bytes overall). Header, CHR,
sprite geometry, palettes, and every other instruction remain intact.

The native FCEUX job
[39134434353](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39134434353)
finished **successfully** in all three GitHub Actions jobs.
The pinned FCEUX log contains:

`STAGE141_NATIVE_FRAME_OVERFLOW_RESET_PROOF native_fceux=yes synthetic_mapper4_only=yes cases=2 frames=4 samples=32 observed_pre_render_status_reset=yes overflow_reappears_next_frame=yes clean_frame_remains_clean=yes wrong_clean_control=rejected observer_off_control=clean original_game_multiframe_proven=no`

All four Stage144 ROM relocation regression tests passed. This is
actual native proof for the controlled four rendered frames and the
pre-render overflow reset, not proof about the original game.

## Stage146: same-binary causal regression against the stale JMP

The subsequent experiment adds an explicit paired negative control to
the **same** pinned FCEUX runner. It regenerates the original Stage141
nine-sprite ROM with the stale JMP, verifies that relocating its
terminal operands reproduces the fixed positive ROM exactly, and
requires the genuine stale ROM to be *rejected* by FCEUX with the
original first/second-frame XBuf difference 143/164, raw colors 15/36
and no sprite pixel. The fixed ROM must still pass before the
`STAGE146_NATIVE_STALE_JMP_CAUSAL_CONTROL` summary can be emitted.
The observer-off and false-clean controls remain mandatory.

Stage146 is now confirmed by the completed
[39136164059](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39136164059)
pinned native run: `STAGE146_NATIVE_STALE_JMP_CAUSAL_CONTROL` and the
original `STAGE141_NATIVE_FRAME_OVERFLOW_RESET_PROOF` both passed.
The old and corrected Mapper4 test ROMs differed by precisely eight
6502 JMP-operand bytes, and reproduced/stabilized XBuf 143→164/143→143.

## Stage147: positive pixel-source evidence

The native Stage141 observer already records raw `pixelcolor`,
`havepixel`, and background pattern bits from the actual raster
source alongside final XBuf. Previously it printed these only for
rejected frames. Stage147 adds an *independent positive* certificate
`VPD_STAGE147_NATIVE_FRAME_COLOR_SOURCE_PASS` for every accepted
two-frame ROM:

- `eight_visible`: raw palette color 42 and a selected sprite pixel
  in both frames; background pattern bits zero; XBuf 170.
- `nine_overflow`: raw palette color 15, no selected sprite pixel,
  background pattern bits zero; XBuf 143 in both frames.

This source gate executes only when pre-existing OAM, status and XBuf
checks are clean, preserving established negative-control rejection
counts. It catches a matching final XBuf with the wrong underlying
sprite/palette/background source. The native Python runner requires
one such marker **and** the existing Stage141 positive certificate
per scenario, before either can count toward a sweep.

A compiled C++ regression additionally alters only the raw palette
value on the second frame, preserving its nominal XBuf, and requires
a native-observer-style explicit REJECT. A separate Python suite
rejects duplicate, absent, malformed, noncanonical and forged source
certificates.

This work uses only synthetic Mapper4 fixtures and must not be
described as confirmed by pinned FCEUX until CI reports:
`STAGE147_NATIVE_TWO_FRAME_COLOR_SOURCE_PROOF`.
It does not validate original game graphics or a Switch build.

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
