# ROM-free combat target — gameplay prototype

This is an original practice-dummy mechanic in the existing native
Nintendo Switch test scene, not reconstructed Vice: Project Doom enemy
behavior, hitboxes, weapons or damage balancing. It contains no
copyrighted ROM, game graphics or game code.

## Behavior

The independently authored stationary training target starts at
world X400, Y208, with 3 health. Its hitbox is a 16×16 axis-aligned
rectangle in original simulation pixels.

Shots move in one-pixel swept steps along X. World-solid collision is
checked before the target hit. The first projectile crossing a valid
target coordinate loses its active state and reduces target health by
exactly one, increments total hits, and can never inflict repeated
damage. At health zero the target becomes non-collidable and disappears
from the graphics prototype. Reset restores its original health and
hit tally.

The state is bound into the fixed-tick deterministic replay hash when
shooting has been exercised. Existing no-shoot golden fingerprints are
preserved for old scenarios.

## Switch prototypes

- Y fires (from the preceding feature PR).
- The graphical NRO shows an original colored rectangle with a simple
  three-mark health indicator; after three hits, it disappears.
- The text-mode NRO shows "T" on the map and remaining health/hits.

## Verification

Host-side C++ regressions check the original projectile path versus
an identical deterministic second replay, all three target hits,
absence of extra hits after target destruction, protection by an
intervening solid wall, and full reset to 3 health.

Pixel tests independently confirm target geometry changes the synthetic
RGBA raster, decreasing health changes the indicator, and health zero
restores the original target-free golden image.

Checks are performed by the same game-core, graphics-core and Switch
NRO CI workflows as the shooting prototype. Passing compilation alone
must **not** be described as emulator or physical Switch gameplay
execution. The source relies on completely new placeholder assets.
