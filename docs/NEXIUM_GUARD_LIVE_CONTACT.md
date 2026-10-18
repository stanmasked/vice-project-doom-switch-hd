# NeXium: live manual guard detection and first melee hit

This follow-up stacks on PR #19, which independently proved guard detection,
melee attack and projectile destruction using an offscreen scripted instance
of the production C++ `Simulation` executed inside the Nintendo Switch NRO.

**New evidence is materially different.** The normal, visible manual
encounter receives input from the actual NeXium keyboard mapping through
libnx `padGetButtons()`, and only that authoritative `game.tick()` can
write `guard_live_witness.txt`.

After the existing R+A/right/fire/jump/left/ZR sequence, the X11 runner
holds the verified D (Right) input for 3.4 additional seconds.
The NRO independently captures two events:

- `alert`: the guard changes from unaware to alerted during live Right
  input while both actors are alive, hero HP is 5 and the guard has not
  previously attacked. The hero is within the source-code detection radius.
- `strike`: the **same visible gameplay state** loses one hero HP
  (5 to 4), increments the guard's attack counter from zero to one, and
  starts the real 32-tick contact-attack cooldown, while receiving Right.

The guest log records strictly bounded frames, the actual fixed-point
positions, HP, attack count and cooldown. Both records require a live
direction input and are rejected if a caller merely claims to have
sent a key but the gameplay simulation did not change.

`audit_nexium_guard_live.py` enforces two strictly ordered events,
valid source labels, canonical numeric formatting, game-world bounds,
detection/strike radii and the expected HP/cooldown transitions. It
requires independent success of original seven-event manual control,
ZR dash, guard patrol, separate scripted combat and kernel guest exit.
Mutation tests reject incomplete or forged inputs. A host C++ test
cross-checks the exact serializer against gameplay input and physics.

This stage is *not* a proof that the live player destroyed the guard
via keyboard-fired bullets; that is separate future work.
Nor does it demonstrate recovered original NES enemy behavior or
performance on real Nintendo Switch hardware. No copyrighted ROM or
proprietary art enters the public repository.
