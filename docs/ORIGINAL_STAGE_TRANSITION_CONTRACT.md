# Original Stage 1-1 → Stage 2-1 timing reference

This is a source-only reference derived from **private** playback of the owner's
USA FM2 in FCEUX 2.6.5. It is not a claim that the Switch remake implements
the original gameplay, input, collision, or graphics.

## Confirmed original display timeline

| Original zero-based FM2 frame | Visible observation |
|---:|---|
| 3606 | Final nonblack car/driving screen |
| 3607 | First completely black screen |
| 3607–3647 | 41 consecutive all-black frames |
| 3648 | First visible city/platform screen |

The 59-frame private capture (3596–3654) has one screenshot for each recorded
frame. Seven frames present in an independent 8-frame-cadence run (3600, 3608,
3616, 3624, 3632, 3640, 3648) have byte-identical RGB **and** indexed palette
data. This is evidence of repeatable rendering of this *interval only*.
Neither focused run constitutes a full 43,652-frame terminal witness.

The opt-in, **ROM-free** implementation in
game_core/stage_transition.hpp models the three scene presentations.
Its requestExit() should be called **after** the final driving presentation.
The next present() returns Black exactly 41 times; the following
presentation returns Platform. The standalone C++ test proves the reference
frame indexing, no duplicate transition, deterministic replay and reset.
This module is not yet connected to the Switch NRO's actual renderer or
gameplay stage machine.

## Private Stage 1-1 roadway geometry observation (early segment)

A separate FCEUX run recorded 41 complete 256×240 screenshots, inclusive
frames 600–920 at 8-frame cadence. The local capture reports zero callback
gaps through its chosen endpoint. **Source pixels are not committed.**

For a cautious visual-road estimate, a private analyzer selected the known
neutral roadway fill color in the local RGB frames. At scanlines Y=120, 140,
160, 180 it measured the leftmost/rightmost visible fill pixels and took
medians over at least three usable scanlines. Full-screen flashes and
ambiguous rows are rejected. These numbers are **observed image cross
sections**, not collision widths, camera X/Y, extracted map coordinates,
scroll registers, or game engine parameters.

| Frame | Approx. observed left/right (pixels) | Width | Center X |
|---:|---:|---:|---:|
| 600 | 66 / 188 | 123 | 127.0 |
| 744 | 66 / 188 | 123 | 127.0 |
| 760 | 82 / 173 | 92 | 127.5 |
| 784 | 98 / 156 | 59 | 127.0 |
| 800 | 100 / 155 | 56 | 127.5 |
| 840 | 84 / 171 | 88 | 127.5 |
| 920 | 116 / 203 | 88 | 159.5 |

Thirty-seven of 41 sampled frames yielded usable cross-sections; four were
rejected as ambiguous. The visible roadway narrows, widens and shifts
laterally within this early segment. A single constant-width static road or
a constant scalar background-translation assumption is therefore **not
validated** by these images. Sprite occlusion, transitions and palette
effects can affect color-mask measurements. Do not infer camera velocity or
parallax until independent source-level scroll/PPU observations corroborate it.

## Required next work

1. Correlate private roadway RGB measurements with actual frame-tagged
   PPU scroll/MMC3 and RAM evidence before deriving camera/scroll parameters.
2. Build a separately selectable original-style HD driving-stage mode with
   placeholder geometry, then compare its observable transitions against
   the reference without embedding original graphics.
3. Integrate the verified 41-frame transition after gameplay stage-exit
   conditions are implemented, with Debug/Release native tests and NeXium
   rendering/input checks.
4. Preserve existing ROM-free autoplay fingerprints and never upload
   original ROM, FM2, RGB, PAL, CHR, PPU snapshots or commercial graphics.

**Proven today:** local source-only transition C++ test, private screenshots
and numerical timing/roadway observations. **Not yet proven:** original car
physics, camera/scroll speed, collision and Switch runtime integration.


## Stage 152 — observed original PPU write timing

A **new private** original ROM+FM2 run on FCEUX 2.6.5 captured CPU register
events for every frame 600–920 inclusive, plus 41 RAM snapshots at 8-frame
cadence. Playback callbacks were contiguous from frame 1 through frame 920.
The original ROM, FM2 and unabridged TSV traces remain local and private.

### Direct observations (not guesses about rendered scroll)

- 321 frames observed; **1,284 writes to $2005**, exactly four writes per
  observed frame.
- In all 321 frames, the captured write-value order was
  **0x00, changing value, 0x00, 0x00**.
- The first two $2005 writes were **seven measured CPU cycles apart** in
  all 321 frames.
- FCEUX reported a usable CPU cycle counter. The trace also contains $2000,
  $2006, $2007, MMC3 register events, and 41 postframe RAM samples of
  zero-page $0B, $0C and $0D.
- The running FCEUX Lua API **did not provide memory.registerread**. No actual
  $2002/PPUSTATUS read callbacks were observed. Do not reconstruct a known
  first/second PPUSCROLL latch from these write records alone.

A few aligned private image-and-register observations illustrate why source
values must not be confused with the effective display or camera position:

| Frame | Second raw $2005 value (decimal) | End-of-frame RAM $0D | Observed road width, pixels |
|---:|---:|---:|---:|
| 600 | 79 | 79 | 123 |
| 744 | 136 | 134 | 123 |
| 800 | 144 | 139 | 56 |
| 920 | 24 | 19 | 88 |

The difference between the sampled RAM $0D and an earlier $2005 write
demonstrates that an end-of-frame memory sample cannot simply be substituted
for the value used at an earlier CPU write. These are real values **observed
together**, not a derived camera speed or proof that visible road width is
caused by a single scroll register.

Added source-only `tools/audit_private_stage1_ppu_timing.py` and nine wholly
synthetic tests. The analyzer checks the raw event sequence, CPU-cycle order,
postframe samples, and optional private road measurement JSON, while keeping
`display_effective_scroll_proven=false`, `camera_speed_proven=false`.
No raw TSV, ROM, FM2, RGB, PAL or derived commercial graphics are in GitHub.

### Emulator Lua API compatibility

The public `tools/capture_fceux_ppu.lua` now checks for the actual presence
of `memory.registerread` rather than assuming it exists. Metadata declares
`ppu_status_read_hook=available` or `unavailable`. When missing, the capture
still collects supported write evidence but must **not invent PPUSTATUS read
markers or assert that the scroll latch is synchronized**. A fully invented
Lua negative test and CI workflow invocation cover that situation.

## Stage 153 — executed original scroll emitter, proven in real FCEUX

A third and fourth **private genuine FCEUX 2.6.5** run of the same
owner-provided USA ROM+FM2 established CPU execution provenance for the
previously source-audited fixed-bank routine at **$E8DE**. Both replayed
contiguously from the movie start through the requested frame **920**,
with **zero callback gaps**. All source ROM/FM2, CPU-cycle traces and rendered
game pixels remain private.

The first run observed exactly **321 execution callbacks at $E8DE**, one per
frame 600–920 inclusive. An independent comparison with the already captured
CPU video-write trace found **321/321 exact matches** between RAM $0B/$0D
at execution and the first two subsequent $2005 write values.

A second FCEUX session registered separate CPU execution callbacks at
five known original instructions. It recorded **1,605 execution events**
(5 per frame, 321 frames), with the following **identical CPU-cycle offsets
on every checked frame**:

| Fixed-bank CPU instruction address | Prior verified opcode | Cycles after $E8DE |
|---|---|---:|
| $E8DE | LDA $0C | 0 |
| $E8E4 | STA $2000 | +9 |
| $E8E7 | LDA $2002 | +13 |
| $E8EC | STA $2005 | +20 |
| $E8F1 | STA $2005 | +27 |

The actual register-write callbacks independently agree: $2000 occurs at +9,
while $2005 writes occur at +20 and +27 with **precisely the values of
RAM $0B and $0D captured at $E8DE**. This proves that the original
scroll-emitter instruction path actually executes during Stage 1-1, and
provides direct callback evidence that the **$E8E7 instruction (LDA $2002)**
executes as part of it.

The FCEUX Lua build still lacks a direct memory.registerread API for
$2002, so the claim is **executed read instruction, not directly
instrumented bus-read callback**. The separate static ROM anchor audit
identifies that executed opcode as LDA $2002. PPUSTATUS read semantics
reset the PPU scroll write latch, but this observation still does **not**
prove what scroll remains effective on visible raster lines: later
per-frame $2005/$2006 writes, mapper IRQ/raster splits, CHR changes and
screen composition need independent analysis.

A fifth independent private FCEUX run registered all **16** fixed-bank
literal $2005 store-instruction candidates from the source audit. It collected
**1,284 executed writer PCs**, each matched at the exact CPU-cycle timestamp
of one of the **1,284 previously recorded real $2005 writes**. Every original
frame 600–920 used the exact same four-instruction order:

| $2005 write order | Executed CPU address | Observed value |
|---|---|---|
| 1 | $E8EC | 00 |
| 2 | $E8F1 | RAM $0D at emitter entry |
| 3 | $E369 | 00 |
| 4 | $E36C | 00 |

The two late zero writes are therefore traced to specific original CPU
instructions, rather than assigned to a guessed NMI/IRQ or screen region.
**All 321 frames and all four individual write cycles matched exactly
(0 mismatches).** Determining whether the late writers belong to a
particular visible raster interval remains the next separate task.

The reusable, **source-only** private research tooling now includes
tools/capture_private_e8de_instructions.lua and
tools/audit_private_e8de_exec.py with synthetic positive/negative tests.
The audit distinguishes executed PC provenance from register writes
and explicitly reports display-effective scroll and camera speed as
**unverified**. Neither original traces nor game assets belong in GitHub.

### Remaining Stage 1-1 blockers

1. Measure later $2005/$2006 writers and their effective raster timing,
   including MMC3 IRQ/raster state.
2. Correlate source-backed video scroll with actual roadway image motion;
   do **not** equate the $2005 Y source with camera velocity.
3. Restore authentic car physics, collisions, opponent patterns and level
   geometry using separately verified original-game references.
4. Keep the 41-frame transition model opt-in until Switch renderer and
   actual driving-stage exit integration have been independently proven.



## Stage 154 — independent FCEUX frame-clock anchors

A separate actual original USA ROM+FM2 playback in FCEUX 2.6.5 captured
**336 consecutive after-frame CPU clock anchors, frames 590–925**, with zero
callback gaps. The ROM hash and read-only playback were rechecked privately.
This trace is independent from the already confirmed original CPU writer-PC
capture for frames 600–920. All raw traces and game assets stay private.

Cross-session comparison on frames 600–920 establishes *frame-relative CPU
timing*, without claiming an exact PPU scanline:

| Observed original timing | Result |
|---|---:|
| FCEUX frame-to-frame period, mean | 29,780.49 CPU cycles |
| Previous-frame callback → first $2005 ($E8EC) | 793–2,212 CPU cycles |
| Previous-frame callback → late $2005 ($E369) | 24,283–24,291 CPU cycles |
| Late writer phase spread across 321 frames | 8 CPU cycles |
| Late $E369 → $E36C | Exactly 4 CPU cycles |
| Late $E369 → current after-frame callback | 5,489–5,500 CPU cycles |

This shows a large difference between the *variable* earlier writer
position and the highly *stable* late writer phase (the latter differs by
only eight CPU cycles). That supports a **frame-synchronized CPU operation**;
it does not, by itself, establish an NMI, an MMC3 IRQ or a sprite-zero split.
FCEUX's emu.registerafter clock is not a calibrated PPU dot/scanline
origin. Do **not** turn ~24,286 CPU cycles into an asserted display line or
treat an observed $2005 write as the camera's world coordinate.

The private-only, ROM-free source tools
tools/capture_private_fceux_frame_anchors.lua and
tools/audit_private_stage1_frame_phase.py reproduce these checks.
Public test fixtures are entirely synthetic; they exercise continuity,
monotone CPU clock, all-four writer origin, cross-run epoch consistency,
stability bounds and negative cases without including original traces.

### Additional late-writer register sequence observed

The private CPU register-event log independently shows that after
the fourth $2005 writer at $E36C (value 00), the following CPU writes
occur with the **same relative timing on all 321 Stage 1-1 frames**:

| After executed $E36C | CPU register | Value |
|---:|---|---:|
| +0 cycles | $2005 | 00 |
| +8 cycles | $2006 | 0F |
| +12 cycles | $2006 | 00 |

No CPU writes to mapper IRQ-control registers $C000, $C001, $E000 or
$E001 were captured in frames 600–920 (**0 observed in this window**).
This does not rule out IRQ state configured before frame 600,
an interrupt already enabled earlier, or unrelated interrupt behavior.
The fixed phase of the late writes remains established; their
effect on visible PPU scanlines is **not**.

### Still unproven

1. The exact visible scanline/dot where late $E369/$E36C writes take effect.
2. Whether this late operation is driven by NMI, MMC3 IRQ, polling or another
   mechanism; tracing callback PCs and CPU timing does not prove IRQ origin.
3. Which road/background pixels depend on each PPU scroll state.
4. World camera velocity, physics, collisions, and actual HD Switch
   reproduction of Stage 1-1.


## Stage 155 — late PPU/CHR routine verified with original CPU register state

A **new independent private FCEUX 2.6.5 run** replayed the owner's matching
USA ROM+FM2 from movie start, validating the callback timeline through frame
920 (0 gaps, read-only movie, matching ROM hash). It recorded the executing
CPU instruction PC, CPU cycle, A/X/Y/P registers, and writes to
$2000/$2001/$2005/$2006/$8000/$8001 on original Stage 1-1 frames 600–920.
No source media or full logs are included in the public repository.

The 16-instruction late routine from $E367 was observed **in exactly the
same order and at the same relative CPU-cycle offsets on all 321 frames**.
The following nine CPU write instructions match their corresponding memory
register writes **at the exact same CPU cycle**, with 2,889/2,889 matches
and zero disagreements:

| Instruction PC | Relative cycles from $E367 | Source instruction | Verified port/value |
|---|---:|---|---|
| $E369 | +4 | STX $2005 (X=00) | $2005=00 |
| $E36C | +8 | STX $2005 (X=00) | $2005=00 |
| $E373 | +16 | STA $2006 (A=0F) | $2006=0F |
| $E376 | +20 | STX $2006 (X=00) | $2006=00 |
| $E37D | +28 | STX $8000 (X=00) | MMC3 $8000=00 |
| $E380 | +32 | STX $8001 (X=00) | MMC3 $8001=00 |
| $E384 | +38 | STX $8000 (X=01) | MMC3 $8000=01 |
| $E387 | +42 | STA $8001 (A=02) | MMC3 $8001=02 |
| $E38E | +51 | STA $2001 (A=0E) | PPUMASK=0E |

The full 16-PC timing chain therefore provides **5,136/5,136 exact
instruction offsets**. The instructions between those writes include
LDX #00 at $E367, LDA #0F at $E36F, LDX #00 at $E371,
LDA #02 at $E379, LDX #00 at $E37B, INX at $E383,
and LDA $01 / AND #EF before the final $E38E write.

At that observed register write, PPUMASK 0E has its **background rendering
enable bit set** and **sprite rendering enable bit unset**. This is a CPU
register-state observation, **not** evidence that sprites were absent across
the whole rendered frame. The MMC3 $8000/$8001 sequence selects CHR bank
registers 0 and 1 with values 0 and 2, respectively, at that moment;
other mapper writes later can change the banks.

### Public reproducibility and restrictions

- Source-only private capture: tools/capture_private_late_ppu_routine.lua
- Fail-closed auditor: tools/audit_private_late_ppu_routine.py
- Synthetic regressions: tests/test_audit_private_late_ppu_routine.py and
  tests/test_private_late_ppu_routine.lua
- Private captures require read-only FM2, matching ROM identity and contiguous
  callback frames. The auditor checks the complete callback transcript
  against its completion witness; output contains only aggregate
  source-free numbers.
- No original ROM, FM2, screenshots, CPU transcript, or extracted copyrighted
  game art should be checked into public GitHub.

**Still unproven:** the raster scanline/dot when PPUMASK and CHR
register state takes effect, its intended HUD/road/camera role, authentic
driving physics or collision geometry, and Switch gameplay integration.
Although these are frame-synchronized CPU writes, they alone do **not**
establish which pixels were rendered under which PPU state.
