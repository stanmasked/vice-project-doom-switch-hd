# Stage 90 — genuine LOW HP warning lifecycle, four native NeXium X11 states

Stage 89 (the parent Ready PR #63) independently confirmed that a ROM-free, real guest guard collision caused source HP3→2, and the HUD drew the LOW HP warning at the source-owned pulse-ON frame 192. The earlier acceptance proved **appearance**. This independent stage proves **disappearance at the right time and correct recovery after defeat**, without changing gameplay.

## Existing second-run source and X11 frames

The same source-owned guest, pad and X11 artifacts from [successful NeXium run #39473228239](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39473228239) (evidence artifact #12287589163) contain:

| Native X11 capture | True occupied HP cells | Empty cells | Warning underline | Warning glyph |
|---|---:|---:|---:|---:|
| `screen-live-low-hp-0` | 2 | 3 | 228 pixels | 300 pixels |
| `screen-live-low-hp-2` | 2 | 3 | 0 | 0 |
| `screen-live-game-over` | 0 | 5 | 0 | 0 |
| `screen-live-defeat-restart` | 5 | 0 | 0 | 0 |

Native source audit grounds the sequence: first real guard melee frame **114**, third hit and HP2 frame **178**, pulse-ON at frame **192**, fifth hit and player defeat frame **242**, then a fresh physical Minus reset to HP5.

Corresponding full P6 SHA256 fingerprints, from the *actual archived host X11 captures*:

- HP2 warning ON: `248b3a8e4829f178bb9a141e545c58396e5f0f2dd06511ea3ea8a670fed7f02d`
- HP2 warning OFF: `1e6fa939ad9611f20c2742d3c8390eed44e2fa3d016b9df02cfbefe6a27d42db`
- HP0 defeat: `03db7aee31655f9123ef73c729c7beb9f7c8b5bff795f7fe6733bf13d5f67c52`
- HP5 restart: `ff9e357f498909b4c14f64938880d85dd7fcc064be5c1fb220d61d0386cd57ca`

## Independent fail-closed acceptance

New `tools/audit_nexium_hd_low_health_lifecycle.py` runs **after** all earlier independent source- and native-X11-based guard and warning verifiers. It requires:

1. Same authentic first/third/fifth guard strikes, independently confirmed by live source SD records and completed native defeat/retry PASS, with physically reported Minus.
2. The specific prior verified native warning-ON screenshot, proven by its **exact P6 SHA256** and previous pass receipt; then a **strictly later** screenshot with the *same* HP2 and both warning colors absent (never a death-screen shortcut).
3. A native game-over screenshot with **all five** source-owned hearts empty and **zero** low-HP label/underline.
4. The later physically triggered replay with **all five** source-owned hearts filled and **zero** lingering low-HP glyphs.
5. All four full native 1280×720 PNG+P6 images distinct by SHA256, in the correct event order; identical source-owned heart ROI geometry from the prior genuine bullet health audit.

Ten adversarial tests reject missing/partial hearts, forgery by writing LOW HP over HP5, warning leakage into pulse-OFF/defeat/retry, and malformed X11 buffers.

The test **does not** add a new NRO diagnostic marker, modify simulation frames or use artificial gameplay inputs. It validates existing real NeXium evidence, and the same gate must pass again on the exact new PR head before the stage is certified.

**Scope:** clean-room ROM-free prototype only; Nintendo Switch device runtime and equivalence with the original commercial NES release remain unproven.
