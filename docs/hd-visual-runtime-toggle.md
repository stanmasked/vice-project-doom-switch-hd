# Nintendo Switch native HD effects runtime switch

This change makes the already validated, independently authored ROM-free
HD visuals compareable **without leaving manual gameplay**.

**Control:** hold **L + R** together in manual gameplay. Pressing the
second button toggles the state. The chord consumes both single-shoulder
backdrop commands while held. Releasing the buttons, then making a
new chord, toggles back. Normal individual L backdrop reload and R
backdrop reset remain available, and controls behave exactly as before
in the scripted demonstration. ZR dash, Y fire, A/B jump, stick and
Minus retry remain unchanged.

Visuals default **ON** for manual play, matching prior approved stages.
The toggle only changes four existing `SceneView` options:
`hd_hit_lighting`, `hd_atmospheric_haze`, `hd_footstep_dust`,
and `hd_hostile_projectile_halo`. All four are set together from
the same `HdFxRuntimeMode::activeForGameplay(manual)` source.

A small `HD FX: ON/OFF` text label in the scene is visible only when
the user is manually playing. It does not appear in previous automated
replay golden frames. The selected state is retained when moving
between manual and attract mode during a single NRO launch, but it is
not saved to disk (and is reset to ON at next launch).

The helper `graphics_core/hd_fx_toggle.hpp` has no libnx dependency,
simulation timers, heap allocations, original game assets or physics
updates. The controller-gesture adapter relies on the existing native
pad's DOWN edges; holding L+R never toggles repeatedly.

`tests/test_hd_fx_toggle.cpp` validates that:
- single L/R controls remain untouched;
- the joint chord toggles once on a new pressed edge;
- holding both for 45 polls does not re-toggle;
- manual and scripted demo modes are independent;
- the same scene renders deterministically, and turning effects OFF
  makes a visible pixel change;
- ON/OFF HUD labels differ only in manual mode;
- the old automated demo renders byte-identically, and renderer row
  padding remains intact.

This is an authored **visual preview** switch. It does not imply
NES behavioral fidelity or physical Nintendo Switch performance.
NeXium CI continues to exercise the default (HD ON) guest path,
including fourth-stage, footstep, actual guard impacts and hostile
projectile pixel evidence. Physical console handling of the L+R
gesture remains unmeasured.
