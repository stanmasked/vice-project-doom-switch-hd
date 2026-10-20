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
the HD ON pre-hit X11 image. The actual NeXium X11 viewport transforms
the authored fifth HUD segment: its observed bright rect occupies
approximately x=814..824, y=17..28 rather than authored x=821..831.
Require at least 80 pixels of exact `healthy teal -> empty grey`
transitions within x=805..835, y=15..31. Also require at least 440
pixels in the four preceding health bars to remain filled (teal or
legitimate yellow damage flash). This explicitly rejects HUD flashes
and a second missing heart as evidence of exactly one HP loss.

**Failure-driven verification:** NeXium run #39450682479 supplied the
real guest source collision record at frame 394 (HP 5 -> 4,
`shots_hit` 0 -> 1). Its archived P6 images show exactly
132 teal-to-empty fifth-bar pixels and 504 retained pixels across
the first four bars. The old x=821..831 scan detected only
44 changes and had an incorrect minimum of 60. The revised
color-specific ROI was measured from the authentic archived frames;
this is a visual-audit correction, NOT a gameplay or renderer change.

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
