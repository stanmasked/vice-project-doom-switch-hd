# Vice: Project Doom HD Remake — Stage365: full real NeXium guest sequence

**Result: PASS.** This report describes a source-safe numerical DEMO running inside an actual NeXium process. It does not claim original NES gameplay, art reconstruction, original source-frame authentication or vehicle/camera physics.

## Exact tested revision and workflows

- Exact tested code revision: `25c2061f11abada4ddc98a0291df98736c6f3c7e`.
- [Stage365 NeXium full 41-state sequence #40074546986](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/40074546986) — **Success**.
- [Native Core CI #40074546965](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/40074546965) — **Success**.
- [Exact-head ROM-free NRO build artifact #12552935595](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/40074546986/artifacts/12552935595) and [real guest evidence #12552274467](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/40074546986/artifacts/12552274467).

## Independent artifact verification

- NRO extracted from the build ZIP: **487,480 bytes**, SHA-256 `5e0f1c1c7e319188a630d7c5826ce89d3c3facec8ea451e3c8890408f129e80c`.
- Build ZIP: **163,882 bytes**, SHA-256 `b6601d64b7b788350cc21209397848677f648f5234a5c4db1e5da7c0751621da`; ZIP CRC passes, one NRO member.
- Guest evidence ZIP: **93,057 bytes**, SHA-256 `ec599e6516a0c25ca0e7957790e693aefb85398099066f29cb8aa5b3cbbf2338`; ZIP CRC passes, 12 members.
- NeXium nightly was fetched and verified against GitHub's official release API before execution. Asset ID `670955988`, archive SHA-256 `d08e89d15632c2ba3ef0521635286793885ac1eaabed6ab93f2d0ec7d5c10180`. The upstream tag is mutable; the exact downloaded asset digest is recorded with the run.

## Real guest evidence — all 41 states

A fresh keyboard edge was sent to a real NeXium GUI after the guest recorded manual-driving entry. NeXium's upstream default map converts host `R+T+Q` to Switch `ZL+ZR+L`. The NRO itself sampled the panel, edge and DEMO glyph pixels from its rendered framebuffer for every sequence record.

| Guest event | Published numeric reference pair | Actual NRO guest frame | Numeric shift |
|---|---:|---:|---:|
| `on` | 519 | 13 | +3 px |
| `frame` × 39 | 520–558 | 14–52 | +3 px for 520–526; +4 px for 527–558 |
| `last` | 559 | 53 | +5 px |

Verified properties:

- Exactly **41** guest-written rows: 1 `on`, 39 `frame`, 1 `last`.
- Pair IDs and NRO guest frames are contiguous; no skipped, repeated, rewound or reordered row.
- The first-to-last guest frame delta is **40**, spanning all 41 presentations.
- Every row carries expected framebuffer samples: panel `ff5b4118`, edge `ffefda66`, glyph `ffefda66`.
- One unchanged source-free platform-state fingerprint appears in all 41 rows.
- Four actual 1280×720 X11 screenshots were captured. The strict screenshot audit found the cyan DEMO panel in three: 197, 194 and 203 sampled cyan pixels respectively.
- All **28** synthetic negative tests passed, including missing/extra/reordered states, frame gaps/wrap, incorrect pair/shift/pixel samples, fingerprint changes and attempts to claim original ROM or physics proof.

## Implementation

- `graphics_core/driving_source_scroll_demo_guest.hpp` now emits a Stage365 v2 guest trace for each displayed state while preserving the Stage364 two-endpoint compatibility file.
- `switch_graphical/source/main.cpp` samples each presented `Preview`/ `LastFrame` state only while the source-safe DEMO is active.
- `tools/nexium_stage365_sequence_probe.sh` sends real host inputs and captures real X11 images; it never writes guest evidence.
- `tools/audit_nexium_stage365_sequence.py` rejects incomplete or malformed traces and requires the screenshot evidence.
- `tests/test_nexium_stage365_sequence.py` contains 28 synthetic negative regressions.

The first Stage365 attempt did collect all 41 guest states but failed closed because the host summary wrote `yes` instead of the required `on`/`last` labels. That attempt is retained separately in the private evidence archive. The corrected second run passed without weakening the auditor.

## Strict boundary and next step

The result confirms the source-safe numerical overlay and per-frame libnx framebuffer witness inside NeXium. It does **not** prove original NES source-frame replay, original artwork, original camera motion, road physics or car physics. Stage355's original-source motion confidence gate and Stage357's five ambiguous pairs remain unresolved.

Next: add explicit pause/restart and deliberate dropped-frame/repeated-frame cases to the full trace test, while keeping source authentication and original-game comparison as a separate evidence gate. PR #99 remains Draft; `main` is untouched.
