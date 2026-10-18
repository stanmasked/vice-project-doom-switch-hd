# Native Nintendo Switch NRO artifact audit — ROM-free research build

This record identifies **specific GitHub Actions build artifacts** from
commit `721a2db5a7881dd7a514ba1f3db1b1e0976d8039` in
`stanmasked/vice-project-doom-switch-hd`, rather than implying any
general claim that all future builds are identical. Original commercial
game ROMs, graphics, firmware, or console keys are not involved.

## Successful build provenance

| Prototype | Actions run | NRO SHA-256 | NRO bytes | Program bytes |
| --- | --- | --- | ---: | ---: |
| ROM-free ASCII test | [#39154101041](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39154101041) | `c006879256702d98c7369c28e941561fdc28df04841188b3ff8ccc979a0a6849` | 221240 | 204800 |
| ROM-free native graphical scene | [#39154101148](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39154101148) | `0adad7512c6ffd4be86d17215b7cb9b932c45e2dae03214705628ca048196b40` | 340024 | 323584 |

Actual artifact entries: `vpd_native_probe.nro` and
`vpd_native_scene.nro`. In this build each binary has a valid
`NRO0` header, adjacent page-aligned text/rodata/data segments, a
nonzero NRO build ID, 16 KiB BSS, and an `ASET` header with one
16 KiB `NACP` block. Both ZIPs were independently retrieved from
their respective successful GitHub Actions runs and examined offline.

Original GitHub archive artifact names are
`vpd-native-rom-free-probe` and `vpd-native-raster-scene`.
GitHub-side NRO checks and full host gameplay/raster tests also
succeeded for the associated revision. None of this demonstrates a
runtime launch or even a graphics frame rendered by Nintendo Switch.

## Stricter build checking

The existing `tests/check_nro.py` has been strengthened beyond
the former two-condition signature+length check. It now rejects
bad version/flags, invalid or overlapping aligned sections, missing
build identity, malformed `ASET` descriptors, overlapping or
out-of-range assets, and trailing bytes. Unit regressions
`tests/test_nro_layout.py` exercise deliberately corrupted
self-generated NRO samples (no downloaded or proprietary binaries
are committed).

Future NRO build jobs run this checker on the resulting build.
Only successful actual CI logs can establish that the *new*
checker ran against a future NRO; previous CI success applied the
earlier weaker implementation.

## Emulator or console smoke-test protocol

When a legally configured, NRO-capable Nintendo Switch homebrew
runtime is available, run **the exact artifact** `vpd_native_scene.nro`
from the GitHub run above, or a new artifact with separately recorded
SHA-256. The graphical prototype should show the **original ROM-free
synthetic arena**, not any actual Vice: Project Doom level.

Basic controls in the current source:

- D-pad / left stick: walk left or right
- A or B: jump
- Y: fire bounded synthetic projectiles
- Plus: exit

Capture the launch result, emulator/runtime version, tested NRO SHA-256,
button-input observations, whether the target responds to hits, and
whether framebuffer crashes or data corruption occur. Mark each item
**observed**, **failed**, or **not tested**; do not infer FPS, frame
timing, controller behavior or a working remake from CI alone.

No emulator, Switch console, original game source, licensed firmware or
game files have been used in this artifact audit. This is a test-scene
homebrew prototype, not a playable recreation of the commercial game.
