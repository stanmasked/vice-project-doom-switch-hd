# Third manual attempt: authentic Fire and first swept guard hit

This stage stacks on PR #32's independent proof of movement after a real
victory retry, a genuine guard-caused defeat, and a second Minus restart.

## Test route

1. Use existing native Right to move the restored hero, and keep the
   previous source-witness / X11 actor image.
2. Only after the same visible libnx NRO logs that movement, inject
   **Z** via X11 (NeXium's Nintendo Switch Y/Fire mapping).
3. Read the native source witness for the exact **first projectile spawn**:
   shots fired 0->1, guard HP 3, one active bullet, hero HP 5.
4. Release Fire *as soon as that event is observed*. Allow the same
   source simulation to move the bullet until swept collision reduces
   the guard from HP 3->2 and increments real projectile hits to 1.
5. Capture a further actual 1280×720 X11 image after the source impact
   and compare the grounded guard's region to the earlier movement frame.

The strict Python auditor requires the previous third-run movement PASS,
the exact two guest SD records in order, host X11 Fire/impact observations,
at least one frame and fewer than 90 frames between shot and collision,
stable third-run player x/HP, the real projectile count, and X11 pixels.
Neither native C++ simulated replay nor Python fixtures may satisfy the
live NeXium proof on their own.

The synthetic map/hero, enemies and bullet are independently authored
ROM-free placeholders. This does not establish NES ROM compatibility,
faithful Vice: Project Doom mechanics, original graphical assets, or
performance on physical Nintendo Switch hardware.
