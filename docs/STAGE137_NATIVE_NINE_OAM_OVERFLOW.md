# Stage137 — native FCEUX ninth OAM sprite, overflow and XBuf

## Experiment

Stage136 established the pinned FCEUX source algorithm for selecting the
first eight OAM sprites and setting status bit `$20` on the ninth.
Stage137 instruments the same pinned native FCEUX `newppu` binary to
link that evaluation to **actual framebuffer XBuf pixels**, not merely
a source-level or C++-mock prediction.

A first native run 39123374368 rejected the eight-visible control:
`VPD_STAGE137_REJECTED_NINE_OAM case=eight_visible invalid=8
row=122 eval_row=120 count=8 overflow=yes xbuf=170`.
The visible sprite and selected OAM count were correct, but status bit
`$20` was set unexpectedly. In that version only the intended eight
OAM records had been initialized; all remaining entries depended on
emulator power-on contents. The generator now deterministically fills
**all 256 OAM bytes** with `$FF` using a 6502 indexed `$2004`
write loop, resets `$2003` to zero and only then installs the chosen
eight or nine entries. In the eight-visible control the unused ninth
record must be observed as Y=`$FF` and X=`$FF`. This is a
hypothesis-driven repair, not accepted until native CI succeeds.

Four temporary, wholly synthetic NES Mapper-4 ROM variants use sprite
CHR tile2 (opaque two-bit pattern3, palette `$2A`) and a transparent
background tile1 (universal backdrop `$0F`):

| ROM scenario | OAM slots | Expected overflow | XBuf at X64 |
|---|---|---|---|
| `eight_visible` | OAM0–6 at X160, OAM7 at X64 | No | 170 (visible OAM7) |
| `nine_overflow` | OAM0–7 at X160, OAM8 at X64 | Yes | 143 (ninth sprite absent) |
| `ninth_offscreen` | OAM0–7 at X160, OAM8 above scanline | No | 143 (offscreen ninth) |
| `nine_8x16` | Nine same-row 8×16 sprites | Yes | 143 (ninth absent in lower half) |

The source hook is guarded by
`VPD_NATIVE_SYNTHETIC_NINE_OAM` and installed into pinned FCEUX
`ppu.cpp` **after** the earlier Stage135 hooks. At the actual sprite
evaluation pass, it captures selected count, all eight original OAM
indexes, overflow bit, ninth entry's Y/X and scanline.
At the actual final XBuf write, it checks the recorded evaluation and
last rendered color. The 8×16 case samples on or after scanline 132
to exercise the lower eight-row half. The expected universal backdrop
XBuf `143` was separately established by Stage127.

Each accepted native scenario requires eight raster-pixel observations.
The Python runner verifies a complete four-scenario sweep with
`4 × 8 = 32` actual pixel samples. It also runs an unchanged
`nine_overflow` ROM falsely claiming `eight_visible`, which must
produce an explicit REJECT marker; an observer-off run must remain
alive and emit neither PASS nor REJECTED.

## Regressions

```bash
python -m unittest discover -s tests -p 'test_fceux_stage137_nine_oam.py' -v
```

The suite checks ROM bytes and OAM writes, guarded source injection,
duplicate/missing/forged native witness rejection, a compiled C++ mock
of the native observer and the negative overflow control.

The dedicated **native** result is only valid when GitHub Actions'
pinned FCEUX job prints:

`STAGE137_NATIVE_NINE_SPRITE_OVERFLOW_PROOF`

Before that, unit/model passes do **not** prove native XBuf suppression.
This stage uses synthetic NES fixtures only. It does not prove original
Vice: Project Doom OAM content, timings or a playable Switch remake.
