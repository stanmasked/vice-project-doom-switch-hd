# Fourth attempt: first guard really defeated after three source hits

After PR #37's independent proof of renewed manual shooting and the
first swept collision on a freshly restarted fourth playable attempt,
this change verifies a genuine **complete first-guard fight**.

## Real X11/guest scenario

- The host presses NeXium's **Z / Nintendo Switch Y (Fire)** after
  guest-sourced event #2 confirms the first projectile impact HP=3→2.
- The *same visible* libnx NRO runs ordinary simulation updates and
  further projectile collisions, without a guest-only scripted bypass.
- A fresh native source witness may be emitted only upon the third
  swept hit, with previous guard HP=1 and hits=2, resulting in
  guard HP=0 and hits=3.
- The hero must still have all 5 HP, with no guard melee attacks,
  unchanged sentry HP=2, no second-wave activation and no dash.
- The host releases Fire as soon as the third-hit event is observed
  and saves a real 1280×720 X11 screenshot after the kill.
- A separate fail-closed Python audit links this journal to the
  prior fourth-run first Fire/impact source and its X11 PASS, confirms
  host key evidence and measures a significant change in the guard
  region between first-impact and guard-clear frames.

The portable C++ regression now plays the entire win → Minus →
melee death → Minus → win → Minus → move → Fire → 3 guard hits
cycle with the actual deterministic core. It rejects forged prior
HP and missing Fire. Python fixtures reject forged event origin, shot
count, timestamp, hit counters and X11-hostless results.

This covers only our independently authored ROM-free gameplay
prototype. It does **not** recover Nintendo Entertainment System
logic or copyrighted Vice: Project Doom assets and does not
demonstrate physical Switch hardware behavior.
