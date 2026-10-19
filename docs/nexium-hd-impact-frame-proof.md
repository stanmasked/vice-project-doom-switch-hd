# Proving that HD impact light appears in the real NeXium guest

## What this test adds beyond source-side hit lighting

The parent PR #41 introduces optional hand-authored amber/cyan/red lighting
when source-side hit-flash ticks are positive. Ordinary native renderer
tests verify pure pixel safety and golden-frame identity. Those results
alone cannot show that the actual graphical Nintendo Switch NRO receives
the intended effect during a physically controlled fight in NeXium.

This extension gathers a **native differential screenshot measurement**
from the *same game frame*:

1. In the fourth live manually controlled encounter, a real player Y/Fire
   projectile strikes a newly restarted guard and causes guard HP 3→2.
   Existing source guest records link the physical keypress and collision
   to a real captured X11 image.
2. On that precise frame, after a single ordinary game tick and animation
   update, the guest runs the same pixel renderer with the optional impact
   light disabled. It samples **25 RGBA8888 pixels** around the guard.
3. Without another game tick, it renders the identical scene with the
   source-driven impact light enabled. It samples those same 25 pixels
   and submits this lit frame to the real NeXium display.
4. The NRO writes a source-owned SD witness only when there is a genuine
   flash tick, guard HP=2, exactly one projectile hit and one shot,
   no melee attack, and at least three changed pixel samples with
   different deterministic hashes.
5. A fail-closed Python CI audit requires that exact witness, checks its
   frame is within the actual guard hit's 12-frame feedback window,
   and additionally requires the earlier real-pad Fire/Impact X11 PASS
   and genuine screenshot evidence.

The double-draw happens **once** per full manual scenario. Normal game
frames are rendered once. No original NES assets, physics changes,
new controller buttons, screen stretching or gameplay shortcuts are
introduced. The optional glow remains disabled in the default render
and the attract-mode golden frames.

## Regression coverage

A standalone C++ test rejects invalid or absent source damage, unchanged
or insufficiently changed pixels, and verifies all 25 sample positions.
Python negative fixtures reject wrong damage/HP, impossible flash ticks,
forged frame identity/source, equal hashes, duplicate records and missing
live physical input or X11 evidence.

## Scope

A successful result proves authored visual feedback is applied by the
graphical homebrew NRO at a real manually caused hit in NeXium. It is
**not** a parity demonstration for original `Vice: Project Doom`, a
physical Switch performance benchmark, or restoration of commercial art.
