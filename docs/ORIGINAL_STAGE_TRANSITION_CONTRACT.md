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
