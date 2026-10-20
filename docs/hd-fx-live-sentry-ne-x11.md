# Real NeXium L+R with an active second-wave bullet — ROM-free prototype

This independent guest stage is stacked on verified PR #56. The parent
host CTest confirmed that only the authored projectile halo changes
scene pixels while simulation, hostile-shot collision and player health
remain deterministic. This stage tests real guest `libnx` shoulder edges,
not an isolated native scene fixture.

## Source-owned runtime witness

On the fourth real pad-driven playthrough, after the first guard has
died and the second wave has genuinely begun, NeXium waits for the
**existing native hostile-halo witness** from a real active sentry bullet.
It stops the player's movement and sends two Q+E shoulder chords
(NeXium mappings for L+R), taking X11 images after OFF and ON.

The live Nintendo Switch NRO appends `VPD_HD_FX_SENTRY_V1` records
to `sdmc:/switch/vice_project_doom/hd_fx_sentry_guest.txt` only if:

- a genuine shoulder chord made the graphics preference change;
- the source game has an alive hero, dead guard, living sentry,
  active second-wave encounter, and no stage clear;
- a hostile projectile is active after the real gameplay tick;
- both framebuffer passes independently cover 414,000 non-HUD pixels,
  differ in appearance and leave `Simulation::fingerprint()` untouched.

The record includes projectile slot, position, age, velocity,
turret shots fired, frame number, HD mode and before/after
fingerprints. The strict auditor requires both records to follow the
**same bullet** with the exact fixed-point `-768` horizontal
velocity and monotonically increasing age. The first bullet must
be the one previously sampled by the successful hostile-halo witness.

The X11 off/on screenshots, physical host input records, prior source
halo, a successful fourth-stage exit, and prior guard defeat must all
exist. The original after-stage V2 HD toggle and all earlier guest
audits remain mandatory.

## Acceptance and limits

- `python3 tests/test_nexium_hd_fx_sentry.py` rejects reordered
  modes, injected host-only entries, replayed events, bullet
  teleportation, changed shot identity and altered gameplay hashes.
- `python3 tools/audit_nexium_hd_fx_sentry.py --evidence ...`
  must emit `VPD_NEXIUM_HD_FX_SENTRY_PASS` after actual emulation.
- A successful cross-build or host CTest alone cannot establish the
  guest L+R event; keep the PR in Draft until exact-head NeXium and
  all existing native workflows pass.

This is **not** a ROM decompilation, a measured reproduction of
Vice: Project Doom (NES), or verification on a physical Nintendo Switch.
