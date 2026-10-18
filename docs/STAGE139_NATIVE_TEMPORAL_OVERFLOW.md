# Stage139 — Native temporal ninth OAM, sticky overflow and real XBuf

Stage137 was natively confirmed in [run #39124431670](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39124431670) (4 scenarios, 32 actual XBuf pixels, correct overflow and both controls). Stage138 added source/model temporal OAM fixtures. Stage139 adds actual pinned FCEUX `newppu` instrumentation at two distinct sprite-evaluation scanlines.

## Corrected synthetic CHR source

In NES 8×16 mode, the low bit of **OAM tile index 2** chooses the PPU pattern table at `$0000`. Stage138 initially populated only the other CHR table at `$1000`, which would have made its free-slot positive visibility control transparent. The Stage139 preflight additionally fills tile2/tile3 in the physical `$0000` bank with opaque two-bit pattern3, and a regression verifies those bytes. The background remains transparent, so XBuf `143` represents the universal backdrop, while visible sprite8 produces `170`.

## Native source observation

A guarded source patch instruments two real FCEUX locations:

- At `oamcounts[scanslot] = oamcount;`, record original OAM indices, selected count and actual `PPU_status & $20` for evaluation rows **124 and 132**.
- At the real XBuf assignment, record eight pixels at X=64..71 on raster rows **126 and 134**, which FCEUX corresponds to those evaluation rows.

The $20 sprite overflow flag is frame-sticky; it must not be read as a new event on every later line. Capturing both early and later evaluation rows differentiates the actual transition from an already-present overflow.

| Mode | Row 124: count / overflow / XBuf | Row 132: count / overflow / XBuf |
|---|---|---|
| `eight_stable` | 8 / no / 143 | 8 / no / 143 |
| `nine_late` | 8 / no / 143 | 8 / yes / 143 |
| `seven_plus_late` | 7 / no / 143 | 8 / no / 170 |
| `nine_early` | 8 / yes / 143 | 8 / yes / 143 |

The C++ observer validates every sampled pixel, original OAM index and count, 8×16 sprite mode, relevant row and status; it emits a PASS only after both complete eight-pixel spans. If any property is contradicted, it emits an explicit REJECT. The strict Python parser rejects malformed, noncanonical, duplicate and contradictory certificates.

Controls: run the **unchanged** `seven_plus_late` ROM while falsely declaring `nine_late` (must REJECT), and run `eight_stable` with observer disabled (must emit no evidence). Successful native sweep requires 4 × 16 = **64 actually rendered XBuf pixels**, the $20 transition and a positive freed-slot contrast.

## How to check

```bash
python -m unittest discover -s tests -p 'test_fceux_stage138_temporal_nine_oam.py' -v
python -m unittest discover -s tests -p 'test_fceux_stage139_native_temporal_nine.py' -v
```

CI extends the existing pinned native FCEUX build to compile the guarded `VPD_NATIVE_SYNTHETIC_TEMPORAL_NINE` hook, run the four generated ROMs under Xvfb and demand:

`STAGE139_NATIVE_TEMPORAL_NINE_PROOF`

**Evidence boundary:** Until pinned native CI actually completes with this marker, Stage139 is an implemented experiment, not a natively proven behavior. All ROMs are independently generated temporary Mapper-4 fixtures. No original *Vice: Project Doom* ROM, graphics or playable Switch build is part of these tests.
