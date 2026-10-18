# Stage151 — verified pre-render reset between CPU OAM and next XBuf

## Why this additional gate is needed

Stage149 already proved native CPU writes to OAM. Stage150's dynamic
sprite-to-XBuf experiment targets the first post-write rendered frame.
Stage151 adds an *independent real source boundary* so a positive pixel
difference cannot masquerade as a transition between frames without
the FCEUX pre-render PPU reset.

## Native observations

The opt-in source injector instruments three exact sites in the pinned
private FCEUX C++ build, preserving all previously installed hooks:

- Immediately before the original \`PPU_status = 0;\` statement, after
  Stage141's existing pre-reset observer.
- Immediately after that real status clear, after Stage141's existing
  post-reset observer.
- Immediately after the Stage150 real final XBuf pixel observation.

A reset counts as the transition only if, **before the reset**,
the Stage150 before-frame contains all eight actual XBuf samples,
the after-frame is not yet seen, and Stage149 has emitted a complete,
error-free CPU OAM write witness following a real bit7-high $2002 read.

The completion hook accepts exactly one matching reset, a cleared
post-reset PPU status, eight before-frame and eight after-frame XBuf
samples, and a positive underlying Stage150/149 witness. Repeated,
absent, improperly ordered or contradicted resets yield a native
REJECT, not a positive certificate.

The distinct expected source certificate is:

\`VPD_STAGE151_NATIVE_PRERENDER_OAM_BOUNDARY_PASS\`

and after *both* ROMs, wrong-mode REJECT and observer-off check:

\`STAGE151_NATIVE_PRERENDER_OAM_FRAME_BOUNDARY_PROOF\`

The native experiment is an integration test of pinned FCEUX
emulator behavior using synthetic Mapper4 ROMs. It is **not** a
claim about exact real NES hardware scanline timing or original
Vice: Project Doom gameplay, nor about a working Switch remake.

## Synthetic preflight

The Stage151 unit tests exercise both LF and CRLF guarded hook
placement, missing source-site rejection, strict certificate
parsing, forged reset counts and frame sample totals, and compiled C++
stubs with correct, absent and corrupt pre-render reset events.

Run:

    python -m unittest discover -s tests -p 'test_fceux_stage151_prerender_boundary.py' -v

Stage151 is native-unverified until its own GitHub Actions build passes
and the exact aggregate marker appears. No commercial ROM data,
screenshots or private game resources are included.
