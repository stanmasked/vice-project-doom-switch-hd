# NeXium native: manual Fire defeats the visible guard

This stage stacks on PR #20, where an actual pad-controlled `Simulation`
within the running Nintendo Switch homebrew NRO confirmed that the guard
noticed the player and delivered first contact damage. The previous
guest-only scripted combat proof (PR #19) is separate.

## Updated real-keyboard scenario

The NeXium X11 driver retains the original manual R+A, Right, Fire,
Jump, Left and ZR smoke checks. It then holds D/Right until the *actual
guest-written* `guard_live_witness.txt` contains the first contact
strike. Only then does it release Right (so the player does not walk
past the guard) and hold Z/Y (Fire) for 1.6 seconds, before pressing Plus.
The host can inspect the guest record to schedule its next keypress, but
**the host does not write or substitute any of the gameplay evidence**.

The visible, authoritative NRO `game.tick(Input{pad})` tracks:

1. **fire**: `Fire` is present in actual libnx input, the game core
   increases `shotsFired()`, and the guard is still alive and ahead
   of the player. The witness includes the observed guard HP, accounting
   for any earlier manual Fire hits.
2. **impact**: one of the existing swept projectiles physically changes
   the guard's hit counter and decreases HP by exactly one. This may
   occur on a later tick after the Fire input is released.
3. **defeat**: the last real projectile hit reduces guard HP to zero.
   The witness's event count depends on the HP observed at the start
   (1–3), rather than assuming the initial one-shot probe missed.

`game_core/guard_live_defeat_witness.hpp` serializes strictly
bounded guest events to `guard_live_defeat_witness.txt`, resetting
the file on NRO startup. The independent strict auditor validates
monotone frames, HP+hit conservation, chronological and cumulative
projectile counts, actual rightward gunfire, exactly as many impacts
as initially observed HP, a terminal enemy death, the host keypress
record, the prior live guest strike, and all independent previous
NeXium guest proofs.

This stage does not claim a reproduction of original NES enemy AI,
authentic Vice: Project Doom assets, physical Nintendo Switch
performance or user-driven console gameplay outside the tested
experimental NeXium setup. It proves only the custom ROM-free
homebrew simulation behavior when confirmed by the native CI.
