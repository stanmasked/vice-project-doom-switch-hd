# Stage 94 — CPU-clock bracketing of PPU/MMC3 register callbacks

## What changed

Stage93 characterized **which ordered families of CPU-visible callbacks**
co-occurred with saved screen differences. Stage94 now classifies each
event's **CPU-cycle timestamp** relative to two consecutive verified
FCEUX `registerafter` *snapshot sample* clocks when these were captured.

Tool: `tools/audit_ppu_cpu_clock_bracketing.py`.

For each pair of consecutive saved snapshots the report shows mutually
exclusive **aggregate counts** of callbacks observed:
- exactly at the prior saved snapshot's sampled CPU clock;
- strictly between the two snapshot sample clocks;
- exactly at the later sampled clock;
- at an indistinguishable common clock when the two samples are equal;
- without a valid pair of sampled clock anchors.

The same groups are counted separately for MMC3 CHR-context, PPU scroll /
address, display control, PPU data, status reads, and other CPU events.
Raw CPU counters, MMC3 bank values, image data, and original ROM contents
are **not exported**. The algorithm preserves MMC3 selector continuity
across snapshot windows and cross-checks Stage93 callback-family totals.

**A sampled `registerafter` CPU clock is not an observed PPU scanline,
VBlank edge or physical frame boundary.** Even a callback with an equal
timestamp at a snapshot anchor does not prove when the NES PPU used its
state for actual pixels. Do not convert these clock brackets to scanline
indices or camera offsets. Equal snapshot clocks are a separate ambiguity
class rather than arbitrarily assigned to two endpoints.

## Run against private, integrity-verified captures

```bash
python3 tools/audit_ppu_cpu_clock_bracketing.py \
  private/ppu_capture_session.meta.txt \
  --require-cycle --require-clock-anchors --require-screen-pair \
  --out private/ppu_clock_brackets_stage94.json
```

The strict flags require a valid CPU cycle log, a recorded sample clock for
each saved snapshot, and at least one pair of verified FCEUX reference
screens. Omit them when investigating evidence gaps: absent clocks are
explicitly `unanchored`, and absent reference pairs are not synthesized.

All upstream Stage79/90/91/92/93 session, event-log checksum, screen and
snapshot integrity gates remain in force. No original ROM, PPU memory dump,
screen image or commercial game-derived JSON report belongs in public GitHub.

## Result and limitations

This is a testable **CPU-side timing evidence gate** that makes it easier to
identify event-heavy intervals worthy of true PPU raster instrumentation.
It does not prove which CHR bank, scroll state, background pixel or sprite
was actually used on a scanline; the HD renderer remains unchanged.

The next research requirement is independently measured physical PPU
raster state at scanline/VBlank boundaries, then pixel ownership
(background versus sprites), verified scrolling, and authenticated
first-level provenance before any HD layout is approved.

## ROM-free checks

```bash
python3 -m unittest discover -s tests -p 'test_ppu_cpu_clock_bracketing.py' -v
```

Synthetic tests cover missing samples, unknown/verified cycles,
strictly-between and equal-clock cases, identical sample clocks,
MMC3 selector continuity, same-cycle events, missing anchors,
tampering, and refusal to infer scanlines or camera displacement.
