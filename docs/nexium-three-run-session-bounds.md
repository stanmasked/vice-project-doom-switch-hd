# PR #35: bounded terminal input witness after three complete attempts

## Failure observed

NeXium Actions run `39294450405` built the guest NRO and completed real
native X11 captures through the third stage-clear, then its strict manual
input auditor rejected the **five-line** guest manual witness instead of
the seven ordered events required for native Plus and Exit.

The actual guest SD record retained original real input effects for
Enter (frame 0), Right (19), Fire (57), Jump (77) and Left (102). The
NeXium kernel log independently recorded a successful
`svcExitProcess` and runner completion. The missing two records were
not grounds to falsely mark the manual audit passed.

## Root cause

The main loop counts `manual_session_ticks` continuously across
manual gameplay, while each Minus restarts the *level-local*
`game.frame()`. The previous serializer rejected terminal Plus and
Exit when session ticks exceeded **1200**, which is appropriate for
the early two-attempt probe but too short for a win -> loss ->
third complete win scenario.

## Bounded correction

- The native serializer caps **terminal session time at 3600** ticks.
  It still checks `session_ticks >= game.frame()`, the explicit
  terminal event type, correct event sequence, and physical controller
  session; it does not forge terminal evidence or issue an automatic pass.
- The independent Python auditor keeps the old 1200-frame cap for
  the first five control events and allows up to 3600 only for
  Plus/Exit. It requires **identical Plus and Exit frame values**,
  because the guest does not advance gameplay between those two
  source-side records.
- Native C++ regression now rejects 3601, accepts a continuous
  1800-tick third-run terminal record and verifies serialized frames.
- Python mutation tests reject oversized terminal ticks,
  disagreements between Plus and Exit, and early gameplay events
  claiming a frame later than 1200.

## Success criteria

This fix is not complete until all GitHub Actions succeed **and** the
NeXium log shows all seven native input events followed by the source
third-stage `VPD_NEXIUM_THIRD_STAGE_PASS` and real guest process exit.

All graphics, physics and tests remain original ROM-free homebrew,
not recovered NES gameplay or verification on physical Switch hardware.
