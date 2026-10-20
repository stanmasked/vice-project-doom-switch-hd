# NeXium X11 remaining-heart spatial audit hardening

This stacked, ROM-free regression improvement builds on [PR #58](https://github.com/stanmasked/vice-project-doom-switch-hd/pull/58). The preceding real NeXium run at commit `043fcf7f` confirmed the first source-owned sentry bullet hit after L+R OFF/ON (HP 5 -> 4; authentic X11 fifth segment teal -> gray, 132 pixels), plus four prior hearts present despite their legitimate yellow damage flash.

## Identified remaining false-positive risk

A **single total** of >=440 preserved teal-to-teal/yellow pixels across the first four HUD cells was not enough to guarantee each individual heart survived. For example, with the real 504-pixel starting evidence, a one-pixel disappearance in the second heart still gives 503 aggregate pixels, which the original sum would accept.

## New independent acceptance criteria

- The original guest witness, moving projectile age/coordinates, swept hit, HP 5 -> 4, sentry hit counter and chronology requirements remain unchanged.
- The fifth cell is sampled only at its actual native X11 horizontal interval **814..824**, with >=80 teal-to-empty pixels. It does not overlap the fourth cell.
- Each remaining cell is audited individually at native X11 x-intervals **757..766**, **771..781**, **786..795**, **800..810**, and y=15..31. Each must preserve >=105 teal-to-teal/yellow pixels and must have **zero** teal-to-empty pixel transitions; the previous >=440 aggregate requirement also remains.
- The real #58 image yielded 120/132/120/132 preserved pixels in those four cells. A single darkened second-heart pixel must now fail.
- Synthetic adversarial unit tests prove the specific old false positive is rejected, and an unflashed but still healthy four-heart HUD is accepted.

The work changes only the Python visual auditor, its unit tests, and documentation; no native collision rules, HD renderer, commercial ROM, or emulator settings are modified.

## Evidence boundary

Until exact-head CI re-runs the NeXium NRO and captures its **real** 1280x720 X11 display, this stage is a proposed hardening. Passing synthetic tests alone does not establish runtime acceptance. No claim about original NES fidelity or physical Switch hardware is made.
