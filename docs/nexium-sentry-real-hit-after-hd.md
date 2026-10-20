# Source-confirmed hostile hit after real NeXium HD OFF/ON

This stacked ROM-free guest test extends verified PR #57. That branch
already proved the actual AArch64 libnx NRO accepted two distinct
L+R shoulder edges while the **same first sentry bullet** flew during
the fourth, real-pad-controlled second wave.

## New proof boundary

The X11 controller stops movement after the *native* hostile-halo event,
injects two real Q+E chords (L+R), captures HD OFF/ON images, and
**remains idle** while the first bullet continues its original path.
It does not fake input to damage the hero, write to HP, move bullets,
or modify the source collision rules.

The NRO records a fresh
`sdmc:/switch/vice_project_doom/hd_fx_sentry_hit_guest.txt` event
only when a real `Simulation::tick(Input{})` satisfies all conditions:

- The sentry projectile still occupies the same slot and is sourced
  from the previously recorded **HD ON** event.
- Its age and fixed-point position follow exact `-768` motion from
  that event, and the pre-tick projectile is active, then consumed.
- The swept projectile enters the genuine player collision rectangle.
- Native hero HP falls by **exactly one**, while the source-owned
  sentry `shots_hit` increases by exactly one.
- The same guard is dead, second wave remains active, sentry still
  lives, HD is ON and the stage has not cleared.
- The previously captured simulation fingerprint **differs** after
  the real physics tick. (In contrast to render-only L+R, real damage
  must change authoritative simulation state.)

The strict auditor compares this record to the independently verified
guest L+R events and fourth-stage chronology, requires one native
X11 image taken after the source collision, and compares it with
the HD ON pre-hit X11 image. The rendered **fifth health segment**
(x=821..831, y=18..29) must lose at least 60 changed RGB pixels.

`tests/test_nexium_hd_fx_sentry_hit.py` rejects fabricated host-only
damage, duplicate records, expired/replaced bullets, wrong age or
motion, wrong player hitboxes, multiple HP losses, counter mismatch
and identical before/after simulation snapshots.

The previously accepted scene tests, NeXium guard/sentry flow, X11
HD OFF/ON images, fourth-stage victory, and post-clear toggle remain
mandatory; this new check does not replace earlier independent proofs.

**Acceptance:** the exact GitHub PR head must pass Native Core,
graphics/NRO, deterministic Debug+Release, and real NeXium
`VPD_NEXIUM_HD_FX_SENTRY_HIT_PASS`, including the unchanged earlier
`VPD_NEXIUM_HD_FX_SENTRY_PASS`. No claim about original NES fidelity
or physical Nintendo Switch execution.
