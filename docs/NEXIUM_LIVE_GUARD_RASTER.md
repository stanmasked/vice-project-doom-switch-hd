# Live guard battle: native NeXium X11 raster evidence

This research stage stacks on PR #21, where the self-authored ROM-free
Nintendo Switch NRO passed a **real manual** guard encounter:
Right to approach, first native guest-recorded melee hit, then real
Y/Fire projectiles until the guard died. PR #21's X11 screenshots were
taken during the original auto-demo, **before manual controls**, and
therefore did not prove that the guard was displayed or disappeared.

## Two native host raster observations

`tools/nexium_visual_probe.sh` now captures real host X11 pixels and
PNG screenshots at two distinct guest-authenticated milestones:

1. `screen-live-strike.{ppm,png}`: after the *live pad-controlled*
   `guard_live_witness.txt` reported first melee contact, while the
   guard was alive and the player was still in the visible encounter.
2. `screen-live-defeat.{ppm,png}`: after a later authentic
   `guard_live_defeat_witness.txt` event reports that Y/Fire projectiles
   reduced guard health to zero.

The same libnx NRO continues to produce guest records; the host only
uses their events to decide when to sample real NeXium X11 frames.
It does not generate screenshots through a Python renderer or insert
dummy evidence. A small settling delay lets the guest present the state.
The watchdog and original manual, dash, patrol, autonomous script and
live-defeat checks remain unchanged.

## Strict visual criterion

The new `tools/audit_nexium_guard_live_raster.py` checks:

- Exactly formatted 1280x720, 8-bit P6 pixels from both captures and
  valid PNG signatures, plus traceable screenshot capture events.
- Independent PASS results from the native live-contact, live-defeat,
  original host visual and kernel guest-exit auditors.
- A genuine native guest event ordering: melee precedes final defeat.
- Guard's on-screen horizontal region from the **actual guest world
  guard/player coordinates** and the production simulation's camera
  transform (ROM-free map units, fixed point 256).
- In the lower gameplay region, a substantial patch of the production
  renderer's alerted-guard torso tint `(220,103,93)` must be present
  in the **strike** raster and absent after the **defeat** event.
- The raw SHA-256 of each screenshot is included in the verdict.

Unit tests generate distinct synthetic PPM fixtures *only to test the
auditor itself*: they cannot substitute for actual NeXium run artifacts.
A successful CI is a narrowly scoped proof that the self-authored
guard silhouette visually disappeared from host X11 output in sync
with verified live guest death. It does not prove authentic NES
graphics, hardware video scanout, 60 FPS, or physical Switch support.

## Limitations

NeXium adds application chrome/overlays and may pillarbox the guest
frame; the guard ROI allows a bounded horizontal display margin.
This test deliberately excludes HUD/overlay regions so FPS counters
or constantly moving sky cannot falsely prove the disappearance.
The game remains a standalone homebrew gameplay prototype, not a
full remaster of Vice: Project Doom.
