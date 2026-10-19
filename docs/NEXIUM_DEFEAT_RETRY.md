# Native NeXium: retry after an actual guard-caused defeat

PR #28 successfully verified real keyboard N=Minus after *victory* in the
same running Switch NRO: two enemies were defeated with live Right+Fire,
the player reached the exit, pressed N, and the game source reset itself.

This stacked phase tests the **other terminal outcome**, without
substituting a generated replay for actual controller-driven gameplay.

## Same live NRO, multiple genuine encounters

After the previously verified victorious restart:

1. The host holds **D=Right**. The freshly reset first guard must make
   genuine melee contact (guard attack 1, hero HP falls from 5 to 4).
2. Right is released. The living guard must deliver four more actual
   attacks to reduce the hero's HP to 0 while the hero remains nearby.
3. The NeXium host captures the actual X11 **MISSION FAILED** screen.
4. Only then does the host press **N=Minus** again.
5. The guest's very same live Simulation must initialize the hero with
   5 HP, the first guard with 3 HP, the sentry with 2 HP, clear bullets
   and progression, and return to the original spawn. A separate real
   X11 screenshot is taken after this second restart.

The NRO's `live_defeat_retry_witness.txt` contains exactly three
source-derived, ordered events: `contact`, `death`, `restart`.
The new witness cannot claim death based on a keyboard event or on an
isolated native guest-script simulation. It is enabled only after the
previous victory retry was genuinely recorded in the same NRO process.

The strict auditor requires the older manual, live victory, native exit
and first Minus proofs, actual separate Right and Minus host injections,
all three canonical guest records with legal damage and reset fields,
and both new actual 1280×720 P6/PNG X11 captures. It rejects a replay
that has not visibly cleared the centered failure screen.

Portable C++ integration drives the identical source through a real
victory, first replay, first guard contact, five melee attacks, death,
and second replay. Python mutation tests reject fake/wrong-order/
inconsistent guest data, but **cannot themselves prove NeXium execution**.

No proprietary ROM/asset is committed; all enemies, map and scenes
remain a self-authored ROM-free homebrew experiment. Physical Nintendo
Switch performance and original NES accuracy are not inferred.
