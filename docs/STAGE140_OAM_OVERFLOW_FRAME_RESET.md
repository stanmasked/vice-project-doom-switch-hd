# Stage140 — overflow status across frame boundaries (source/model)

The pinned FCEUX native Stage139 run [39126349578](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39126349578)
proved four time-dependent 8×16 OAM scenarios, including a late ninth
sprite and its reappearance when the eighth slot is freed. Its native
proof covers 64 real XBuf samples and independent observation of OAM
selection on source rows 124 and 132.

Stage140 targets a **different time dimension**: the status bit
`PPU_status & $20` persists within a frame after a ninth sprite has
triggered overflow, but must be cleared by the renderer's pre-render
reset so that the next frame begins with a clean status.

## Pinned-source evidence

The exact pinned upstream `src/ppu.cpp` has:

- VBlank NMI event `if (VBlankON) TriggerNMI();`
- Completed VBlank lines, then a comment marking the dummy scanline
- `PPU_status = 0;` before rendering for the next frame
- A separate subsequent real OAM-evaluation pass that executes
  `PPU_status |= 0x20;` if a ninth sprite qualifies

`tools/audit_stage140_overflow_frame_reset.py` independently checks
the ordered reset source anchors and reuses the anchored Stage136
native OAM-overflow source audit. It fails closed on missing,
duplicated, reordered or distant reset operations.

## Independent source/model controls

The companion Python reference model resets the emulated status at
the beginning of each frame, retains the overflow bit across later
scanlines, and allows it to be set again by a ninth sprite in a later
frame. Tests cover:

1. Nine sprites trigger overflow in frame A, eight sprites do not in B.
2. Nine → eight → late ninth: overflow clears at frame B, reappears
   only in the lower eight-row interval of frame C.
3. A ninth sprite leaves the visible region but its overflow bit
   remains set until the next pre-render reset.
4. An eighth slot freed for the late sprite does not set overflow.
5. Invalid frame counts, source OAM lists, scanlines and sprite
   heights are rejected.
6. Tampering with the reset site/order is rejected.

Run:

```bash
python -m unittest discover -s tests -p 'test_fceux_stage140_frame_overflow_reset.py' -v
python tools/audit_stage140_overflow_frame_reset.py /path/to/pinned/fceux/src/ppu.cpp
```

A successful source audit emits
`STAGE140_PINNED_OVERFLOW_FRAME_RESET_SOURCE_PASS`.

**Evidence boundary:** Stage140 is *source/model only*. It has no
instrumented cross-frame observation from a running FCEUX binary.
A future native experiment should record the status immediately
before and after pre-render reset and through the next frame, using
synthetic frames with different OAM counts, and reject forged frame
boundaries. Previous native Stage139 proof is not a substitute for
this additional experiment. No original Vice: Project Doom ROM,
copyrighted graphics, or Switch gameplay is involved.
