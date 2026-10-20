# Stage 92 — native NeXium X11 proof of real guard melee cooldown pips

The preceding Ready PR #65 adds optional ROM-free HD guard awareness and melee cooldown cues. Its shared renderer/Simulation host test proved the complete visual semantics: a genuine detected guard displays a ready `!`, the first legitimate melee hit at cooldown 32 replaces that with three dim pips, and the pips refill from the same existing source timer after idle simulation ticks.

This stage uses actual NeXium evidence to test **specifically the three dim pips after the real first contact and their disappearance after the same guard is defeated**. It does not create synthetic battle events or claim to prove the ready `!` state in native X11 yet.

## Existing real guest/X11 sequence

The successful NeXium run from parent PR #65, [runtime #39479877207](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39479877207), [evidence #12291287668](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39479877207/artifacts/12291287668), contains a source-owned guest `guard_live_witness.txt` pair:

- Alert frame **143**, genuine Right input, AI detection true, attack cooldown **0**, hero HP **5**.
- First actual melee strike frame **195**, cooldown **32**, hero HP **4**, same source-attested living guard.
- Later the pad-driven Y/Fire projectile path kills that guard; independently proven native X11 image `screen-live-defeat.png/.ppm` shows the enemy sprite gone.

The already-captured `screen-live-strike.png/.ppm` contains a physically rendered living guard with its two existing HP chips, authentic face/body colors, and a dark 3-pip cooldown bar directly above its sprite. Its genuine X11 RGB pixels are the authored dim color `(92,101,118)`, **68** in the confined threat meter region. After actual gunfire kills the guard, **0** such pixels remain in the corresponding source projected guard ROI.

## New fail-closed verifier

New `tools/audit_nexium_guard_cooldown_x11.py` imports the old strict guest event and native X11 APIs. It requires all three independent live contact, kill and guard-raster prior PASS reports; physically observed Right input and guest death; unique correctly ordered screenshots; genuine 1280x720 P6 raster and PNG companions. It **locates the real guard sprite** by simultaneous exact pixels of its surviving orange HP bars, authentic torso and face near the source-logged game/camera location, rejecting detached grayscale bars in the wrong area. It then demands all three exact-color dim pips on the real strike screenshot and no lingering dim pips near the guest-authenticated location after the kill. It rejects stale identical images and preserves their SHA256 fingerprints.

Nine adversarial tests reject unanchored/fake bars, wrong cooldown color, missing single pip, lingering post-death marker, forged source-camera anchor, identical/reused frames, truncated P6 and an improperly ready-to-attack glyph after real contact.

The NeXium workflow runs the new test suite and this strict auditor **as an additional gate following the pre-existing guard sprite/kill audit**. Native Core and deterministic gameplay should stay unmodified; Switch NRO and gameplay outputs are identical to the parent commit, as only diagnostics and CI metadata change.

**Limitations:** the earlier native host test still supplies the only proof of the guard's ready exclamation and progressive refill; this stage adds X11 proof of its first cooling state and disappearance upon guard death. The project is a clean-room synthetic ROM-free prototype. Commercial game fidelity and physical Nintendo Switch runtime remain unverified.
