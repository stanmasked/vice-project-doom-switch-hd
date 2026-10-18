# Switch startup autoplay — ROM-free smoke-test mode

This feature adds a **new, self-authored input-demo mode** to both
Nintendo Switch homebrew prototypes. It does **not** contain or execute
the original Vice: Project Doom ROM or game resources.

## Behavior

On launch, the 200-tick demonstration begins immediately, even without
gamepad input. It uses the exact same schedule as the host replay CLI and
host game-to-raster regression, taken from the *single*
`game_core/combat_demo.hpp` implementation. Expected events include:

| Demo tick (zero-based) | Synthetic input |
| --- | --- |
| 0–109 | Hold Fire (Y) |
| 110–114 | Idle |
| 115–144 | Hold Right |
| 145–149 | Left + Jump |
| 150–174 | Hold Left |
| 175–199 | Idle |

At the end of 200 ticks, the game resets the synthetic arena and
replays tick zero. This also resets graphical animation playback to
prevent old animation state from leaking across loops. The graphical
scene labels the state **REPLAY DEMO**.

To switch to **manual gameplay** on Switch, click the left analog stick.
This resets the scene, clears all projectiles and restores the
three-health training dummy. In manual mode use D-pad/left stick to
move, A/B to jump, Y to fire, Plus to exit. Click the left analog stick
again to restart the demo from tick zero.

The graphical test-scene developer reset `Y + left-stick click`
remains separate from the single-click replay toggle.

## Reproducibility

`romfree_combat_autoplay_demo` is a host CTest which executes 400
ticks (two full loops). It requires both loop endings to reproduce
the original pinned synthetic 200-frame FNV64
`5947277116621119566`, 11 projectiles fired and three training
hits, verifies no stale state after the reset, then switches into
manual play and back to demo. It checks input-script edge transitions.

`tests/test_romfree_autoplay_shared.py` verifies that the host replay
and host raster regression and both Switch source frontends refer
to the **same header** and that the two NRO Makefiles depend on it.

Successful **host simulation** does not demonstrate actual libnx or
emulator frame timing. The NRO must still be cross-compiled in Actions
and run in a compatible legal homebrew environment. A usable
emulator/console was unavailable in the development container at
this stage. No firmware, game image or keys are distributed.
