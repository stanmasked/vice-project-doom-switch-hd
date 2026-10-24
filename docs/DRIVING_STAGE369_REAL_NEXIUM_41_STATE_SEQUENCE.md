# Stage369 — robust manual-mode handshake and full NeXium guest sequence

## Result

**PASS** — [Stage365 full 41-state NeXium workflow #40078361434](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/40078361434) completed successfully on exact branch revision `03d6b90c0c618f0b895e87b2b8d3d0aa6658f527`.

- Exact-head NRO build: Success.
- Real NeXium guest run: Success.
- Synthetic negative audit regressions: **30/30 passed**.
- Real NRO guest trace: **41 records**, source-safe numeric reference pairs 519–559.
- Guest frames: 11–51, contiguous, delta 40.
- Guest-owned manual-mode entry witness and driving-preview entry witness both present.
- Real NeXium X11 focus was verified before input.
- Four real DEMO screenshots and additional startup/manual-entry screenshots captured.

## Why the input handshake changed

An earlier rerun with the same reproducible NRO SHA failed closed because it did not produce a native driving-entry witness. It was not counted as a pass. The failed artifact is retained privately for diagnosis.

Stage369 hardened the probe without changing the NRO runtime source:
1. Wait for the NRO itself to create its own SD witness files before sending input.
2. Confirm the NeXium window actually has keyboard focus.
3. Enter manual mode with the real R+A input and require the NRO-owned `manual_witness.txt` record.
4. Only then send the real ZL+ZR+X driving-preview chord.
5. Require the guest-created 41-state trace after the real ZL+ZR+L DEMO chord.
6. Save genuine X11 screenshots on startup and failure paths to aid diagnosis.
7. The auditor independently checks manual mode, driving entry, event ordering, all numeric values, all 41 guest frame numbers, per-frame framebuffer colors, constant source-free simulation fingerprint and screenshot evidence.

## Real guest record

The successful NRO trace starts at guest frame **11** (numeric reference pair 519, +3 px) and ends at guest frame **51** (pair 559, +5 px). Every row has the same source-free platform fingerprint `73663915c615b5d4`. Every row independently reports the expected libnx framebuffer samples: panel `ff5b4118`, edge `ffefda66`, DEMO glyph `ffefda66`.

Display contract: pair starts 519–526 show +3; 527–558 show +4; 559 shows +5. The numeric labels are a finite published aggregate contract, not a new original NES frame capture.

## Exact reproducibility hashes

- NRO inside the build artifact: 487,480 bytes; SHA-256 `7416c2bcb07e01e481d44f054186290d26a94d380e3f81c9efd8be6461e15ddf`.
- Exact-head NRO artifact ZIP: 163,881 bytes; SHA-256 `5b7b6338b97f0acdfdd484473a72661f60784430cab5867ca35aa1e42a356070`.
- Guest evidence ZIP: 165,462 bytes; SHA-256 `2debe1c2d930a4ca795860c67102a08689b971ec4e7f14cf657e89a3562cc880`.
- Both ZIP files pass CRC checks; the guest evidence ZIP has 15 files.
- Both artifacts were independently downloaded from private Google Drive after upload; sizes and SHA-256 values match the GitHub Actions artifacts.
- The official NeXium nightly release asset was verified against its publisher digest before execution.

## Evidence boundary

This proves the source-safe manual numeric DEMO and its guest framebuffer in NeXium. It does **not** prove original NES camera speed, vehicle physics, original art, original ROM/FM2 replay, or per-frame authenticity of original-game footage. The Stage355 source-image motion gate remains failed/inconclusive; Stage357's five ambiguous image pairs remain inconclusive. No original game ROM/FM2 or proprietary captures are embedded in public CI.

PR #99 remains Draft. No merge or `main` change was performed.
