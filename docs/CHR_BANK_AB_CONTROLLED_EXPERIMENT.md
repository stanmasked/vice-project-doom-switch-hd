# Stage 158 — private CHR register A/B evidence

Original media remains PRIVATE. These observations use the matching USA
NES ROM and read-only FM2 inside genuine FCEUX 2.6.5. Public GitHub stores
only source-only tools, invented tests and aggregate results, never ROM, FM2,
PPM, palette data, CHR resources or original game screenshots.

## Completed experiment: MMC3 CHR register #1

At original CPU PC $E387 (STA $8001, A=02, MMC3 CHR register 1),
one diagnostic FCEUX replay temporarily replaced A=02 with A=00.
At the next original instruction PC $E38A, CPU accumulator A was
restored to 02 before further unmodified CPU execution. Source ROM and FM2
bytes were not edited. The private captures independently checked
read-only movie playback and uninterrupted callback frames through N+2.

| Target frame | Original/probe image frames | RGB changed pixels | Palette changed pixels |
|---:|---|---:|---:|
| 600 | 599, 600, 601, 602 | 0 at each frame | 0 at each frame |
| 800 | 799, 800, 801, 802 | 0 at each frame | 0 at each frame |

All eight paired P6 RGB and NES indexed palette files are byte-identical.
This is a **negative observation in the chosen four-frame windows**, not
proof the CHR bank is unused, identical or visually inactive elsewhere.
There is no inference of scanline activation or camera speed.

The private original control frames were captured earlier during PPUMASK
research, with their own verified control completion markers. The
intervention runs used an equivalent private research script and different
completion metadata. These old authentic observations were compared
locally, NOT passed through the new standardized GitHub auditor or
retroactively marked as if they shared its witness format.

## Reusable strict protocol

A standardized private control/probe harness is provided in:
- tools/capture_private_chr_bank_ab.lua
- tools/audit_private_chr_bank_ab.py

The capture script accepts these local environment variables:
- VPD_PRIVATE_CHR_AB_DIR: NEW empty private output directory
- VPD_PRIVATE_CHR_AB_MODE: original or probe_chr1_zero
- VPD_PRIVATE_CHR_AB_FRAME: selected original zero-based FM2 frame
- VPD_PRIVATE_FRAME_COUNT: the original FM2 frame count
- VPD_PRIVATE_FM2_PATH: local matching FM2 path
- VPD_PRIVATE_ROM_PAYLOAD_MD5: local original PRG+CHR payload MD5

With the above variables set, run the local FCEUX binary with:

    --loadlua tools/capture_private_chr_bank_ab.lua /private/original.nes

Repeat with a separate new output directory in probe_chr1_zero mode.
The private auditor then accepts:

    python3 tools/audit_private_chr_bank_ab.py /private/control /private/probe --frame 600

The auditor demands identical private ROM identity hashes in the two
completion witnesses, a read-only FM2 assertion, frame continuity, exactly
one execution of both original CPU instructions, restoration of the
accumulator before $E38A, and valid captures for N-1 through N+2.
It intentionally does not claim to independently hash FM2 movie bytes.

Public synthetic CI regressions:
- tests/test_audit_private_chr_bank_ab.py
- tests/test_private_chr_bank_ab.lua

## Limitations and next experiment

In Stage 156/157, altering PPUMASK at $E38E produced a measurable lower
framebuffer effect at Y=201-207 and 209-223. In contrast, the single
CHR register #1 substitution at $E387 did not alter captured framebuffer
pixels at frames 600 or 800. These are distinct interventions; an
unchanged image does not imply an unchanged CHR mapping or PPU state.

Investigate MMC3 CHR register #0 via original CPU PC $E380 with
X-register restoration at the next instruction $E383, and separately
measure PPU dot/scanline timing. Do not infer a calibrated scanline or
authentic car physics or scroll from this CHR A/B result.


## Stage 158 — CHR register #0 positive visual counterfactual

Following the negative CHR register #1 result, two **additional actual
original FCEUX 2.6.5** replay experiments were completed at original FM2
frames **600** and **800**. The private diagnostic temporarily substituted
X=02 instead of X=00 for the single CPU instruction **$E380 / STX $8001**,
the write to MMC3 CHR register #0. The CPU X register was restored to its
original X=00 value at the following **$E383 / INX** before the original
program continued. Source ROM and read-only FM2 were not modified; each
capture reached N+2 with zero callback gaps and exactly one original CPU
writer/restore callback.

The same previously verified, unmodified original FCEUX control frames
were used as for the CHR register #1 comparisons.

| Original FM2 intervention | Captured frames differing | RGB changed pixels | NES palette changed pixels |
|---:|---|---:|---:|
| 600 | **601 only** | **3,042** | **3,042** |
| 800 | **801 only** | **3,039** | **3,039** |

The pre-intervention N−1, target N and later N+2 frames are **byte-identical**
across baseline/probe for both cases. Exact changed RGB pixel masks are
identical to their changed NES indexed-palette masks. Both experiments
affected exactly the same 35 scanlines of the *captured framebuffer*:

    Y=196–207, 209–223, 228–231, 236–239

This contrasts sharply with register #1, whose tested write substitution
affected **zero pixels** in the same frame ranges. We have therefore
independent experimental evidence that **CHR register #0 controls graphic
content visible in the lower portion of these two Stage 1-1 frames**,
while the register #1 substitution tested here does not. This is only
a counterfactual observation for these values/scenes, not proof that
register #1 is unused or that the original visible pixels directly
came from a single CHR mapping.

### Authentic private observation vs public capture format

These two real Stage-158 CHR0 sessions used an older, separately verified
local script: it **asserted** restoration of X at original CPU PC $E383,
but its completion metadata mistakenly labelled that successful
restoration as an accumulator-A restoration at $E38A. That is an
**old witness field-naming error**, not a direct independent X-register
attestation. The private numerical report explicitly discloses it;
these legacy metadata are not rewritten or passed off as newer
public-tool outputs.

The subsequently committed standardized private Lua harness
tools/capture_private_chr0_bank_ab.lua correctly emits a strict witness
field named **cpu_x_restored_before_e383** and a separate
**private_chr_bank0_one_write_ab_v1** schema.
tools/audit_private_chr_bank_ab.py accepts CHR register 0 or 1 only when
matching original/probe captures contain the respective new witness
schema. To audit CHR0 standardized captures privately, pass
**--chr-register 0** (CHR1 defaults to 1). It compares private ROM
identities, frames N−1 through N+2, P6 and palette sizes and restoration,
while emitting only numeric row/pixel aggregates.

Synthetic CI now includes 10 CHR1 Python tests, 5 CHR0 Python tests and
separate FCEUX Lua mock regressions for the two original CPU writer PCs.
No genuine ROM, FM2 or original screenshots entered GitHub.

### What remains unknown

The **row sets are observed output locations, not CPU execution
scanlines**. Neither original FCEUX callback phase nor these image
differences independently calibrates PPU dot/scanline origin. The effect
of CHR register #0 on the entire original stage, HUD/road tile semantics,
original camera speed and collision/physics remain unproven.
