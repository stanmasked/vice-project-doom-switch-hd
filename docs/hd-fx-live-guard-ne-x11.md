# Native HD L+R chords during an active fourth-guard encounter

This ROM-free experiment extends the separately proven NeXium post-clear
L+R V2 check. It does **not** replace or weaken the existing visual, replay,
fourth-stage or original-asset restrictions.

## Source event gate

The NRO first requires the authentic, pad-driven fourth attempt to
produce one swept projectile hit on the living guard. The result must be
guard health 2, guard projectile hits 1, player alive and stage uncleared.
Only new real libnx L+R press edges under these conditions may emit a
`VPD_HD_FX_COMBAT_V1` record, in the independent
`sdmc:/switch/vice_project_doom/hd_fx_combat_guest.txt` report.

Each accepted edge compares an alternate effect setting with the displayed
one **on the exact same native simulation frame**, using 414,000 HUD-free
scene pixels. It fingerprints the actual `Simulation` both before and
after drawing; the source hashes must be equal, and the scene hashes must
differ. Records include native frame, guard health/hits, player health,
effect mode and both source/raster hashes. Exactly two ordered OFF/ON
entries are accepted.

## Independent emulator evidence

The X11 harness stops firing immediately after the first real source hit,
injects Q+E twice, and captures an OFF and ON NeXium screen while the
wounded guard is still alive. It then resumes firing until the guard is
defeated, completes the same fourth-stage wave, and performs the established
POST-CLEAR L+R V2 witness separately.

The standalone `audit_nexium_hd_fx_combat.py` requires the proven fourth
hit, before-kill timestamps, both host Q+E events, two X11 screenshots and
an actual HUD pixel delta. Missing or malformed sources fail closed.
Synthetic parser tests exercise misordered edge data, false guard state,
missing X11 provenance and mismatched before/after fingerprints.

The existing `romfree_hd_fx_live_combat` host CTest verifies guard
projectile impacts and a real hostile turret bullet through independent
source-derived ON/OFF raster comparisons.

No original NES content is included, and neither NES behavior fidelity nor
physical Nintendo Switch hardware is established.
